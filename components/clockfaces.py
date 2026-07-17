import os
import json
from PyQt6.QtCore import Qt, QTime, QDate, QPoint, QRect, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, pyqtProperty, QSize
from PyQt6.QtGui import QFont, QPainter, QPainterPath, QPen, QColor, QBrush, QPolygon, QLinearGradient, QPixmap, QIcon
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QStackedWidget, QScrollArea, QScroller, QSizePolicy, QListWidget, QListWidgetItem

# =================================================================
# GLOBAL SETTINGS ENGINE
# =================================================================
def get_setting(key, default=None):
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                return json.load(f).get(key, default)
    except Exception: pass
    return default

def save_setting(key, value):
    cfg = {}
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                cfg = json.load(f)
    except Exception: pass
    cfg[key] = value
    try:
        with open("config.json", "w") as f:
            json.dump(cfg, f)
    except Exception: pass

def draw_custom_background(painter, bg_val, w, h):
    """Dynamically parses and paints Hex, Gradients, or Images (with pan/scale) to the clockface."""
    if bg_val.startswith("#"):
        painter.fillRect(0, 0, w, h, QColor(bg_val))
    elif bg_val.startswith("grad:"):
        parts = bg_val.split(":")
        if len(parts) == 3:
            grad = QLinearGradient(0, 0, w, h)
            grad.setColorAt(0.0, QColor(parts[1]))
            grad.setColorAt(1.0, QColor(parts[2]))
            painter.fillRect(0, 0, w, h, grad)
    elif bg_val.startswith("img:"):
        # Format: img:path|pan_x|pan_y|mode
        parts = bg_val.split("|")
        path = parts[0][4:]
        pan_x = float(parts[1]) if len(parts) > 1 else 0.0
        pan_y = float(parts[2]) if len(parts) > 2 else 0.0
        mode = parts[3] if len(parts) > 3 else "fill"

        if os.path.exists(path):
            pix = QPixmap(path)
            if not pix.isNull():
                painter.fillRect(0, 0, w, h, QColor(0, 0, 0)) # Base black for 'fit' mode bars
                if mode == "fit":
                    scaled = pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                else:
                    scaled = pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                
                x = (w - scaled.width()) / 2.0 + pan_x
                y = (h - scaled.height()) / 2.0 + pan_y
                painter.drawPixmap(int(x), int(y), scaled)
        else:
            painter.fillRect(0, 0, w, h, QColor(12, 12, 14))
    else:
        painter.fillRect(0, 0, w, h, QColor(12, 12, 14))


class FadeOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self._alpha = 0
        self.hide()

    @pyqtProperty(int)
    def alpha(self):
        return self._alpha

    @alpha.setter
    def alpha(self, value):
        self._alpha = value
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(12, 12, 14, self._alpha))


# =================================================================
# CUSTOM UI WIDGETS
# =================================================================
class ImagePickerButton(QPushButton):
    """Small button for the 5-recent photos row."""
    def __init__(self, path, callback):
        super().__init__()
        self.callback = callback
        self.path = path
        self.setFixedSize(80, 80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QPushButton { background-color: #1C1C22; border-radius: 12px; border: 2px solid rgba(255,255,255,40); } QPushButton:hover { border-color: #5A8DEF; }")
        
        pix = QPixmap(path)
        if not pix.isNull():
            side = min(pix.width(), pix.height())
            x = (pix.width() - side) // 2
            y = (pix.height() - side) // 2
            cropped = pix.copy(x, y, side, side)
            scaled = cropped.scaled(76, 76, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            
            rounded = QPixmap(76, 76)
            rounded.fill(Qt.GlobalColor.transparent)
            p = QPainter(rounded)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            path_obj = QPainterPath()
            path_obj.addRoundedRect(0, 0, 76, 76, 10, 10)
            p.setClipPath(path_obj)
            p.drawPixmap(0, 0, scaled)
            p.end()
            self.setIcon(QIcon(rounded))
            self.setIconSize(QSize(76, 76))
            
        self.clicked.connect(lambda: self.callback(self.path))

class GalleryGridButton(QPushButton):
    """Large button for the 'All Photos' gallery overlay grid."""
    def __init__(self, path, click_cb):
        super().__init__()
        self.path = path
        self.setFixedSize(160, 160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QPushButton { background-color: #1C1C22; border-radius: 16px; border: 1px solid #2C2C35; } QPushButton:hover { border-color: #5A8DEF; }")
        
        pix = QPixmap(path)
        if not pix.isNull():
            side = min(pix.width(), pix.height())
            x = (pix.width() - side) // 2
            y = (pix.height() - side) // 2
            cropped = pix.copy(x, y, side, side)
            scaled = cropped.scaled(156, 156, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            
            rounded = QPixmap(156, 156)
            rounded.fill(Qt.GlobalColor.transparent)
            p = QPainter(rounded)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            path_obj = QPainterPath()
            path_obj.addRoundedRect(0, 0, 156, 156, 14, 14)
            p.setClipPath(path_obj)
            p.drawPixmap(0, 0, scaled)
            p.end()
            self.setIcon(QIcon(rounded))
            self.setIconSize(QSize(156, 156))
            
        self.clicked.connect(lambda: click_cb(self.path))


# =================================================================
# CLOCKFACE RENDERING ENGINES
# =================================================================
class ClassicClock(QWidget):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_time = QLabel()
        self.lbl_time.setFont(QFont("Google Sans", 95, QFont.Weight.Bold))
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_date = QLabel()
        self.lbl_date.setFont(QFont("Google Sans", 24))
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_time)
        layout.addWidget(self.lbl_date)
        self.load_settings()

    def sizeHint(self):
        return QSize(1024, 600)

    def minimumSizeHint(self):
        return QSize(100, 100)

    def load_settings(self):
        self.color = get_setting("classic_color", "#FFFFFF")
        self.bg = get_setting("classic_bg", "#0C0C0E")
        self.lbl_time.setStyleSheet(f"color: {self.color}; background: transparent;")
        self.lbl_date.setStyleSheet(f"color: {self.color}; background: transparent;")
        self.update()

    def update_time(self, t, d):
        self.lbl_time.setText(t.toString("HH:mm"))
        self.lbl_date.setText(d.toString("dddd, MMMM d"))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        radius = 36 if self.width() < 1000 else 0
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), radius, radius)
        painter.setClipPath(path)
        draw_custom_background(painter, self.bg, self.width(), self.height())


class StackedClock(QWidget):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(0)
        
        self.lbl_hour = QLabel()
        self.lbl_hour.setFont(QFont("Google Sans", 115, QFont.Weight.Bold))
        self.lbl_hour.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_minute = QLabel()
        self.lbl_minute.setFont(QFont("Google Sans", 115, QFont.Weight.Bold))
        self.lbl_minute.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_date = QLabel()
        self.lbl_date.setFont(QFont("Google Sans", 20))
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.lbl_hour)
        layout.addWidget(self.lbl_minute)
        layout.addSpacing(15) 
        layout.addWidget(self.lbl_date)
        self.load_settings()

    def sizeHint(self):
        return QSize(1024, 600)

    def minimumSizeHint(self):
        return QSize(100, 100)

    def load_settings(self):
        self.hour_color = get_setting("stacked_hour", "#FFFFFF")
        self.min_color = get_setting("stacked_min", "#5A8DEF")
        self.bg = get_setting("stacked_bg", "#0C0C0E")
        self.lbl_hour.setStyleSheet(f"color: {self.hour_color}; background: transparent; margin-bottom: -25px;")
        self.lbl_minute.setStyleSheet(f"color: {self.min_color}; background: transparent; margin-top: -25px;")
        self.lbl_date.setStyleSheet("color: #AAAAAA; background: transparent;")
        self.update()

    def update_time(self, t, d):
        self.lbl_hour.setText(t.toString("HH"))
        self.lbl_minute.setText(t.toString("mm"))
        self.lbl_date.setText(d.toString("dddd, MMM d"))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        radius = 36 if self.width() < 1000 else 0
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), radius, radius)
        painter.setClipPath(path)
        draw_custom_background(painter, self.bg, self.width(), self.height())


class AnalogClock(QWidget):
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.time = QTime.currentTime()
        self.date = QDate.currentDate()
        self.load_settings()

    def sizeHint(self):
        return QSize(1024, 600)

    def minimumSizeHint(self):
        return QSize(100, 100)

    def load_settings(self):
        self.theme = get_setting("analog_theme", "dark")
        self.update()

    def update_time(self, t, d):
        self.time = t
        self.date = d
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        radius = 36 if self.width() < 1000 else 0
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), radius, radius)
        painter.setClipPath(path)
        
        is_light = (self.theme == "light")
        bg_col = QColor(245, 245, 245) if is_light else QColor(12, 12, 14)
        painter.fillRect(0, 0, self.width(), self.height(), bg_col)
        
        side = min(self.width(), self.height())
        painter.translate(self.width() / 2.0, self.height() / 2.0)
        painter.scale(side / 320.0, side / 320.0)

        ring_col = QColor(200, 200, 200) if is_light else QColor(40, 40, 50)
        painter.setPen(QPen(ring_col, 6))
        painter.drawEllipse(QPoint(0,0), 145, 145)

        tick_col = QColor(100, 100, 100) if is_light else QColor(255, 255, 255, 150)
        painter.setPen(QPen(tick_col, 3))
        for i in range(12):
            painter.drawLine(0, -125, 0, -135)
            painter.rotate(30.0)

        hour_hand = QPolygon([QPoint(6, 12), QPoint(-6, 12), QPoint(0, -75)])
        h_col = QColor(40, 40, 40) if is_light else QColor(255, 255, 255)
        painter.setBrush(QBrush(h_col))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.save()
        painter.rotate(30.0 * ((self.time.hour() + self.time.minute() / 60.0)))
        painter.drawPolygon(hour_hand)
        painter.restore()

        min_hand = QPolygon([QPoint(4, 12), QPoint(-4, 12), QPoint(0, -115)])
        painter.setBrush(QBrush(QColor(90, 141, 239)))
        painter.save()
        painter.rotate(6.0 * (self.time.minute() + self.time.second() / 60.0))
        painter.drawPolygon(min_hand)
        painter.restore()

        sec_hand = QPolygon([QPoint(2, 12), QPoint(-2, 12), QPoint(0, -125)])
        painter.setBrush(QBrush(QColor(226, 74, 74)))
        painter.save()
        painter.rotate(6.0 * self.time.second())
        painter.drawPolygon(sec_hand)
        painter.restore()

        c_col = QColor(40, 40, 40) if is_light else QColor(255, 255, 255)
        painter.setBrush(QBrush(c_col))
        painter.drawEllipse(QPoint(0,0), 6, 6)
        painter.end()


CLOCKFACES = [
    ("Classic Digital", ClassicClock),
    ("Stacked Bold", StackedClock),
    ("Minimal Analog", AnalogClock)
]
CLOCKFACE_CLASSES = [cls for name, cls in CLOCKFACES]


# =================================================================
# PHOTO ADJUSTMENT OVERLAY (Drag to Pan & Fit/Fill)
# =================================================================
class ImageAdjusterOverlay(QFrame):
    def __init__(self, parent, apply_callback):
        super().__init__(parent)
        self.apply_callback = apply_callback
        self.setGeometry(0, 0, 1024, 600)
        self.setStyleSheet("background-color: #000000;")
        self.hide()
        
        self.path = ""
        self.setting_key = ""
        self.mode = "fill"
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.pix = QPixmap()
        self.last_mouse = None
        
        # Transparent UI Overlays
        top_bar = QWidget(self)
        top_bar.setGeometry(0, 0, 1024, 90)
        top_bar.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(0,0,0,180), stop:1 rgba(0,0,0,0));")
        
        btn_cancel = QPushButton("Cancel", top_bar)
        btn_cancel.setGeometry(30, 25, 100, 40)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("background: rgba(255,255,255,30); color: white; border-radius: 20px; font-weight: bold; font-size: 15px;")
        btn_cancel.clicked.connect(self.hide)
        
        btn_done = QPushButton("Apply Background", top_bar)
        btn_done.setGeometry(1024 - 200, 25, 170, 40)
        btn_done.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_done.setStyleSheet("background: #5A8DEF; color: white; border-radius: 20px; font-weight: bold; font-size: 15px;")
        btn_done.clicked.connect(self.on_apply)

        bot_bar = QWidget(self)
        bot_bar.setGeometry(0, 500, 1024, 100)
        bot_bar.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(0,0,0,0), stop:1 rgba(0,0,0,180));")

        self.btn_toggle = QPushButton("Mode: Fill Screen", bot_bar)
        self.btn_toggle.setGeometry(1024//2 - 90, 30, 180, 45)
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setStyleSheet("background: #1C1C22; color: white; border-radius: 22px; border: 2px solid #5A8DEF; font-weight: bold; font-size: 15px;")
        self.btn_toggle.clicked.connect(self.toggle_mode)
        
        self.lbl_hint = QLabel("Drag to reposition", self)
        self.lbl_hint.setGeometry(0, 250, 1024, 100)
        self.lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_hint.setFont(QFont("Google Sans", 24, QFont.Weight.Bold))
        self.lbl_hint.setStyleSheet("color: rgba(255,255,255,100); background: transparent;")

    def setup(self, path, setting_key):
        self.path = path
        self.setting_key = setting_key
        self.pix = QPixmap(path)
        self.mode = "fill"
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.btn_toggle.setText("Mode: Fill Screen")
        self.lbl_hint.show()
        self.update()

    def toggle_mode(self):
        if self.mode == "fill":
            self.mode = "fit"
            self.btn_toggle.setText("Mode: Fit (Black Bars)")
        else:
            self.mode = "fill"
            self.btn_toggle.setText("Mode: Fill Screen")
        
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.clamp_pan()
        self.update()

    def mousePressEvent(self, event):
        self.last_mouse = event.position()
        self.lbl_hint.hide()

    def mouseMoveEvent(self, event):
        if self.last_mouse and not self.pix.isNull():
            delta = event.position() - self.last_mouse
            self.pan_x += delta.x()
            self.pan_y += delta.y()
            self.last_mouse = event.position()
            self.clamp_pan()
            self.update()

    def clamp_pan(self):
        if self.pix.isNull(): return
        w, h = 1024, 600
        if self.mode == "fill":
            scaled = self.pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            max_x = max(0.0, (scaled.width() - w) / 2.0)
            max_y = max(0.0, (scaled.height() - h) / 2.0)
            self.pan_x = max(-max_x, min(max_x, self.pan_x))
            self.pan_y = max(-max_y, min(max_y, self.pan_y))
        else:
            scaled = self.pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            max_x = max(0.0, (w - scaled.width()) / 2.0)
            max_y = max(0.0, (h - scaled.height()) / 2.0)
            self.pan_x = max(-max_x, min(max_x, self.pan_x))
            self.pan_y = max(-max_y, min(max_y, self.pan_y))

    def on_apply(self):
        val = f"img:{self.path}|{self.pan_x}|{self.pan_y}|{self.mode}"
        self.apply_callback(self.setting_key, val)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0))
        if self.pix.isNull(): return
        
        w, h = self.width(), self.height()
        if self.mode == "fit":
            scaled = self.pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        else:
            scaled = self.pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            
        x = (w - scaled.width()) / 2.0 + self.pan_x
        y = (h - scaled.height()) / 2.0 + self.pan_y
        p.drawPixmap(int(x), int(y), scaled)


# =================================================================
# ALL PHOTOS GALLERY OVERLAY
# =================================================================
class GalleryPickerOverlay(QFrame):
    def __init__(self, parent, photo_selected_callback):
        super().__init__(parent)
        self.photo_selected = photo_selected_callback
        self.setting_key = None
        self.setGeometry(0, 0, 1024, 600)
        self.setStyleSheet("background-color: #0C0C0E;")
        self.hide()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.albums = ["Photos", "Screenshots", "Videos"]
        self.current_selected_album = "Photos"
        self.ignored_folders = [".", "__", "apps", "components", "fonts", "icons", "venv", "browser_data"]
        
        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(240)
        self.sidebar.setStyleSheet("background-color: #14141A; border-right: 1px solid #22222A;")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(15, 30, 15, 20)
        
        lbl_title = QLabel("Albums")
        lbl_title.setFont(QFont("Google Sans", 15, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #666670; margin-left: 10px; margin-bottom: 10px;")
        sidebar_layout.addWidget(lbl_title)
        
        self.album_list_widget = QListWidget()
        QScroller.grabGesture(self.album_list_widget.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
        self.album_list_widget.setStyleSheet("""
            QListWidget { background: transparent; border: none; color: #AAAAAA; outline: 0; }
            QListWidget::item { padding: 12px 15px; margin-bottom: 4px; border-radius: 10px; font-weight: bold; font-size: 15px; }
            QListWidget::item:hover { background-color: rgba(255, 255, 255, 8); color: white; }
            QListWidget::item:selected { background-color: rgba(90, 141, 239, 30); color: #5A8DEF; }
        """)
        self.album_list_widget.itemClicked.connect(self.on_album_nav_clicked)
        sidebar_layout.addWidget(self.album_list_widget)
        
        btn_back = QPushButton("← Back to Editor")
        btn_back.setFixedHeight(45)
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.setStyleSheet("background: #2C2C35; color: white; border-radius: 12px; font-weight: bold; font-size: 15px; border: none;")
        btn_back.clicked.connect(self.hide)
        sidebar_layout.addWidget(btn_back)
        
        layout.addWidget(self.sidebar)
        
        # Grid
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(30, 25, 30, 30)
        
        self.lbl_album_title = QLabel("Photos")
        self.lbl_album_title.setFont(QFont("Google Sans", 28, QFont.Weight.Bold))
        self.lbl_album_title.setStyleSheet("color: white;")
        right_layout.addWidget(self.lbl_album_title)
        right_layout.addSpacing(10)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        QScroller.grabGesture(self.scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
        
        self.grid_container = QWidget()
        self.grid = QGridLayout(self.grid_container)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.grid.setSpacing(20)
        self.scroll.setWidget(self.grid_container)
        
        right_layout.addWidget(self.scroll)
        layout.addWidget(right_panel, stretch=1)
        
    def setup(self, setting_key):
        self.setting_key = setting_key
        self.scan_and_sync_local_albums()
        self.populate_sidebar_items()
        self.load_images()
        self.show()

    def scan_and_sync_local_albums(self):
        for d in ["photos", "screenshots", "videos"]:
            if not os.path.exists(d): os.makedirs(d, exist_ok=True)
            if d.title() not in self.albums: self.albums.append(d.title())
        for entry in os.listdir("."):
            if os.path.isdir(entry):
                if not any(entry.startswith(ig) for ig in self.ignored_folders) and entry not in ["photos", "screenshots", "videos"]:
                    if entry not in self.albums: self.albums.append(entry)

    def populate_sidebar_items(self):
        self.album_list_widget.clear()
        for folder in self.albums:
            item = QListWidgetItem(folder)
            self.album_list_widget.addItem(item)
            if folder == self.current_selected_album:
                self.album_list_widget.setCurrentItem(item)

    def on_album_nav_clicked(self, item):
        self.current_selected_album = item.text()
        self.lbl_album_title.setText(self.current_selected_album)
        self.load_images()

    def load_images(self):
        for i in reversed(range(self.grid.count())):
            w = self.grid.itemAt(i).widget()
            if w: w.deleteLater()
            
        target_dir = self.current_selected_album.lower() if self.current_selected_album in ["Screenshots", "Photos", "Videos"] else self.current_selected_album
        paths = []
        if os.path.exists(target_dir):
            for f in os.listdir(target_dir):
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    paths.append(os.path.join(target_dir, f))
                        
        paths.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        if not paths:
            lbl_empty = QLabel("No images in this album.")
            lbl_empty.setFont(QFont("Google Sans", 16))
            lbl_empty.setStyleSheet("color: #666670;")
            self.grid.addWidget(lbl_empty, 0, 0)
            return
            
        cols = 4
        for i, path in enumerate(paths):
            btn = GalleryGridButton(path, lambda p: self.photo_selected(p, self.setting_key))
            self.grid.addWidget(btn, i // cols, i % cols)


class ClockSelectorOverlay(QWidget):
    def __init__(self, parent, apply_callback):
        super().__init__(parent)
        self.apply_callback = apply_callback
        self.setGeometry(0, 0, 1024, 600)
        self.hide()
        
        self.main_container = QFrame(self)
        self.main_container.setGeometry(0, 0, 1024, 600)
        
        self.bg_fade = FadeOverlay(self.main_container)
        self.bg_fade.setGeometry(0, 0, 1024, 600)
        
        self.lbl_title = QLabel("Swipe to browse • Tap to apply", self.main_container)
        self.lbl_title.setGeometry(0, 10, 1024, 25)
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setFont(QFont("Google Sans", 13, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet("color: #888888; background: transparent;")
        self.lbl_title.hide()
        
        self.current_idx = 0
        self.previews = []
        self.wrappers = []
        self.name_labels = []
        self.border_frames = []
        
        for i, (name, Cls) in enumerate(CLOCKFACES):
            inst = Cls()
            wrapper = QFrame(self.main_container)
            wrapper.setStyleSheet("background-color: transparent;")
            
            l = QGridLayout(wrapper)
            l.setContentsMargins(0, 0, 0, 0)
            
            lbl_card_name = QLabel(name, self.main_container)
            lbl_card_name.setFont(QFont("Google Sans", 24, QFont.Weight.Bold))
            lbl_card_name.setStyleSheet("color: white; background: transparent; border: none;")
            lbl_card_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_card_name.hide()
            
            border_frame = QFrame()
            border_frame.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            border_frame.setStyleSheet("border: 2px solid #33333F; border-radius: 36px;")
            border_frame.hide()
            
            l.addWidget(inst, 0, 0)
            l.addWidget(border_frame, 0, 0)
            
            self.previews.append(inst)
            self.wrappers.append(wrapper)
            self.name_labels.append(lbl_card_name)
            self.border_frames.append(border_frame)
            wrapper.hide()

        self.btn_close = QPushButton("✕", self.main_container)
        self.btn_close.setGeometry(30, 30, 50, 50)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet("background: rgba(255,255,255,10); color: white; border-radius: 25px; font-size: 20px; border: none;")
        self.btn_close.clicked.connect(self.close_selector)
        self.btn_close.hide()

        self.btn_customize = QPushButton("⚙️ Customize", self.main_container)
        self.btn_customize.setGeometry(1024//2 - 80, 540, 160, 45)
        self.btn_customize.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_customize.setStyleSheet("background-color: #2C2C35; color: white; border-radius: 22px; font-weight: bold; font-size: 15px; border: none;")
        self.btn_customize.clicked.connect(self.open_editor)
        self.btn_customize.hide()

        self.setup_editor_panel()
        
        self.adjuster_overlay = ImageAdjusterOverlay(self.main_container, self.apply_adjusted_photo)
        self.gallery_picker = GalleryPickerOverlay(self.main_container, self.open_adjuster)
        
        self.swipe_start_x = None
        self.is_swiping = False
        self.is_editing = False
        self.saved_idx = 0

    # -----------------------------------------------------------------
    # CUSTOM EDITOR UI BUILDERS
    # -----------------------------------------------------------------
    def setup_editor_panel(self):
        self.edit_panel = QFrame(self.main_container)
        self.edit_panel.setGeometry(0, 600, 1024, 210)
        self.edit_panel.setStyleSheet("background-color: rgba(20, 20, 26, 250); border-top-left-radius: 24px; border-top-right-radius: 24px;")
        
        self.btn_done = QPushButton("Done", self.edit_panel)
        self.btn_done.setGeometry(1024 - 110, 15, 80, 35)
        self.btn_done.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_done.setStyleSheet("background-color: #5A8DEF; color: white; border-radius: 17px; font-weight: bold; border: none;")
        self.btn_done.clicked.connect(self.close_editor)
        
        self.edit_stack = QStackedWidget(self.edit_panel)
        self.edit_stack.setGeometry(30, 20, 1024 - 160, 170)
        self.edit_stack.setStyleSheet("background: transparent;")

        self.all_colors = [
            "#FFFFFF", "#CCCCCC", "#888888", "#000000",
            "#E24A4A", "#E91E63", "#9B59B6", "#673AB7",
            "#5A8DEF", "#03A9F4", "#00BCD4", "#009688",
            "#1ED760", "#4CAF50", "#8BC34A", "#CDDC39",
            "#FFEB3B", "#FFC107", "#FF9800", "#F39C12"
        ]
        
        self.all_bgs = [
            ("#0C0C0E", "background-color: #0C0C0E;"),
            ("grad:#5A8DEF:#9B59B6", "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #5A8DEF,stop:1 #9B59B6);"),
            ("grad:#E24A4A:#F39C12", "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #E24A4A,stop:1 #F39C12);"),
            ("grad:#1ED760:#03A9F4", "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #1ED760,stop:1 #03A9F4);"),
            ("grad:#E91E63:#673AB7", "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #E91E63,stop:1 #673AB7);"),
            ("grad:#FF9800:#E24A4A", "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #FF9800,stop:1 #E24A4A);")
        ]

        page0 = self.build_editor_page({
            "Clock Color": self.create_color_grid("classic_color"),
            "Colors & Gradients": self.create_bg_grid("classic_bg"),
            "My Photos": self.create_photo_grid("classic_bg")
        })
        page1 = self.build_editor_page({
            "Hour Color": self.create_color_grid("stacked_hour"),
            "Minute Color": self.create_color_grid("stacked_min"),
            "Colors & Gradients": self.create_bg_grid("stacked_bg"),
            "My Photos": self.create_photo_grid("stacked_bg")
        })
        page2 = self.build_editor_page({
            "Theme": self.create_analog_theme_widget()
        })
        
        self.edit_stack.addWidget(page0)
        self.edit_stack.addWidget(page1)
        self.edit_stack.addWidget(page2)

    def _apply_tab_style(self, btn, active):
        if active:
            btn.setStyleSheet("background-color: #5A8DEF; color: white; border-radius: 8px; font-weight: bold; text-align: left; padding-left: 15px;")
        else:
            btn.setStyleSheet("background-color: transparent; color: #AAAAAA; border-radius: 8px; font-weight: bold; text-align: left; padding-left: 15px;")

    def _switch_editor_tab(self, idx, stack, buttons):
        stack.setCurrentIndex(idx)
        for i, btn in enumerate(buttons):
            self._apply_tab_style(btn, i == idx)

    def build_editor_page(self, sections_dict):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        tab_container = QWidget()
        tab_container.setFixedWidth(150)
        tab_layout = QVBoxLayout(tab_container)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(5)
        
        stack = QStackedWidget()
        buttons = []
        for i, (name, widget) in enumerate(sections_dict.items()):
            btn = QPushButton(name)
            btn.setFixedSize(140, 36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._apply_tab_style(btn, i == 0)
            btn.clicked.connect(lambda checked, idx=i: self._switch_editor_tab(idx, stack, buttons))
            tab_layout.addWidget(btn)
            stack.addWidget(widget)
            buttons.append(btn)
            
        tab_layout.addStretch()
        layout.addWidget(tab_container)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        QScroller.grabGesture(scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
        scroll.setWidget(stack)
        
        layout.addWidget(scroll, stretch=1)
        return page

    def create_color_grid(self, setting_key):
        w = QWidget()
        l = QGridLayout(w)
        l.setContentsMargins(5, 5, 5, 5)
        l.setSpacing(15)
        row, col = 0, 0
        for c in self.all_colors:
            btn = QPushButton()
            btn.setFixedSize(45, 45)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"background-color: {c}; border-radius: 22px; border: 2px solid rgba(255,255,255,40);")
            btn.clicked.connect(lambda checked, val=c: self.set_setting(setting_key, val))
            l.addWidget(btn, row, col)
            col += 1
            if col > 10: 
                col = 0
                row += 1
        l.setRowStretch(row + 1, 1)
        l.setColumnStretch(11, 1)
        return w

    def create_bg_grid(self, setting_key):
        w = QWidget()
        l = QGridLayout(w)
        l.setContentsMargins(5, 5, 5, 5)
        l.setSpacing(15)
        row, col = 0, 0
        for val, css in self.all_bgs:
            btn = QPushButton()
            btn.setFixedSize(60, 60)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"QPushButton {{ {css} border-radius: 12px; border: 2px solid rgba(255,255,255,40); }}")
            btn.clicked.connect(lambda checked, v=val: self.set_setting(setting_key, v))
            l.addWidget(btn, row, col)
            col += 1
            if col > 8: 
                col = 0
                row += 1
        l.setRowStretch(row + 1, 1)
        l.setColumnStretch(9, 1)
        return w

    def create_photo_grid(self, setting_key):
        w = QWidget()
        l = QGridLayout(w)
        l.setContentsMargins(5, 5, 5, 5)
        l.setSpacing(15)
        
        photos = []
        if os.path.exists("photos"):
            valid = [f for f in os.listdir("photos") if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            valid.sort(key=lambda x: os.path.getmtime(os.path.join("photos", x)), reverse=True)
            photos = valid[:5]
            
        if not photos:
            lbl = QLabel("No photos found.\nUpload images via the Gallery app.")
            lbl.setStyleSheet("color: #888888; font-weight: bold; font-size: 14px;")
            l.addWidget(lbl, 0, 0)
        else:
            col = 0
            for img in photos:
                path = f"photos/{img}"
                btn = ImagePickerButton(path, lambda p, k=setting_key: self.open_adjuster(p, k))
                l.addWidget(btn, 0, col)
                col += 1
                
            btn_all = QPushButton("All\nPhotos")
            btn_all.setFixedSize(80, 80)
            btn_all.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_all.setStyleSheet("background-color: #2C2C35; color: white; border-radius: 12px; font-weight: bold;")
            btn_all.clicked.connect(lambda checked, k=setting_key: self.open_gallery_picker(k))
            l.addWidget(btn_all, 0, col)

        l.setRowStretch(1, 1)
        l.setColumnStretch(6, 1)
        return w

    def create_analog_theme_widget(self):
        w = QWidget()
        l = QHBoxLayout(w)
        l.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        l.setSpacing(20)
        
        btn_dark = QPushButton("Dark Mode")
        btn_dark.setFixedSize(130, 45)
        btn_dark.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dark.setStyleSheet("background: #0C0C0E; color: white; border-radius: 12px; border: 2px solid #444; font-weight: bold;")
        btn_dark.clicked.connect(lambda: self.set_setting("analog_theme", "dark"))
        
        btn_light = QPushButton("Light Mode")
        btn_light.setFixedSize(130, 45)
        btn_light.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_light.setStyleSheet("background: #FFFFFF; color: black; border-radius: 12px; border: 2px solid #444; font-weight: bold;")
        btn_light.clicked.connect(lambda: self.set_setting("analog_theme", "light"))
        
        l.addWidget(btn_dark)
        l.addWidget(btn_light)
        return w

    def set_setting(self, key, value):
        save_setting(key, value)
        self.previews[self.current_idx].load_settings()

    def update_time(self, t, d):
        for p in self.previews:
            p.update_time(t, d)

    # -----------------------------------------------------------------
    # CUSTOM PHOTO OVERLAY MANAGERS
    # -----------------------------------------------------------------
    def open_adjuster(self, path_str, setting_key):
        path = path_str[4:] if path_str.startswith("img:") else path_str
        self.adjuster_overlay.setup(path, setting_key)
        self.adjuster_overlay.show()
        self.adjuster_overlay.raise_()

    def open_gallery_picker(self, setting_key):
        self.gallery_picker.setup(setting_key)
        self.gallery_picker.raise_()

    def apply_adjusted_photo(self, setting_key, val):
        self.set_setting(setting_key, val)
        self.adjuster_overlay.hide()
        self.gallery_picker.hide()

    # -----------------------------------------------------------------
    # CAROUSEL ANIMATIONS
    # -----------------------------------------------------------------
    def slide_to(self, idx):
        self.current_idx = idx
        
        for i, b_frame in enumerate(self.border_frames):
            if i == self.current_idx:
                b_frame.setStyleSheet("border: 4px solid #FFFFFF; border-radius: 36px;")
            else:
                b_frame.setStyleSheet("border: 2px solid #33333F; border-radius: 36px;")
        
        self.grp_slide = QParallelAnimationGroup()
        for i, wrapper in enumerate(self.wrappers):
            offset = i - self.current_idx
            target_x = 162 + (offset * 740) 
            
            anim = QPropertyAnimation(wrapper, b"geometry")
            anim.setDuration(300)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.setEndValue(QRect(target_x, 110, 700, 420))
            self.grp_slide.addAnimation(anim)
            
            anim_l = QPropertyAnimation(self.name_labels[i], b"geometry")
            anim_l.setDuration(300)
            anim_l.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim_l.setEndValue(QRect(target_x, 40, 700, 50))
            self.grp_slide.addAnimation(anim_l)
            
        self.grp_slide.start()

    def prev_face(self):
        if self.current_idx > 0:
            self.slide_to(self.current_idx - 1)
        
    def next_face(self):
        if self.current_idx < len(self.wrappers) - 1:
            self.slide_to(self.current_idx + 1)

    def mousePressEvent(self, event):
        if self.is_editing: return
        self.swipe_start_x = event.position().toPoint().x()
        self.is_swiping = False
        
    def mouseMoveEvent(self, event):
        if self.is_editing: return
        if self.swipe_start_x is not None:
            dx = event.position().toPoint().x() - self.swipe_start_x
            if abs(dx) > 15:
                self.is_swiping = True
                
    def mouseReleaseEvent(self, event):
        if self.is_editing: return
        if self.swipe_start_x is not None:
            dx = event.position().toPoint().x() - self.swipe_start_x
            if dx > 60:
                self.prev_face()
            elif dx < -60:
                self.next_face()
            elif not self.is_swiping:
                rect = self.wrappers[self.current_idx].geometry()
                if rect.contains(event.position().toPoint()):
                    self.apply()
        self.swipe_start_x = None
        self.is_swiping = False

    def open_editor(self):
        self.is_editing = True
        self.lbl_title.hide()
        self.btn_close.hide()
        self.btn_customize.hide()
        for lbl in self.name_labels: lbl.hide()
        
        self.edit_stack.setCurrentIndex(self.current_idx)
        
        active_wrapper = self.wrappers[self.current_idx]
        active_wrapper.raise_()
        self.edit_panel.raise_() 
        
        self.grp_edit = QParallelAnimationGroup()
        
        anim_w = QPropertyAnimation(active_wrapper, b"geometry")
        anim_w.setDuration(300)
        anim_w.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim_w.setStartValue(active_wrapper.geometry())
        anim_w.setEndValue(QRect(212, 10, 600, 360)) 
        self.grp_edit.addAnimation(anim_w)
        
        anim_e = QPropertyAnimation(self.edit_panel, b"geometry")
        anim_e.setDuration(300)
        anim_e.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim_e.setStartValue(QRect(0, 600, 1024, 210))
        anim_e.setEndValue(QRect(0, 390, 1024, 210))
        self.grp_edit.addAnimation(anim_e)
        
        self.grp_edit.start()

    def close_editor(self):
        self.is_editing = False
        active_wrapper = self.wrappers[self.current_idx]
        self.grp_edit = QParallelAnimationGroup()
        
        anim_w = QPropertyAnimation(active_wrapper, b"geometry")
        anim_w.setDuration(300)
        anim_w.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim_w.setStartValue(active_wrapper.geometry())
        anim_w.setEndValue(QRect(162, 110, 700, 420))
        self.grp_edit.addAnimation(anim_w)
        
        anim_e = QPropertyAnimation(self.edit_panel, b"geometry")
        anim_e.setDuration(300)
        anim_e.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim_e.setStartValue(self.edit_panel.geometry())
        anim_e.setEndValue(QRect(0, 600, 1024, 210))
        self.grp_edit.addAnimation(anim_e)
        
        self.grp_edit.finished.connect(self._on_editor_closed)
        self.grp_edit.start()
        
    def _on_editor_closed(self):
        self.lbl_title.show()
        self.btn_close.show()
        self.btn_customize.show()
        for lbl in self.name_labels: lbl.show()

    def apply(self):
        self.lbl_title.hide()
        self.btn_close.hide()
        self.btn_customize.hide()
        
        for lbl in self.name_labels:
            lbl.hide()
        for b_frame in self.border_frames:
            b_frame.hide()
            
        active_wrapper = self.wrappers[self.current_idx]
        active_wrapper.raise_()
        
        self.zoom_anim = QPropertyAnimation(active_wrapper, b"geometry")
        self.zoom_anim.setDuration(350)
        self.zoom_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.zoom_anim.setStartValue(QRect(162, 110, 700, 420))
        self.zoom_anim.setEndValue(QRect(0, 0, 1024, 600))
        
        self.bg_fade_anim = QPropertyAnimation(self.bg_fade, b"alpha")
        self.bg_fade_anim.setDuration(350)
        self.bg_fade_anim.setStartValue(245)
        self.bg_fade_anim.setEndValue(0)
        
        self.grp_hide = QParallelAnimationGroup()
        self.grp_hide.addAnimation(self.zoom_anim)
        self.grp_hide.addAnimation(self.bg_fade_anim)
        self.grp_hide.finished.connect(self._finalize_apply)
        self.grp_hide.start()
        
    def _finalize_apply(self):
        self.hide()
        for wrapper in self.wrappers:
            wrapper.hide()
        self.apply_callback(self.current_idx)
        
    def show_selector(self, current_idx):
        self.saved_idx = current_idx
        self.current_idx = current_idx
        
        self.bg_fade.alpha = 0
        self.bg_fade.show()
        
        for i, wrapper in enumerate(self.wrappers):
            self.name_labels[i].hide() 
            self.border_frames[i].show()
            
            if i == self.current_idx:
                self.border_frames[i].setStyleSheet("border: 4px solid #FFFFFF; border-radius: 36px;")
            else:
                self.border_frames[i].setStyleSheet("border: 2px solid #33333F; border-radius: 36px;")
                
            offset = i - self.current_idx
            if offset == 0:
                wrapper.setGeometry(0, 0, 1024, 600)
                wrapper.show()
                wrapper.raise_()
            else:
                wrapper.setGeometry(162 + (offset * 740), 110, 700, 420)
                wrapper.show()

        self.show()
        self.raise_()
        
        self.zoom_anim = QPropertyAnimation(self.wrappers[self.current_idx], b"geometry")
        self.zoom_anim.setDuration(400)
        self.zoom_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.zoom_anim.setStartValue(QRect(0, 0, 1024, 600))
        self.zoom_anim.setEndValue(QRect(162, 110, 700, 420))
        
        self.bg_fade_anim = QPropertyAnimation(self.bg_fade, b"alpha")
        self.bg_fade_anim.setDuration(400)
        self.bg_fade_anim.setStartValue(0)
        self.bg_fade_anim.setEndValue(245)
        
        self.grp_show = QParallelAnimationGroup()
        self.grp_show.addAnimation(self.zoom_anim)
        self.grp_show.addAnimation(self.bg_fade_anim)
        self.grp_show.finished.connect(self._on_show_finished)
        self.grp_show.start()

    def _on_show_finished(self):
        self.lbl_title.show()
        self.btn_close.show()
        self.btn_customize.show()
        
        for i, lbl in enumerate(self.name_labels):
            offset = i - self.current_idx
            target_x = 162 + (offset * 740)
            lbl.setGeometry(target_x, 40, 700, 50)
            lbl.show()
        
    def close_selector(self):
        self.lbl_title.hide()
        self.btn_close.hide()
        self.btn_customize.hide()
        
        for lbl in self.name_labels:
            lbl.hide()
        for b_frame in self.border_frames:
            b_frame.hide()
        
        if self.current_idx != self.saved_idx:
            self.current_idx = self.saved_idx
            for i, wrapper in enumerate(self.wrappers):
                offset = i - self.current_idx
                wrapper.setGeometry(162 + (offset * 740), 110, 700, 420)
                
        active_wrapper = self.wrappers[self.saved_idx]
        active_wrapper.raise_()
        
        self.zoom_anim = QPropertyAnimation(active_wrapper, b"geometry")
        self.zoom_anim.setDuration(350)
        self.zoom_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.zoom_anim.setStartValue(QRect(162, 110, 700, 420))
        self.zoom_anim.setEndValue(QRect(0, 0, 1024, 600))
        
        self.bg_fade_anim = QPropertyAnimation(self.bg_fade, b"alpha")
        self.bg_fade_anim.setDuration(350)
        self.bg_fade_anim.setStartValue(245)
        self.bg_fade_anim.setEndValue(0)
        
        self.grp_hide = QParallelAnimationGroup()
        self.grp_hide.addAnimation(self.zoom_anim)
        self.grp_hide.addAnimation(self.bg_fade_anim)
        self.grp_hide.finished.connect(self._finalize_close)
        self.grp_hide.start()
        
    def _finalize_close(self):
        self.hide()
        for wrapper in self.wrappers:
            wrapper.hide()