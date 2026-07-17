"""
DAG direct-post path for fourclaw: goal -> title/content -> fourclaw_auto_post_async -> thread_id/thread_url.

Used when the DAG runs fourclaw-auto-post with a goal in inputs; creates a post in-process
without invoking the session runner (run_task only emits instructions and does not execute the agent).
See hg_core/task_graph/docs/dag_wiring_plan.md.

Option B (LLM): Set HG_DAG_POST_USE_LLM=1 to generate title and content in the agent's persona
(4claw SOUL/HEART/IDENTITY + session memory, then generic LLM if needed). The post is paraphrased
in 4claw voice. Requires OPENAI_API_KEY and the openai package. If the LLM path fails, we return
an error (no template fallback); the LLM must run every time when USE_LLM=1.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Optional OpenAI for LLM fallback when hg_llm not used
try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None  # type: ignore[misc, assignment]
    _OPENAI_AVAILABLE = False


def _llm_complete(messages: list, model: str, max_tokens: int = 200, temperature: float = 1.0) -> Optional[str]:
    """Call LLM via hg_llm registry (preferred) or OpenAI. Returns content or None."""
    provider = os.environ.get("HG_DAG_POST_LLM_PROVIDER", "openai")
    try:
        from hg_llm import get_default_registry
        registry = get_default_registry()
        resp = registry.complete(
            messages=messages,
            model=model,
            provider=provider,
            api_key_env="OPENAI_API_KEY",
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return (resp.content or "").strip() or None
    except Exception:
        pass
    if _OPENAI_AVAILABLE and OpenAI:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if api_key:
            try:
                client = OpenAI(api_key=api_key)
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_completion_tokens=max_tokens,
                    temperature=temperature,
                )
                return (resp.choices[0].message.content or "").strip() or None
            except Exception:
                pass
    return None


USE_LLM_ENV = "HG_DAG_POST_USE_LLM"
DAG_POST_LLM_MODEL_ENV = "HG_DAG_POST_LLM_MODEL"
DAG_POST_LLM_MODEL_DEFAULT = "gpt-5-mini"

# Captured from LLM calls when they raise; used to surface real error in run_fourclaw_post_from_goal
_last_llm_error: Optional[str] = None


def _goal_to_title_content_template(goal_str: str) -> Tuple[str, str]:
    """Template-only: title = first line or goal[:80], content = goal."""
    first_line = goal_str.splitlines()[0].strip() if goal_str.splitlines() else goal_str
    title = (first_line or "DAG post")[:80]
    content = goal_str
    return title, content


def _goal_to_title_content_agent_like(goal_str: str, model: str) -> Optional[Tuple[str, str]]:
    """
    Generate title and content using 4claw persona (SOUL/HEART/IDENTITY) and session memory.
    Returns (title, content) or None on failure. Uses hg_llm or OPENAI_API_KEY.
    """
    global _last_llm_error
    try:
        persona: Dict[str, str] = {}
        try:
            from hg_persona import load_platform_persona
            persona = load_platform_persona("fourclaw") or {}
        except Exception:
            pass
        soul = (persona.get("soul") or "").strip()[:1500]
        heart = (persona.get("heart") or "").strip()[:800]
        identity = (persona.get("identity") or "").strip()[:800]
        memory_summary = ""
        try:
            from hg_core.session_manager import load_compacted_memory
            from hg_core.context_loader import format_memory_context
            memory = load_compacted_memory("automation-fourclaw-auto-post", max_tokens=500)
            memory_summary = (format_memory_context(memory) or "").strip()[:500]
        except Exception:
            pass
        system_parts = [
            "You are the 4claw agent. Create one 4claw thread in your voice (shitposting style, /b/ energy).",
            "Output exactly two lines. Line 1: thread title only, max 80 characters, no newline. Line 2: post body (1-3 sentences).",
        ]
        if soul:
            system_parts.append(f"SOUL (who you are): {soul}")
        if heart:
            system_parts.append(f"HEART (priorities): {heart}")
        if identity:
            system_parts.append(f"IDENTITY (voice): {identity}")
        system_content = "\n\n".join(system_parts)
        user_content = f"Mandatory topic for this post: {goal_str[:500]}"
        if memory_summary:
            user_content += f"\n\nRecent context: {memory_summary}"
        text = _llm_complete(
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            model=model,
            max_tokens=200,
            temperature=1.0,
        )
        if not text:
            _last_llm_error = "LLM returned empty response (expected title on line 1, body on line 2)."
            return None
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if len(lines) < 2:
            _last_llm_error = f"LLM returned single line (expected 2 lines: title then body). Got: {text[:120]!r}"
            return None
        title = (lines[0] or "DAG post")[:80]
        content = "\n".join(lines[1:]) or "Post."
        return title, content
    except Exception as e:
        _last_llm_error = str(e).strip() or f"{type(e).__name__}"
        return None


def _goal_to_title_content_llm(goal_str: str, model: str) -> Optional[Tuple[str, str]]:
    """
    One short LLM call: turn goal into title (max 80 chars) and body (1-2 sentences).
    Returns (title, content) or None on failure. Uses hg_llm or OPENAI_API_KEY.
    """
    global _last_llm_error
    try:
        prompt = (
            f"Given this goal for a 4claw post, output exactly two lines.\n"
            f"Line 1: thread title only, max 80 characters, no newline.\n"
            f"Line 2: post body, 1-2 short sentences.\n\nGoal: {goal_str[:500]}"
        )
        text = _llm_complete(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            max_tokens=200,
            temperature=1.0,
        )
        if not text:
            _last_llm_error = "LLM returned empty response (expected title on line 1, body on line 2)."
            return None
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if len(lines) < 2:
            _last_llm_error = f"LLM returned single line (expected 2 lines: title then body). Got: {text[:120]!r}"
            return None
        title = (lines[0] or "DAG post")[:80]
        content = "\n".join(lines[1:]) or goal_str
        return title, content
    except Exception as e:
        _last_llm_error = str(e).strip() or f"{type(e).__name__}"
        return None


SVG_MAX_BYTES = 4096


def _goal_to_svg_llm(goal_str: str, title: str, content: str, model: str) -> Optional[str]:
    """
    Ask LLM for a single inline SVG string (under 4KB, valid XML, animated).
    Returns SVG string or None on failure. Caller should validate/fix/minify before use.
    """
    prompt = (
        "Generate a single inline SVG for an imageboard post. Requirements:\n"
        "- Output ONLY the SVG markup: start with <svg and end with </svg>. No markdown, no explanation.\n"
        "- Must be valid XML: close all tags, use xmlns=\"http://www.w3.org/2000/svg\" on the root <svg>.\n"
        "- Include 2-4 simple animations (e.g. <animate>, <animateTransform>) so it feels alive.\n"
        "- Total size under 3500 bytes (UTF-8). Use short paths, minimal text, no long comments.\n"
        "- Match the post vibe: meme/shitpost energy, reaction image style.\n\n"
        f"Post title: {title[:80]}\n"
        f"Post topic: {goal_str[:300]}\n"
    )
    text = _llm_complete(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        max_tokens=800,
        temperature=0.8,
    )
    if not text or not text.strip():
        return None
    # Extract first <svg>...</svg> block
    match = re.search(r"<svg[\s\S]*?</svg>", text.strip(), re.IGNORECASE)
    if not match:
        return None
    return match.group(0).strip()


def _parse_stdout_for_thread_result(stdout: str) -> Optional[Dict[str, Any]]:
    """Parse stdout for a JSON line with thread_id/thread_url; return dict or None."""
    if not stdout or not isinstance(stdout, str):
        return None
    lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
    for line in reversed(lines):
        if "thread_id" not in line and "thread_url" not in line:
            continue
        try:
            obj = json.loads(line)
            if not isinstance(obj, dict):
                continue
            thread_id = obj.get("thread_id")
            thread_url = obj.get("thread_url")
            if thread_id and not thread_url:
                thread_url = f"https://www.4claw.org/t/{thread_id}"
            if thread_id or thread_url:
                return {"thread_id": thread_id, "thread_url": thread_url}
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def run_fourclaw_post_from_goal(
    goal: str,
    board: str = "b",
    timeout_s: int = 120,
    use_llm: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Create a single 4claw thread from a goal string (DAG direct-post path).

    Builds title and content from the goal: if use_llm is True (or HG_DAG_POST_USE_LLM=1),
    tries one short LLM call (OpenAI); otherwise or on failure uses template (first line / goal).
    Writes temp files, runs fourclaw_auto_post_async.py, returns thread_id/thread_url on success.

    Returns:
        {"ok": True, "outputs": {"thread_id": ..., "thread_url": ...}} on success,
        or {"ok": False, "error": "..."} on failure.
    """
    global _last_llm_error
    try:
        from hg_lib.config import get_workspace_root
        root = get_workspace_root()
    except Exception as e:
        return {"ok": False, "error": f"Workspace root: {e}"}

    goal_str = (goal or "").strip()
    if not goal_str:
        return {"ok": False, "error": "Goal is empty"}

    # Title and content: Option B (LLM) if enabled: agent-like -> generic LLM -> template from goal
    if use_llm is None:
        use_llm = os.environ.get(USE_LLM_ENV, "").strip() in ("1", "true", "yes")
    if use_llm:
        _last_llm_error = None
        model = os.environ.get(DAG_POST_LLM_MODEL_ENV, "").strip() or DAG_POST_LLM_MODEL_DEFAULT
        pair = _goal_to_title_content_agent_like(goal_str, model)
        if not pair:
            pair = _goal_to_title_content_llm(goal_str, model)
        if not pair:
            if not _OPENAI_AVAILABLE:
                err = "openai package not installed. Install with: pip install openai"
            elif not os.environ.get("OPENAI_API_KEY", "").strip():
                err = "OPENAI_API_KEY is not set or empty."
            else:
                detail = (_last_llm_error or "").strip()[:400]
                err = f"LLM failed to generate title/content: {detail}" if detail else "LLM failed (API or network). Check OPENAI_API_KEY."
            _last_llm_error = None
            return {"ok": False, "error": err}
        title, content = pair
    else:
        title, content = _goal_to_title_content_template(goal_str)

    # Lane-assist (Chapter 2B): draft -> apply -> final_text; post_trace appended on success
    post_trace_result: Optional[Dict[str, Any]] = None
    try:
        from hg_overseer.overseer_core.steering_store import load_profile
        from hg_overseer.overseer_core.lane_assist import apply as lane_assist_apply
        from hg_overseer.overseer_core.post_trace import append_trace_to_jsonl
        steering = load_profile("fourclaw-auto-post", root)
        cycle_id = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        lane_out = lane_assist_apply(content, "fourclaw-auto-post", cycle_id, steering, context={})
        content = lane_out["final_text"]
        post_trace_result = {"post_trace": lane_out["post_trace"], "append_trace": append_trace_to_jsonl}
        # Steering telemetry (Chapter 3): emit lane_assist_applied to overseer steering_events.jsonl
        try:
            events_path = root / "memory" / "overseer" / "steering_events.jsonl"
            events_path.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "event": "lane_assist_applied",
                "agent_id": "fourclaw-auto-post",
                "cycle_id": cycle_id,
                "details": {"transforms_applied": (lane_out.get("post_trace") or {}).get("transforms_applied", [])},
            }
            write_legacy = True
            try:
                from hg_gateway.shared_storage import append_steering_telemetry, use_shared_gateway_db

                append_steering_telemetry("lane_assist_applied", entry)
                write_legacy = not use_shared_gateway_db(events_path)
            except Exception:
                pass
            if write_legacy:
                with open(events_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry) + "\n")
                    f.flush()
        except Exception:
            pass
    except Exception:
        post_trace_result = None

    script_path = root / "hg_platforms" / "fourclaw" / "fourclaw_auto_post_async.py"
    if not script_path.exists():
        script_path = root / "fourclaw" / "fourclaw_auto_post_async.py"
    if not script_path.exists():
        return {"ok": False, "error": f"Posting script not found: {script_path}"}

    tmpdir = tempfile.mkdtemp(prefix="hg_dag_post_")
    try:
        title_file = Path(tmpdir) / "title.txt"
        content_file = Path(tmpdir) / "content.txt"
        title_file.write_text(title, encoding="utf-8")
        content_file.write_text(content, encoding="utf-8")

        svg_file: Optional[Path] = None
        if use_llm and goal_str:
            try:
                raw_svg = _goal_to_svg_llm(goal_str, title, content, model)
                if raw_svg:
                    from hg_platforms.fourclaw.svg_validator import validate_and_fix_svg, minify_svg
                    fixed_svg, is_valid, _ = validate_and_fix_svg(raw_svg)
                    if is_valid:
                        minified = minify_svg(fixed_svg)
                        if len(minified.encode("utf-8")) <= SVG_MAX_BYTES:
                            svg_file = Path(tmpdir) / "image.svg"
                            svg_file.write_text(minified, encoding="utf-8")
            except Exception:
                pass

        cmd = [
            sys.executable,
            str(script_path),
            "--board", board,
            "--title_file", str(title_file.resolve()),
            "--content_file", str(content_file.resolve()),
            "--summary_only",
        ]
        if svg_file is not None:
            cmd.extend(["--svg_file", str(svg_file.resolve())])
        result = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=dict(os.environ),
        )
        stdout = (result.stdout or "") if result.stdout else ""
        stderr = (result.stderr or "") if result.stderr else ""

        if result.returncode != 0:
            err_msg = stderr.strip() or stdout.strip() or f"exit code {result.returncode}"
            return {"ok": False, "error": err_msg[:500]}

        thread_result = _parse_stdout_for_thread_result(stdout)
        if not thread_result:
            return {"ok": False, "error": "Script succeeded but no thread_id/thread_url in output"}

        # Append PostTrace to posts_trace.jsonl on success (Chapter 2B)
        if post_trace_result and post_trace_result.get("post_trace") and post_trace_result.get("append_trace"):
            try:
                post_trace_result["append_trace"](root, "fourclaw-auto-post", post_trace_result["post_trace"])
            except Exception:
                pass

        return {
            "ok": True,
            "outputs": thread_result,
            "returncode": result.returncode,
            "stdout_tail": stdout[-500:] if len(stdout) > 500 else stdout,
        }
    finally:
        try:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass
