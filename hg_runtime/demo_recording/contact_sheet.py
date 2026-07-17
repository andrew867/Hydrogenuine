"""Contact sheet generator from dashboard screenshots.

Uses PIL/Pillow to create a grid of all captured views.
Falls back to HTML contact sheet if PIL unavailable.
Screenshot is not proof. Dashboard display is not truth.
"""

from __future__ import annotations

import os

_HAS_PIL = False
try:
    from PIL import Image, ImageDraw, ImageFont
    _HAS_PIL = True
except ImportError:
    pass


def generate_contact_sheet(
    *,
    screenshots_dir: str,
    out_path: str,
    columns: int = 3,
    thumb_width: int = 580,
    padding: int = 16,
    bg_color: tuple = (250, 248, 245),
    label_height: int = 28,
) -> str:
    """Generate a contact sheet PNG from screenshots. Returns output path."""
    if not _HAS_PIL:
        return _generate_html_fallback(screenshots_dir=screenshots_dir, out_path=out_path)

    files = sorted(
        [f for f in os.listdir(screenshots_dir) if f.endswith(".png")],
    )
    if not files:
        return ""

    images = []
    for f in files:
        img = Image.open(os.path.join(screenshots_dir, f))
        label = f.replace(".png", "").replace("_", " ")
        if label and label[0].isdigit():
            label = label.split(" ", 1)[-1] if " " in label else label
        images.append((img, label, f))

    aspect = images[0][0].height / images[0][0].width if images[0][0].width > 0 else 0.5625
    thumb_height = int(thumb_width * aspect)

    rows = (len(images) + columns - 1) // columns
    sheet_w = columns * thumb_width + (columns + 1) * padding
    sheet_h = rows * (thumb_height + label_height) + (rows + 1) * padding + 60

    sheet = Image.new("RGB", (sheet_w, sheet_h), bg_color)
    draw = ImageDraw.Draw(sheet)

    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except (OSError, IOError):
        font = ImageFont.load_default()

    title = "Hydrogenuine Dashboard — Contact Sheet"
    draw.text((padding, padding // 2), title, fill=(26, 26, 26), font=font)

    for idx, (img, label, fname) in enumerate(images):
        col = idx % columns
        row = idx // columns
        x = padding + col * (thumb_width + padding)
        y = 40 + padding + row * (thumb_height + label_height + padding)

        thumb = img.resize((thumb_width, thumb_height), Image.LANCZOS)
        sheet.paste(thumb, (x, y))

        draw.text((x, y + thumb_height + 4), label.title(), fill=(100, 100, 100), font=font)

    footer_y = sheet_h - 30
    try:
        small_font = ImageFont.truetype("arial.ttf", 12)
    except (OSError, IOError):
        small_font = ImageFont.load_default()
    draw.text(
        (padding, footer_y),
        "Screenshot is not proof. Dashboard display is not truth. Source is not truth.",
        fill=(180, 150, 100),
        font=small_font,
    )

    sheet.save(out_path, "PNG")
    return out_path


def _generate_html_fallback(*, screenshots_dir: str, out_path: str) -> str:
    """Generate HTML contact sheet if PIL unavailable."""
    html_path = out_path.replace(".png", ".html")
    files = sorted([f for f in os.listdir(screenshots_dir) if f.endswith(".png")])

    lines = [
        "<!DOCTYPE html><html><head><title>Contact Sheet</title>",
        "<style>",
        "body { background: #faf8f5; font-family: system-ui; padding: 1em; }",
        ".grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1em; }",
        ".cell img { width: 100%; border: 1px solid #d4cfc7; border-radius: 4px; }",
        ".cell label { display: block; text-align: center; font-size: 0.85em; color: #666; margin-top: 0.3em; }",
        ".footer { margin-top: 2em; font-size: 0.8em; color: #b49664; }",
        "</style></head><body>",
        "<h1>Hydrogenuine Dashboard — Contact Sheet</h1>",
        '<div class="grid">',
    ]
    for f in files:
        label = f.replace(".png", "").replace("_", " ").title()
        rel = os.path.relpath(os.path.join(screenshots_dir, f), os.path.dirname(html_path)).replace("\\", "/")
        lines.append(f'<div class="cell"><img src="{rel}" alt="{label}"><label>{label}</label></div>')
    lines.extend([
        "</div>",
        '<p class="footer">Screenshot is not proof. Dashboard display is not truth. Source is not truth.</p>',
        "</body></html>",
    ])

    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return html_path
