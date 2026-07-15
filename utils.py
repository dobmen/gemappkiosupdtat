import os
from PyQt6.QtCore import QByteArray, QRect, Qt
from PyQt6.QtGui import QIcon, QPainter, QPainterPath, QPixmap
from PyQt6.QtSvg import QSvgRenderer

DEFAULT_SVG_ICON = """
<svg viewBox="0 0 24 24" fill="none" stroke="#A0A0AB" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <rect x="3" y="3" width="7" height="7" rx="1.5"/>
    <rect x="14" y="3" width="7" height="7" rx="1.5"/>
    <rect x="14" y="14" width="7" height="7" rx="1.5"/>
    <rect x="3" y="14" width="7" height="7" rx="1.5"/>
</svg>
"""


def load_app_icon(file_path=None, size=80):
    """Loads an icon with a fallback chain: PNG -> SVG -> placeholder.svg -> default vector string.

    Applies an 80x80 circular clipping mask to both PNGs and SVGs.
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    # Apply circular clipping path so square PNGs/SVGs get cleanly cut into circles
    clip_path = QPainterPath()
    clip_path.addEllipse(0, 0, size, size)
    painter.setClipPath(clip_path)

    # Smart path resolution: strip extensions to check for both .png and .svg
    base_path = None
    if file_path:
        if file_path.endswith(".png") or file_path.endswith(".svg"):
            base_path = file_path[:-4]
        else:
            base_path = file_path

    png_path = f"{base_path}.png" if base_path else None
    svg_path = f"{base_path}.svg" if base_path else None

    # 1. PRIORITY: Check if a PNG version exists
    if png_path and os.path.exists(png_path):
        source_pixmap = QPixmap(png_path)
        # Draw PNG scaled smoothly into our 80x80 circular canvas
        painter.drawPixmap(QRect(0, 0, size, size), source_pixmap)
        painter.end()
        return QIcon(pixmap)

    # 2. FALLBACK: Check if an SVG version exists
    if svg_path and os.path.exists(svg_path):
        renderer = QSvgRenderer(svg_path)
    # 3. FALLBACK: Check for folder-based placeholder.svg
    elif os.path.exists("icons/placeholder.svg"):
        renderer = QSvgRenderer("icons/placeholder.svg")
    # 4. SAFETY NET: In-memory vector string
    else:
        renderer = QSvgRenderer(QByteArray(DEFAULT_SVG_ICON.encode("utf-8")))

    # Render vector across full dimensions of the canvas
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


# Keep alias for backwards compatibility with existing components
load_svg_icon = load_app_icon