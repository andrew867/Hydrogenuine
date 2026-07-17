"""Minimal curses TUI for Agent Zero proof browser.

Read-only. No mutation. No network. Source is not truth.
STOP/PANIC always visible. Boundary doctrine always visible.
"""

from __future__ import annotations

import curses
import re

from hg_runtime.zero_cli.tui_data_model import TuiDataModel

BOUNDARY = "Source != truth | Screenshot != proof | Model output != truth | No self-authorization"

KEYMAP = {
    ord('q'): 'quit',
    ord('Q'): 'quit',
    27: 'quit',  # ESC
    curses.KEY_UP: 'nav_up',
    ord('k'): 'nav_up',
    curses.KEY_DOWN: 'nav_down',
    ord('j'): 'nav_down',
    ord('\t'): 'nav_down',
    ord('\n'): 'select',
    curses.KEY_ENTER: 'select',
}


def _sanitize(text: str) -> str:
    text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', str(text))
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text


def _safe_addstr(win, y: int, x: int, text: str, *args):
    h, w = win.getmaxyx()
    if y < 0 or y >= h or x < 0:
        return
    text = _sanitize(text)
    max_len = w - x - 1
    if max_len <= 0:
        return
    try:
        win.addnstr(y, x, text, max_len, *args)
    except curses.error:
        pass


def _draw_status_bar(stdscr, model: TuiDataModel):
    h, w = stdscr.getmaxyx()
    bar = f" Agent Zero | {model.gate_verdict} | STOP/PANIC: {model.stop_panic_status} | Promotions: {model.promotions_count} | Effects: {model.external_effects_count} "
    bar = bar[:w - 1]

    color = curses.color_pair(1) if model.gate_verdict == "GREEN" else curses.color_pair(2)
    _safe_addstr(stdscr, 0, 0, bar.ljust(w - 1), color | curses.A_BOLD)


def _draw_nav(stdscr, model: TuiDataModel):
    h, w = stdscr.getmaxyx()
    nav_width = 22
    counts = model.nav_counts()

    for i, (key, label) in enumerate(model.nav_items):
        y = i + 2
        if y >= h - 2:
            break
        count = counts.get(key, "")
        text = f" {label}"
        if count:
            text += f" ({count})"
        text = text[:nav_width - 1]

        if i == model.nav_index:
            attr = curses.A_REVERSE | curses.A_BOLD
        else:
            attr = curses.A_NORMAL

        _safe_addstr(stdscr, y, 0, text.ljust(nav_width), attr)


def _draw_boundary_bar(stdscr):
    h, w = stdscr.getmaxyx()
    _safe_addstr(stdscr, h - 1, 0, BOUNDARY[:w - 1].ljust(w - 1), curses.color_pair(3))


def _render_overview(stdscr, model: TuiDataModel, x: int, y: int, w: int, h: int):
    o = model.overview
    lines = [
        f"Gate:             {o.get('gate_verdict', 'UNKNOWN')} ({o.get('gate_checks_passed', 0)}/{o.get('gate_checks_total', 0)})",
        f"Cycles:           {o.get('cycles', 0)}",
        f"Sources:          {o.get('successful_fetches', 0)}/{o.get('sources_attempted', 0)}",
        f"Screenshots:      {o.get('screenshots_captured', 0)}",
        f"Model inferences: {o.get('model_successes', 0)}/{o.get('model_attempts', 0)}",
        f"Contradictions:   {o.get('contradictions', 0)}",
        f"Quarantined:      {o.get('quarantine_entries', 0)}",
        f"Promotions:       {o.get('promotions_count', 0)}",
        f"External effects: {o.get('external_effects_count', 0)}",
        f"Claim flags:      {o.get('public_claim_flags', 0)}",
        f"STOP/PANIC:       {model.stop_panic_status}",
    ]
    for i, line in enumerate(lines):
        if y + i >= h - 2:
            break
        _safe_addstr(stdscr, y + i, x, line[:w - x - 1])


def _render_sources(stdscr, model: TuiDataModel, x: int, y: int, w: int, h: int):
    sources = model.sources
    header = f"{'ID':<14} {'URL':<40} {'Status':<8} {'HTTP':<5}"
    _safe_addstr(stdscr, y, x, header[:w - x - 1], curses.A_BOLD)
    for i, s in enumerate(sources):
        row_y = y + 1 + i
        if row_y >= h - 2:
            break
        line = f"{str(s.get('source_candidate_id', '')):<14} {str(s.get('url', ''))[:40]:<40} {str(s.get('status', '')):<8} {str(s.get('http_status', '')):<5}"
        _safe_addstr(stdscr, row_y, x, line[:w - x - 1])


def _render_witnesses(stdscr, model: TuiDataModel, x: int, y: int, w: int, h: int):
    witnesses = model.model_witnesses
    header = f"{'Cycle':<30} {'Model':<24} {'Status':<10} {'Chars':>6}"
    _safe_addstr(stdscr, y, x, header[:w - x - 1], curses.A_BOLD)
    for i, w_item in enumerate(witnesses):
        row_y = y + 1 + i
        if row_y >= h - 2:
            break
        line = f"{str(w_item.get('cycle_id', '')):<30} {str(w_item.get('model_name', '') or '(skip)'):<24} {str(w_item.get('inference_status', '')):<10} {str(w_item.get('output_chars', 0)):>6}"
        _safe_addstr(stdscr, row_y, x, line[:w - x - 1])


def _render_quarantine(stdscr, model: TuiDataModel, x: int, y: int, w: int, h: int):
    items = model.quarantine_items
    if not items:
        _safe_addstr(stdscr, y, x, "No quarantine items.")
        return
    header = f"{'Receipt':<18} {'Q':>3} {'P':>3} {'Promo':<6} {'Timestamp':<22}"
    _safe_addstr(stdscr, y, x, header[:w - x - 1], curses.A_BOLD)
    for i, q in enumerate(items):
        row_y = y + 1 + i
        if row_y >= h - 2:
            break
        line = f"{str(q.get('receipt_id', ''))[:16]:<18} {q.get('quarantined_count', 0):>3} {q.get('promoted_count', 0):>3} {'false':<6} {str(q.get('timestamp', '')):<22}"
        _safe_addstr(stdscr, row_y, x, line[:w - x - 1])


def _render_help(stdscr, x: int, y: int, w: int, h: int):
    lines = [
        "KEYS:",
        "  j/Down  - Navigate down",
        "  k/Up    - Navigate up",
        "  Enter   - Select view",
        "  q/ESC   - Quit",
        "",
        "VIEWS:",
        "  Overview, Sources, Screenshots, Model Witnesses,",
        "  Evidence Graph, Contradictions, Quarantine,",
        "  Public Claims, Gates, Receipts, Demo Script",
        "",
        "DOCTRINE:",
        "  Source is not truth.",
        "  Screenshot is not proof.",
        "  Model output is not truth.",
        "  Evidence graph edge is not proof.",
        "  Candidate knowledge is not knowledge.",
        "  No self-authorization.",
    ]
    for i, line in enumerate(lines):
        if y + i >= h - 2:
            break
        _safe_addstr(stdscr, y + i, x, line[:w - x - 1])


def _render_main(stdscr, model: TuiDataModel, x: int, y: int, w: int, h: int):
    view = model.current_view
    title = dict(model.nav_items).get(view, view)
    _safe_addstr(stdscr, y, x, f"[ {title} ]", curses.A_BOLD | curses.A_UNDERLINE)
    content_y = y + 2

    if view == "overview":
        _render_overview(stdscr, model, x, content_y, w, h)
    elif view == "sources":
        _render_sources(stdscr, model, x, content_y, w, h)
    elif view == "witnesses":
        _render_witnesses(stdscr, model, x, content_y, w, h)
    elif view == "quarantine":
        _render_quarantine(stdscr, model, x, content_y, w, h)
    elif view == "help":
        _render_help(stdscr, x, content_y, w, h)
    else:
        _safe_addstr(stdscr, content_y, x, f"View '{view}' — data loaded. Use j/k to navigate.")


def _main_loop(stdscr, model: TuiDataModel):
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        _draw_status_bar(stdscr, model)
        _draw_nav(stdscr, model)
        _draw_boundary_bar(stdscr)

        nav_width = 23
        _render_main(stdscr, model, nav_width, 2, w, h)

        stdscr.refresh()

        key = stdscr.getch()
        action = KEYMAP.get(key)

        if action == 'quit':
            break
        elif action == 'nav_up':
            model.nav_index -= 1
        elif action == 'nav_down':
            model.nav_index += 1
        elif action == 'select':
            pass


def run_curses_tui(model: TuiDataModel):
    """Launch the curses TUI."""
    curses.wrapper(lambda stdscr: _main_loop(stdscr, model))
