import os
import json
from PyQt6.QtCore import Qt, QTime, QDate, QPoint, QRect, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QFont, QPainter, QPainterPath, QPen, QColor, QBrush, QPolygon, QLinearGradient, QPixmap
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QStackedWidget

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
    """Dynamically parses and paints Hex, Gradients, or Images to the clockface."""
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
        path = bg_val[4:]
        if os.path.exists(path):
            pix = QPixmap(path)
            scaled = pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            x = (scaled.width() - w) // 2
            y = (scaled.height() - h) // 2
            painter.drawPixmap(0, 0, scaled, x, y, w, h)
        else:
            painter.fillRect(0, 0, w, h, QColor(12, 12, 14))
    else:
        painter.fillRect(0, 0, w, h, QColor(12, 12, 14))


class FadeOverlay(QWidget):
    """A thread-safe fade overlay specifically for the background dimming."""
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
# CLOCKFACE RENDERING ENGINES
# =================================================================
class ClassicClock(QWidget):
    def __init__(self):
        super().__init__()
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

    def load_settings(self):
        self.hour_color = get_setting("stacked_hour", "#FFFFFF")
        self.min_color = get_setting("stacked_min", "#5A8DEF")
        self.bg = get_setting("stacked_bg", "#0C0C0E")
        
        # Using negative margins forces the text together vertically without shrinking the font size
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
        self.time = QTime.currentTime()
        self.date = QDate.currentDate()
        self.load_settings()

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


# Mapped list defining the display names for each class
CLOCKFACES = [
    ("Classic Digital", ClassicClock),
    ("Stacked Bold", StackedClock),
    ("Minimal Analog", AnalogClock)
]

CLOCKFACE_CLASSES = [cls for name, cls in CLOCKFACES]


# =================================================================
# WEAR OS STYLE CAROUSEL SELECTOR & EDITOR OVERLAY
# =================================================================
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
        self.lbl_title.setGeometry(0, 20, 1024, 30)
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setFont(QFont("Google Sans", 14, QFont.Weight.Bold))
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
            
            lbl_card_name = QLabel(name)
            lbl_card_name.setFont(QFont("Google Sans", 24, QFont.Weight.Bold))
            lbl_card_name.setStyleSheet("color: white; background: transparent; border: none; padding-top: 40px;")
            
            # Un-clickable border overlay that perfectly wraps the clock
            border_frame = QFrame()
            border_frame.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            border_frame.setStyleSheet("border: 2px solid #33333F; border-radius: 36px;")
            border_frame.hide()
            
            l.addWidget(inst, 0, 0)
            l.addWidget(border_frame, 0, 0)
            l.addWidget(lbl_card_name, 0, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
            
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
        
        self.swipe_start_x = None
        self.is_swiping = False
        self.is_editing = False
        self.saved_idx = 0

    def setup_editor_panel(self):
        """Builds the slide-up editor drawer for deep customizing the active clock."""
        self.edit_panel = QFrame(self.main_container)
        self.edit_panel.setGeometry(0, 600, 1024, 180)
        self.edit_panel.setStyleSheet("background-color: rgba(20, 20, 26, 250); border-top-left-radius: 24px; border-top-right-radius: 24px;")
        
        btn_done = QPushButton("Done", self.edit_panel)
        btn_done.setGeometry(1024 - 110, 20, 80, 35)
        btn_done.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_done.setStyleSheet("background-color: #5A8DEF; color: white; border-radius: 17px; font-weight: bold; border: none;")
        btn_done.clicked.connect(self.close_editor)
        
        self.edit_stack = QStackedWidget(self.edit_panel)
        self.edit_stack.setGeometry(30, 20, 1024 - 160, 140)
        self.edit_stack.setStyleSheet("background: transparent;")

        colors = ["#FFFFFF", "#E24A4A", "#5A8DEF", "#1ED760", "#F39C12", "#9B59B6"]
        bgs = [
            ("#0C0C0E", "background-color: #0C0C0E;"),
            ("grad:#5A8DEF:#9B59B6", "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #5A8DEF,stop:1 #9B59B6);"),
            ("grad:#E24A4A:#F39C12", "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #E24A4A,stop:1 #F39C12);")
        ]
        
        if os.path.exists("photos"):
            imgs = [f for f in os.listdir("photos") if f.lower().endswith(('.png', '.jpg', '.jpeg'))][:3]
            for img in imgs:
                path = f"photos/{img}"
                bgs.append((f"img:{path}", f"background-image: url({path}); background-position: center;"))

        # --- 0: Classic Digital Settings ---
        page0 = QWidget()
        l0 = QHBoxLayout(page0)
        l0.setSpacing(40)
        
        col_box = QVBoxLayout()
        col_box.addWidget(QLabel("Clock Color", styleSheet="color: #888; font-weight: bold;"))
        col_btns = QHBoxLayout()
        for c in colors:
            btn = QPushButton()
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"background-color: {c}; border-radius: 18px;")
            btn.clicked.connect(lambda checked, val=c: self.set_setting("classic_color", val))
            col_btns.addWidget(btn)
        col_box.addLayout(col_btns)
        l0.addLayout(col_box)

        bg_box = QVBoxLayout()
        bg_box.addWidget(QLabel("Background", styleSheet="color: #888; font-weight: bold;"))
        bg_btns = QHBoxLayout()
        for val, css in bgs:
            btn = QPushButton()
            btn.setFixedSize(45, 45)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"QPushButton {{ {css} border-radius: 12px; border: 1px solid #444; }}")
            btn.clicked.connect(lambda checked, v=val: self.set_setting("classic_bg", v))
            bg_btns.addWidget(btn)
        bg_box.addLayout(bg_btns)
        l0.addLayout(bg_box)
        l0.addStretch()
        self.edit_stack.addWidget(page0)

        # --- 1: Stacked Bold Settings ---
        page1 = QWidget()
        l1 = QHBoxLayout(page1)
        l1.setSpacing(25)
        
        h_box = QVBoxLayout()
        h_box.addWidget(QLabel("Hour Color", styleSheet="color: #888; font-weight: bold;"))
        h_row = QHBoxLayout()
        for c in colors:
            btn = QPushButton()
            btn.setFixedSize(30, 30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"background-color: {c}; border-radius: 15px;")
            btn.clicked.connect(lambda checked, val=c: self.set_setting("stacked_hour", val))
            h_row.addWidget(btn)
        h_box.addLayout(h_row)
        l1.addLayout(h_box)
        
        m_box = QVBoxLayout()
        m_box.addWidget(QLabel("Minute Color", styleSheet="color: #888; font-weight: bold;"))
        m_row = QHBoxLayout()
        for c in colors:
            btn = QPushButton()
            btn.setFixedSize(30, 30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"background-color: {c}; border-radius: 15px;")
            btn.clicked.connect(lambda checked, val=c: self.set_setting("stacked_min", val))
            m_row.addWidget(btn)
        m_box.addLayout(m_row)
        l1.addLayout(m_box)

        b1_box = QVBoxLayout()
        b1_box.addWidget(QLabel("Background", styleSheet="color: #888; font-weight: bold;"))
        b1_row = QHBoxLayout()
        for val, css in bgs:
            btn = QPushButton()
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"QPushButton {{ {css} border-radius: 10px; border: 1px solid #444; }}")
            btn.clicked.connect(lambda checked, v=val: self.set_setting("stacked_bg", v))
            b1_row.addWidget(btn)
        b1_box.addLayout(b1_row)
        l1.addLayout(b1_box)
        l1.addStretch()
        self.edit_stack.addWidget(page1)

        # --- 2: Analog Theme Settings ---
        page2 = QWidget()
        l2 = QHBoxLayout(page2)
        l2.addWidget(QLabel("Clock Theme", styleSheet="color:#888; font-weight:bold;"))
        
        btn_dark = QPushButton("Dark Mode")
        btn_dark.setFixedSize(120, 40)
        btn_dark.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dark.setStyleSheet("background: #0C0C0E; color: white; border-radius: 12px; border: 1px solid #444;")
        btn_dark.clicked.connect(lambda: self.set_setting("analog_theme", "dark"))
        
        btn_light = QPushButton("Light Mode")
        btn_light.setFixedSize(120, 40)
        btn_light.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_light.setStyleSheet("background: #FFFFFF; color: black; border-radius: 12px; border: 1px solid #444;")
        btn_light.clicked.connect(lambda: self.set_setting("analog_theme", "light"))
        
        l2.addWidget(btn_dark)
        l2.addWidget(btn_light)
        l2.addStretch()
        self.edit_stack.addWidget(page2)

    def set_setting(self, key, value):
        save_setting(key, value)
        self.previews[self.current_idx].load_settings()

    def update_time(self, t, d):
        for p in self.previews:
            p.update_time(t, d)

    def slide_to(self, idx):
        self.current_idx = idx
        
        # Dynamically map the border highlights
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
        for lbl in self.name_labels: lbl.hide()
        self.btn_close.hide()
        self.btn_customize.hide()
        
        self.edit_stack.setCurrentIndex(self.current_idx)
        
        active_wrapper = self.wrappers[self.current_idx]
        self.grp_edit = QParallelAnimationGroup()
        
        anim_w = QPropertyAnimation(active_wrapper, b"geometry")
        anim_w.setDuration(300)
        anim_w.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim_w.setStartValue(active_wrapper.geometry())
        anim_w.setEndValue(QRect(162, 20, 700, 420))
        self.grp_edit.addAnimation(anim_w)
        
        anim_e = QPropertyAnimation(self.edit_panel, b"geometry")
        anim_e.setDuration(300)
        anim_e.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim_e.setStartValue(QRect(0, 600, 1024, 180))
        anim_e.setEndValue(QRect(0, 420, 1024, 180))
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
        anim_e.setEndValue(QRect(0, 600, 1024, 180))
        self.grp_edit.addAnimation(anim_e)
        
        self.grp_edit.finished.connect(self._on_editor_closed)
        self.grp_edit.start()
        
    def _on_editor_closed(self):
        self.lbl_title.show()
        for lbl in self.name_labels: lbl.show()
        self.btn_close.show()
        self.btn_customize.show()

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
            
            # Map the exact border layout directly upon showing
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
        for lbl in self.name_labels:
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