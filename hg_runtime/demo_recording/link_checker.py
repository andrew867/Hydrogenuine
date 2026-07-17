"""Local link checker for dashboard HTML.

Checks that all src/href references point to local files that exist.
No external network. No mutation. Screenshot is not proof.
"""

from __future__ import annotations

import os
import re


def check_local_links(*, dashboard_dir: str) -> dict:
    index_path = os.path.join(dashboard_dir, "index.html")
    if not os.path.isfile(index_path):
        return {"error": "index.html not found", "broken": [], "ok": []}

    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    link_pattern = re.compile(r'(?:src|href)=["\']([^"\']+)["\']')
    broken = []
    ok = []

    for match in link_pattern.finditer(html):
        ref = match.group(1)
        if ref.startswith(("http://", "https://", "data:", "javascript:", "#", "mailto:")):
            continue
        target = os.path.normpath(os.path.join(dashboard_dir, ref))
        if os.path.exists(target):
            ok.append(ref)
        else:
            broken.append(ref)

    return {
        "broken": broken,
        "ok": ok,
        "broken_count": len(broken),
        "ok_count": len(ok),
        "all_ok": len(broken) == 0,
    }
