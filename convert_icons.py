#!/usr/bin/env python3
"""Convert official SVG icons to PNG format for QGIS plugin."""
import os
import sys

try:
    import cairosvg
    HAS_CAIRO = True
except ImportError:
    HAS_CAIRO = False

try:
    from PyQt5.QtSvg import QSvgRenderer
    from PyQt5.QtGui import QImage, QPainter
    from PyQt5.QtCore import QRectF, Qt
    HAS_QT = True
except ImportError:
    try:
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtGui import QImage, QPainter
        from PyQt6.QtCore import QRectF, Qt
        HAS_QT = True
    except ImportError:
        HAS_QT = False


def convert_svg_to_png(svg_path, png_path, size=48):
    """Convert SVG to PNG using cairosvg or Qt."""
    if HAS_QT:
        r = QSvgRenderer(svg_path)
        if not r.isValid():
            return False
        default_size = r.defaultSize()
        w, h = max(1, default_size.width()), max(1, default_size.height())
        padding = 2
        target_area = size - padding * 2
        if w > h:
            target_w = target_area
            target_h = target_area * (h / w)
        else:
            target_h = target_area
            target_w = target_area * (w / h)
        x = padding + (target_area - target_w) / 2
        y = padding + (target_area - target_h) / 2

        img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent if hasattr(Qt, 'GlobalColor') else Qt.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing if hasattr(QPainter, 'RenderHint') else QPainter.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform if hasattr(QPainter, 'RenderHint') else QPainter.SmoothPixmapTransform)
        r.render(p, QRectF(x, y, target_w, target_h))
        p.end()
        img.save(png_path)
        print(f"[OK] Converted (via Qt): {os.path.basename(svg_path)} -> {os.path.basename(png_path)}")
        return True
    elif HAS_CAIRO:
        try:
            cairosvg.svg2png(url=svg_path, write_to=png_path, output_width=size, output_height=size)
            print(f"[OK] Converted (via Cairo): {os.path.basename(svg_path)} -> {os.path.basename(png_path)}")
            return True
        except Exception as e:
            print(f"[FAIL] Failed to convert {svg_path}: {e}")
            return False
    else:
        print("ERROR: Neither PyQt nor cairosvg is installed.")
        print("Install with: pip install PyQt5 pillow  OR  pip install cairosvg pillow")
        return False


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    img_dir = os.path.join(script_dir, "img")

    icons = [
        ("icon_maps.svg", "icon_maps.png"),
        ("icon_earth.svg", "icon_earth.png"),
        ("icon_streetview.svg", "icon_streetview.png"),
    ]

    print("Converting official SVG icons to PNG format...")
    print("-" * 50)

    success_count = 0
    for svg_name, png_name in icons:
        svg_path = os.path.join(img_dir, svg_name)
        png_path = os.path.join(img_dir, png_name)
        if not os.path.exists(svg_path):
            print(f"[WARN] Skipping {svg_name} (not found)")
            continue
        if convert_svg_to_png(svg_path, png_path):
            success_count += 1

    print("-" * 50)
    print(f"Converted {success_count}/{len(icons)} icons successfully.")


if __name__ == "__main__":
    main()
