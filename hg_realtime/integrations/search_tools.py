"""Brave-backed search tools and SSRF-safe URL fetch."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import socket
import ssl
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .rate_limit_cache import RateLimiter, TTLCache
from .tool_router import ToolCall

MAX_FETCH_BYTES = 1 * 1024 * 1024
MAX_FETCH_REDIRECTS = 3
FETCH_TIMEOUT_S = 15
URL_FETCH_CACHE_TTL_S = float(os.environ.get("HG_URL_FETCH_CACHE_TTL_S", "300"))
BRAVE_CACHE_TTL_S = float(os.environ.get("HG_BRAVE_CACHE_TTL_S", "300"))
MAX_COUNT = 10
BRAVE_SEARCH_BASE_URL = "https://api.search.brave.com/res/v1"

_search_rate_limiter: RateLimiter | None = None
_tenant_limiters: Dict[str, RateLimiter] = {}
_search_cache: TTLCache | None = None
_brave_cache: TTLCache | None = None
_url_fetch_cache: TTLCache | None = None
_credentials_cache: Dict[str, Any] | None = None
_lock = __import__("threading").Lock()


def _workspace_root() -> Path:
    explicit = (os.environ.get("HG_WORKSPACE") or "").strip()
    if explicit:
        return Path(explicit).resolve()
    return Path(__file__).resolve().parents[2]


def _load_workspace_credentials() -> Dict[str, Any]:
    global _credentials_cache
    if _credentials_cache is not None:
        return _credentials_cache
    path = _workspace_root() / "credentials.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, json.JSONDecodeError):
        data = {}
    _credentials_cache = data if isinstance(data, dict) else {}
    return _credentials_cache


def _first_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _credential_api_key(section_name: str) -> str | None:
    creds = _load_workspace_credentials()
    section = creds.get(section_name)
    if isinstance(section, dict):
        return _first_string(section.get("api_key"), section.get("key"), section.get("token"))
    value = creds.get(section_name)
    return _first_string(value)


def _get_brave_search_api_key() -> str | None:
    return _first_string(
        os.environ.get("HG_BRAVE_SEARCH_API_KEY"),
        os.environ.get("BRAVE_API_KEY"),
        _credential_api_key("brave_search"),
    )


def _get_brave_ai_api_key() -> str | None:
    return _first_string(
        os.environ.get("HG_BRAVE_AI_API_KEY"),
        os.environ.get("BRAVE_AI_API_KEY"),
        _credential_api_key("brave_baseai"),
        _credential_api_key("brave_freeai"),
        _get_brave_search_api_key(),
    )


def _get_url_fetch_cache() -> TTLCache:
    global _url_fetch_cache
    if _url_fetch_cache is None:
        with _lock:
            if _url_fetch_cache is None:
                _url_fetch_cache = TTLCache(ttl_seconds=URL_FETCH_CACHE_TTL_S, max_entries=500)
    return _url_fetch_cache


def _is_ip_allowed(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    if addr.is_private or addr.is_loopback or addr.is_link_local:
        return False
    if ip_str == "169.254.169.254" or (addr.version == 4 and str(addr).startswith("169.254.")):
        return False
    return True


def _resolve_host(host: str, port: int) -> str | None:
    try:
        infos = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror:
        return None
    for info in infos:
        sockaddr = info[4]
        ip = sockaddr[0] if isinstance(sockaddr, tuple) else None
        if ip and _is_ip_allowed(ip):
            return ip
    return None


def _fetch_url_ssrf_safe(url: str) -> Tuple[int, str, bytes, str]:
    import http.client

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http and https allowed")
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    resolved_ip = _resolve_host(host, port)
    if not resolved_ip:
        raise ValueError("url_resolved_to_denied_ip")
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query

    content_type = ""
    body = b""
    status = 0
    final_url = url
    for _ in range(MAX_FETCH_REDIRECTS + 1):
        if parsed.scheme == "https":
            conn = http.client.HTTPSConnection(host, port, timeout=FETCH_TIMEOUT_S)
            conn._context = ssl.create_default_context()
            sock = socket.create_connection((resolved_ip, port), timeout=FETCH_TIMEOUT_S)
            conn.sock = conn._context.wrap_socket(sock, server_hostname=host)
        else:
            conn = http.client.HTTPConnection(resolved_ip, port, timeout=FETCH_TIMEOUT_S)
        conn.request("GET", path, headers={"Host": host, "User-Agent": "HgFetch/1.0"})
        resp = conn.getresponse()
        status = resp.status
        headers = dict(resp.getheaders())
        content_type = (headers.get("content-type") or "").split(";")[0].strip().lower() or "application/octet-stream"
        body = resp.read(MAX_FETCH_BYTES + 1)
        if len(body) > MAX_FETCH_BYTES:
            body = body[:MAX_FETCH_BYTES]
        location = headers.get("Location")
        conn.close()
        if 300 <= status < 400 and location:
            location = urllib.parse.urljoin(final_url, location)
            parsed = urllib.parse.urlparse(location)
            if parsed.scheme not in ("http", "https"):
                break
            host = parsed.hostname or ""
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            resolved_ip = _resolve_host(host, port)
            if not resolved_ip:
                raise ValueError("redirect_to_denied_ip")
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            final_url = location
            continue
        break
    return (status, final_url, body, content_type or "application/octet-stream")


def _get_search_limiter(tenant_id: str | None = None) -> RateLimiter:
    global _search_rate_limiter, _tenant_limiters
    if tenant_id:
        with _lock:
            if tenant_id not in _tenant_limiters:
                rpm = int(os.environ.get("HG_SEARCH_RPM", "60"))
                _tenant_limiters[tenant_id] = RateLimiter(requests_per_minute=rpm, window_s=60.0)
            return _tenant_limiters[tenant_id]
    if _search_rate_limiter is None:
        with _lock:
            if _search_rate_limiter is None:
                rpm = int(os.environ.get("HG_SEARCH_RPM", "60"))
                _search_rate_limiter = RateLimiter(requests_per_minute=rpm, window_s=60.0)
    return _search_rate_limiter


def _get_search_cache() -> TTLCache:
    global _search_cache
    if _search_cache is None:
        with _lock:
            if _search_cache is None:
                ttl = float(os.environ.get("HG_SEARCH_CACHE_TTL_S", "3600"))
                _search_cache = TTLCache(ttl_seconds=ttl, max_entries=1000)
    return _search_cache


def _get_brave_cache() -> TTLCache:
    global _brave_cache
    if _brave_cache is None:
        with _lock:
            if _brave_cache is None:
                _brave_cache = TTLCache(ttl_seconds=BRAVE_CACHE_TTL_S, max_entries=500)
    return _brave_cache


def _get(call: ToolCall, key: str, default: Any = None) -> Any:
    return call.args.get(key, default)


def _cache_key(prefix: str, value: str) -> str:
    h = hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()
    return f"{prefix}:{h[:32]}"


def _normalize_count(count: Any, default: int = MAX_COUNT) -> int:
    if count is None:
        return default
    try:
        return min(MAX_COUNT, max(1, int(count)))
    except (TypeError, ValueError):
        return default


def _build_brave_headers(api_key: str) -> Dict[str, str]:
    return {
        "X-Subscription-Token": api_key,
        "Accept": "application/json",
        "User-Agent": "HydrogenuineBrave/1.0",
    }


def _brave_request(path: str, *, method: str = "GET", query: Dict[str, Any] | None = None, body: Dict[str, Any] | None = None) -> Dict[str, Any]:
    api_key = _get_brave_search_api_key()
    if not api_key:
        return {}
    url = f"{BRAVE_SEARCH_BASE_URL}{path}"
    payload: bytes | None = None
    headers = _build_brave_headers(api_key)
    if method.upper() == "GET":
        params = {k: v for k, v in (query or {}).items() if v not in (None, "", [])}
        if params:
            url += "?" + urllib.parse.urlencode(params, doseq=True)
    else:
        headers["Content-Type"] = "application/json"
        payload = json.dumps({k: v for k, v in (body or {}).items() if v not in (None, "", [])}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return {}


def _normalize_brave_search_results(payload: Dict[str, Any], *, kind: str, count: int, freshness: str | None = None) -> List[Dict[str, Any]]:
    if kind == "web":
        results = ((payload.get("web") or {}).get("results") or []) if isinstance(payload, dict) else []
    else:
        results = (payload.get("results") or []) if isinstance(payload, dict) else []
    normalized: List[Dict[str, Any]] = []
    for row in results[:count]:
        if not isinstance(row, dict):
            continue
        item: Dict[str, Any] = {
            "title": row.get("title") or "",
            "url": row.get("url") or "",
            "description": row.get("description") or "",
        }
        age = row.get("age")
        if age:
            item["age"] = age
        page_age = row.get("page_age")
        if page_age:
            item["page_age"] = page_age
        meta_url = row.get("meta_url")
        if isinstance(meta_url, dict):
            item["hostname"] = meta_url.get("hostname") or ""
        if freshness:
            item["freshness"] = freshness
        normalized.append(item)
    return normalized


def _run_brave_search(kind: str, *, query: str, count: int, freshness: str | None = None, method: str = "GET") -> List[Dict[str, Any]]:
    endpoint = "/web/search" if kind == "web" else "/news/search"
    payload = {"q": query, "count": count}
    if freshness:
        payload["freshness"] = freshness
    response = _brave_request(endpoint, method=method, query=payload if method == "GET" else None, body=payload if method != "GET" else None)
    return _normalize_brave_search_results(response, kind=kind, count=count, freshness=freshness)


def _handle_brave_search(call: ToolCall, *, kind: str, action: str, method: str = "GET") -> Dict[str, Any]:
    q = _get(call, "query") or _get(call, "q")
    if not q:
        return {"ok": False, "error": "query or q is required", "action": action}
    q = str(q).strip()
    count = _normalize_count(_get(call, "count"))
    freshness = _get(call, "freshness")
    freshness = str(freshness).strip() if freshness else None
    tenant_id = _get(call, "tenant_id")
    tenant_id = str(tenant_id) if tenant_id else None
    cache = _get_brave_cache()
    key = _cache_key(action, f"{q}|{count}|{freshness or ''}|{method}")
    cached = cache.get(key)
    if cached is not None:
        return {**cached, "cached": True}
    if not _get_search_limiter(tenant_id).check():
        return {"ok": False, "error": "rate_limit_exceeded", "action": action}
    results = _run_brave_search(kind, query=q, count=count, freshness=freshness, method=method)
    result = {
        "ok": True,
        "data": {"query": q, "results": results, "count": len(results), "freshness": freshness, "provider": "brave", "kind": kind},
        "action": action,
    }
    cache.set(key, result)
    return result


def _run_brave_answer(prompt: str, *, model: str | None = None) -> Dict[str, Any]:
    api_key = _get_brave_ai_api_key()
    if not api_key:
        return {}
    base_url = (os.environ.get("HG_BRAVE_AI_BASE_URL") or os.environ.get("BRAVE_AI_BASE_URL") or "https://api.search.brave.com/res/v1/chat/completions").strip()
    body = {
        "model": model or (os.environ.get("HG_BRAVE_AI_MODEL") or "brave-default"),
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "HydrogenuineBrave/1.0",
    }
    req = urllib.request.Request(base_url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return {}


def handler_search_query(call: ToolCall) -> Dict[str, Any]:
    q = _get(call, "q") or _get(call, "query")
    if not q:
        return {"ok": False, "error": "q or query is required", "action": "search.query"}
    q = str(q).strip()
    tenant_id = _get(call, "tenant_id")
    tenant_id = str(tenant_id) if tenant_id else None
    cache = _get_search_cache()
    key = _cache_key("query", q)
    cached = cache.get(key)
    if cached is not None:
        return {**cached, "cached": True}
    if not _get_search_limiter(tenant_id).check():
        return {"ok": False, "error": "rate_limit_exceeded", "action": "search.query"}
    results = _run_brave_search("web", query=q, count=MAX_COUNT)
    result = {"ok": True, "data": {"query": q, "results": results, "count": len(results), "provider": "brave", "kind": "web"}, "action": "search.query"}
    cache.set(key, result)
    return result


def handler_web_search_brave(call: ToolCall) -> Dict[str, Any]:
    return _handle_brave_search(call, kind="web", action="web.search_brave", method="GET")


def handler_brave_web_search(call: ToolCall) -> Dict[str, Any]:
    return _handle_brave_search(call, kind="web", action="brave.web.search", method="GET")


def handler_brave_web_search_post(call: ToolCall) -> Dict[str, Any]:
    return _handle_brave_search(call, kind="web", action="brave.web.search_post", method="POST")


def handler_brave_news_search(call: ToolCall) -> Dict[str, Any]:
    return _handle_brave_search(call, kind="news", action="brave.news.search", method="GET")


def handler_brave_news_search_post(call: ToolCall) -> Dict[str, Any]:
    return _handle_brave_search(call, kind="news", action="brave.news.search_post", method="POST")


def handler_brave_answers(call: ToolCall) -> Dict[str, Any]:
    prompt = _get(call, "prompt") or _get(call, "query") or _get(call, "q")
    if not prompt:
        return {"ok": False, "error": "prompt or query is required", "action": "brave.answers"}
    prompt = str(prompt).strip()
    response = _run_brave_answer(prompt, model=_get(call, "model"))
    choices = response.get("choices") if isinstance(response, dict) else None
    content = ""
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(message, dict):
            content = str(message.get("content") or "")
    return {
        "ok": True,
        "data": {
            "prompt": prompt,
            "content": content,
            "provider": "brave",
            "model": (response.get("model") if isinstance(response, dict) else None) or _get(call, "model"),
        },
        "raw": response,
        "action": "brave.answers",
    }


def handler_search_fetch_url(call: ToolCall) -> Dict[str, Any]:
    url = _get(call, "url")
    if not url:
        return {"ok": False, "error": "url is required", "action": "search.fetch_url"}
    url = str(url).strip()
    cache = _get_url_fetch_cache()
    key = _cache_key("url", url)
    cached = cache.get(key)
    if cached is not None:
        return {**cached, "cached": True}
    tenant_id = _get(call, "tenant_id")
    tenant_id = str(tenant_id) if tenant_id else None
    if not _get_search_limiter(tenant_id).check():
        return {"ok": False, "error": "rate_limit_exceeded", "action": "search.fetch_url"}
    try:
        status_code, final_url, body, content_type = _fetch_url_ssrf_safe(url)
        sha256 = hashlib.sha256(body).hexdigest()
        size_bytes = len(body)
        content_preview = body.decode("utf-8", errors="replace")[:8192]
        result = {
            "ok": True,
            "data": {
                "url": url,
                "final_url": final_url,
                "status_code": status_code,
                "sha256": sha256,
                "size_bytes": size_bytes,
                "content_type": content_type,
                "content_preview": content_preview,
            },
            "evidence": {
                "status_code": status_code,
                "final_url": final_url,
                "sha256": sha256,
                "size_bytes": size_bytes,
                "content_type": content_type,
            },
            "action": "search.fetch_url",
        }
    except ValueError as exc:
        result = {"ok": False, "error": str(exc), "action": "search.fetch_url"}
    except Exception as exc:
        result = {"ok": False, "error": str(exc), "action": "search.fetch_url"}
    cache.set(key, result)
    return result
