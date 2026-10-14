#!/usr/bin/env python3
"""Generate official PNG icons for Lazy Earth & Maps QGIS plugin."""
import os
import shutil

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

try:
    from PIL import Image, ImageDraw, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def render_svg_to_png(svg_path, png_path, size=48, padding=2):
    """Render SVG to crisp anti-aliased PNG using QtSvg."""
    if not HAS_QT:
        return False
    r = QSvgRenderer(svg_path)
    if not r.isValid():
        return False
    default_size = r.defaultSize()
    w, h = max(1, default_size.width()), max(1, default_size.height())

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
    return True


def build_composite_plugin_icon(img_dir):
    """Create the main plugin icon combining official Earth globe and Maps pin."""
    if not HAS_PIL or not HAS_QT:
        return False
    earth_svg = os.path.join(img_dir, "icon_earth.svg")
    maps_svg = os.path.join(img_dir, "icon_maps.svg")
    if not (os.path.exists(earth_svg) and os.path.exists(maps_svg)):
        return False

    r_earth = QSvgRenderer(earth_svg)
    r_maps = QSvgRenderer(maps_svg)

    base = Image.new("RGBA", (192, 192), (0, 0, 0, 0))

    # Earth layer (140x140)
    e_img = QImage(140, 140, QImage.Format_ARGB32_Premultiplied)
    e_img.fill(Qt.GlobalColor.transparent if hasattr(Qt, 'GlobalColor') else Qt.transparent)
    pe = QPainter(e_img)
    pe.setRenderHint(QPainter.RenderHint.Antialiasing if hasattr(QPainter, 'RenderHint') else QPainter.Antialiasing)
    pe.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform if hasattr(QPainter, 'RenderHint') else QPainter.SmoothPixmapTransform)
    r_earth.render(pe, QRectF(0, 0, 140, 140))
    pe.end()

    # Save temp and load with PIL
    tmp_earth = os.path.join(img_dir, "_tmp_earth.png")
    e_img.save(tmp_earth)
    e_pil = Image.open(tmp_earth)
    base.paste(e_pil, (10, 16), e_pil)

    # Maps pin layer (90x130)
    m_img = QImage(90, 130, QImage.Format_ARGB32_Premultiplied)
    m_img.fill(Qt.GlobalColor.transparent if hasattr(Qt, 'GlobalColor') else Qt.transparent)
    pm = QPainter(m_img)
    pm.setRenderHint(QPainter.RenderHint.Antialiasing if hasattr(QPainter, 'RenderHint') else QPainter.Antialiasing)
    pm.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform if hasattr(QPainter, 'RenderHint') else QPainter.SmoothPixmapTransform)
    r_maps.render(pm, QRectF(0, 0, 90, 130))
    pm.end()

    tmp_maps = os.path.join(img_dir, "_tmp_maps.png")
    m_img.save(tmp_maps)
    m_pil = Image.open(tmp_maps)

    # Soft pin drop shadow
    shadow = Image.new("RGBA", (192, 192), (0, 0, 0, 0))
    shadow.paste(Image.new("RGBA", m_pil.size, (0, 0, 0, 140)), (92, 48), m_pil.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(6))
    base = Image.alpha_composite(base, shadow)
    base.paste(m_pil, (90, 44), m_pil)

    # Downscale smoothly to 48x48
    plugin_icon = base.resize((48, 48), Image.LANCZOS)
    plugin_icon.save(os.path.join(img_dir, "icon.png"))

    # Cleanup temp
    for tmp in (tmp_earth, tmp_maps):
        if os.path.exists(tmp):
            os.remove(tmp)
    return True


def build_send_icon(img_dir):
    """Build the Earth export & send icon."""
    if not HAS_PIL or not HAS_QT:
        return False
    earth_svg = os.path.join(img_dir, "icon_earth.svg")
    r_earth = QSvgRenderer(earth_svg)

    e_img = QImage(150, 150, QImage.Format_ARGB32_Premultiplied)
    e_img.fill(Qt.GlobalColor.transparent if hasattr(Qt, 'GlobalColor') else Qt.transparent)
    pe = QPainter(e_img)
    pe.setRenderHint(QPainter.RenderHint.Antialiasing if hasattr(QPainter, 'RenderHint') else QPainter.Antialiasing)
    pe.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform if hasattr(QPainter, 'RenderHint') else QPainter.SmoothPixmapTransform)
    r_earth.render(pe, QRectF(0, 0, 150, 150))
    pe.end()

    tmp_e = os.path.join(img_dir, "_tmp_esend.png")
    e_img.save(tmp_e)
    e_pil = Image.open(tmp_e)

    send_base = Image.new("RGBA", (192, 192), (0, 0, 0, 0))
    send_base.paste(e_pil, (10, 20), e_pil)

    # Badge shadow
    bx, by, br = 138, 54, 38
    b_shadow = Image.new("RGBA", (192, 192), (0, 0, 0, 0))
    sd = ImageDraw.Draw(b_shadow)
    sd.ellipse([bx - br - 2, by - br + 4, bx + br + 2, by + br + 8], fill=(0, 0, 0, 140))
    b_shadow = b_shadow.filter(ImageFilter.GaussianBlur(6))
    send_base = Image.alpha_composite(send_base, b_shadow)

    badge = Image.new("RGBA", (192, 192), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    draw.ellipse([bx - br, by - br, bx + br, by + br], fill=(52, 168, 83, 255), outline=(255, 255, 255, 255), width=5)
    arrow_pts = [
        (bx, by - 22),
        (bx + 18, by - 4),
        (bx + 8, by - 4),
        (bx + 8, by + 18),
        (bx - 8, by + 18),
        (bx - 8, by - 4),
        (bx - 18, by - 4),
    ]
    draw.polygon(arrow_pts, fill=(255, 255, 255, 255))
    send_base = Image.alpha_composite(send_base, badge)
    send_icon = send_base.resize((48, 48), Image.LANCZOS)
    send_icon.save(os.path.join(img_dir, "icon_send.png"))

    if os.path.exists(tmp_e):
        os.remove(tmp_e)
    return True


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    img_dir = os.path.join(script_dir, "img")

    print("Building official Lazy Earth & Maps icons...")
    print("-" * 50)

    # Render SVGs to PNG
    render_svg_to_png(os.path.join(img_dir, "icon_maps.svg"), os.path.join(img_dir, "icon_maps.png"), 48)
    print("[OK] Created: icon_maps.png (Official Google Maps 2020 pin)")

    render_svg_to_png(os.path.join(img_dir, "icon_earth.svg"), os.path.join(img_dir, "icon_earth.png"), 48)
    print("[OK] Created: icon_earth.png (Official Google Earth ribbon globe)")

    render_svg_to_png(os.path.join(img_dir, "icon_streetview.svg"), os.path.join(img_dir, "icon_streetview.png"), 48)
    print("[OK] Created: icon_streetview.png (Official Google Street View logo)")

    build_composite_plugin_icon(img_dir)
    print("[OK] Created: icon.png (Composite Earth + Maps pin)")

    build_send_icon(img_dir)
    print("[OK] Created: icon_send.png (Earth globe + export badge)")

    print("-" * 50)
    print("All icons successfully generated in img/ folder.")


if __name__ == "__main__":
    main()
