import os
from PyQt6.QtCore import Qt, QTime, QDate, QPoint, QRect, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QFont, QPainter, QPen, QColor, QBrush, QPolygon
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QStackedWidget, QPushButton

class FadeOverlay(QWidget):
    """A completely thread-safe fade overlay to replace buggy QGraphicsOpacityEffect."""
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
        self.lbl_date.setStyleSheet("color: #888888;")
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_time)
        layout.addWidget(self.lbl_date)

    def update_time(self, t, d):
        self.lbl_time.setText(t.toString("HH:mm"))
        self.lbl_date.setText(d.toString("dddd, MMMM d"))


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
        self.lbl_minute.setStyleSheet("color: #5A8DEF;")
        self.lbl_minute.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_date = QLabel()
        self.lbl_date.setFont(QFont("Google Sans", 20))
        self.lbl_date.setStyleSheet("color: #AAAAAA; margin-top: 15px;")
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_hour)
        layout.addWidget(self.lbl_minute)
        layout.addWidget(self.lbl_date)

    def update_time(self, t, d):
        self.lbl_hour.setText(t.toString("HH"))
        self.lbl_minute.setText(t.toString("mm"))
        self.lbl_date.setText(d.toString("dddd, MMM d"))


class AnalogClock(QWidget):
    def __init__(self):
        super().__init__()
        self.time = QTime.currentTime()
        self.date = QDate.currentDate()

    def update_time(self, t, d):
        self.time = t
        self.date = d
        self.update()

    def paintEvent(self, event):
        side = min(self.width(), self.height())
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width() / 2.0, self.height() / 2.0)
        painter.scale(side / 320.0, side / 320.0)

        # Draw outer ring
        painter.setPen(QPen(QColor(40, 40, 50), 6))
        painter.drawEllipse(QPoint(0,0), 145, 145)

        # Ticks
        painter.setPen(QPen(QColor(255, 255, 255, 150), 3))
        for i in range(12):
            painter.drawLine(0, -125, 0, -135)
            painter.rotate(30.0)

        # Hour hand
        hour_hand = QPolygon([QPoint(6, 12), QPoint(-6, 12), QPoint(0, -75)])
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.save()
        painter.rotate(30.0 * ((self.time.hour() + self.time.minute() / 60.0)))
        painter.drawPolygon(hour_hand)
        painter.restore()

        # Minute hand
        min_hand = QPolygon([QPoint(4, 12), QPoint(-4, 12), QPoint(0, -115)])
        painter.setBrush(QBrush(QColor(90, 141, 239)))
        painter.save()
        painter.rotate(6.0 * (self.time.minute() + self.time.second() / 60.0))
        painter.drawPolygon(min_hand)
        painter.restore()

        # Second hand
        sec_hand = QPolygon([QPoint(2, 12), QPoint(-2, 12), QPoint(0, -125)])
        painter.setBrush(QBrush(QColor(226, 74, 74)))
        painter.save()
        painter.rotate(6.0 * self.time.second())
        painter.drawPolygon(sec_hand)
        painter.restore()

        # Center dot
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(QPoint(0,0), 6, 6)
        painter.end()


CLOCKFACE_CLASSES = [ClassicClock, StackedClock, AnalogClock]


class ClockSelectorOverlay(QWidget):
    def __init__(self, parent, apply_callback):
        super().__init__(parent)
        self.apply_callback = apply_callback
        self.setGeometry(0, 0, 1024, 600)
        self.hide()
        
        # Container to hold everything so we can animate it sliding up
        self.main_container = QFrame(self)
        self.main_container.setGeometry(0, 0, 1024, 600)
        
        self.bg = QFrame(self.main_container)
        self.bg.setGeometry(0, 0, 1024, 600)
        self.bg.setStyleSheet("background-color: rgba(12, 12, 14, 250);")
        
        self.lbl_title = QLabel("Select Watch Face", self.main_container)
        self.lbl_title.setGeometry(0, 40, 1024, 50)
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setFont(QFont("Google Sans", 24, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet("color: white; background: transparent;")
        
        self.preview_stack = QStackedWidget(self.main_container)
        self.preview_stack.setGeometry(312, 110, 400, 360)
        self.preview_stack.setStyleSheet("background: transparent;")
        
        self.previews = []
        for Cls in CLOCKFACE_CLASSES:
            inst = Cls()
            wrapper = QFrame()
            wrapper.setStyleSheet("background-color: #0C0C0E; border-radius: 180px; border: 4px solid #33333F;")
            wrapper.setFixedSize(360, 360)
            
            l = QVBoxLayout(wrapper)
            l.setContentsMargins(0, 0, 0, 0)
            l.addWidget(inst)
            
            container = QWidget()
            cl = QVBoxLayout(container)
            cl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(wrapper)
            
            self.previews.append(inst)
            self.preview_stack.addWidget(container)

        # Purely hardware-safe fade overlay placed strictly over the preview stack
        self.fade_overlay = FadeOverlay(self.main_container)
        self.fade_overlay.setGeometry(312, 110, 400, 360)
            
        self.btn_prev = QPushButton("◀", self.main_container)
        self.btn_prev.setGeometry(200, 260, 60, 60)
        self.btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev.setStyleSheet("background: rgba(255,255,255,20); color: white; border-radius: 30px; font-size: 24px; border: none;")
        self.btn_prev.clicked.connect(self.prev_face)
        
        self.btn_next = QPushButton("▶", self.main_container)
        self.btn_next.setGeometry(764, 260, 60, 60)
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.setStyleSheet("background: rgba(255,255,255,20); color: white; border-radius: 30px; font-size: 24px; border: none;")
        self.btn_next.clicked.connect(self.next_face)
        
        self.btn_apply = QPushButton("Apply", self.main_container)
        self.btn_apply.setGeometry(412, 500, 200, 50)
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply.setStyleSheet("background-color: #5A8DEF; color: white; border-radius: 25px; font-size: 18px; font-weight: bold; border: none;")
        self.btn_apply.clicked.connect(self.apply)
        
        self.btn_close = QPushButton("✕", self.main_container)
        self.btn_close.setGeometry(50, 40, 50, 50)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet("background: rgba(255,255,255,20); color: white; border-radius: 25px; font-size: 20px; border: none;")
        self.btn_close.clicked.connect(self.close_selector)
        
        self.swipe_start_x = None

    def update_time(self, t, d):
        for p in self.previews:
            p.update_time(t, d)
            
    def prev_face(self):
        idx = self.preview_stack.currentIndex() - 1
        if idx < 0: idx = self.preview_stack.count() - 1
        self.slide_to(idx, "right")
        
    def next_face(self):
        idx = self.preview_stack.currentIndex() + 1
        if idx >= self.preview_stack.count(): idx = 0
        self.slide_to(idx, "left")
        
    def slide_to(self, idx, direction):
        self.target_idx = idx
        base_pos = QPoint(312, 110)
        offset = -50 if direction == "left" else 50
        
        self.anim_out = QPropertyAnimation(self.preview_stack, b"pos")
        self.anim_out.setDuration(150)
        self.anim_out.setStartValue(base_pos)
        self.anim_out.setEndValue(base_pos + QPoint(offset, 0))
        
        self.fade_overlay.show()
        self.fade_overlay.raise_()
        self.fade_out = QPropertyAnimation(self.fade_overlay, b"alpha")
        self.fade_out.setDuration(150)
        self.fade_out.setStartValue(0)
        self.fade_out.setEndValue(255)
        
        self.grp_out = QParallelAnimationGroup()
        self.grp_out.addAnimation(self.anim_out)
        self.grp_out.addAnimation(self.fade_out)
        self.grp_out.finished.connect(lambda: self.mid_slide(idx, direction, base_pos))
        self.grp_out.start()
        
    def mid_slide(self, idx, direction, base_pos):
        self.preview_stack.setCurrentIndex(idx)
        offset = 50 if direction == "left" else -50
        
        self.anim_in = QPropertyAnimation(self.preview_stack, b"pos")
        self.anim_in.setDuration(150)
        self.anim_in.setStartValue(base_pos + QPoint(offset, 0))
        self.anim_in.setEndValue(base_pos)
        
        self.fade_in = QPropertyAnimation(self.fade_overlay, b"alpha")
        self.fade_in.setDuration(150)
        self.fade_in.setStartValue(255)
        self.fade_in.setEndValue(0)
        self.fade_in.finished.connect(self.fade_overlay.hide)
        
        self.grp_in = QParallelAnimationGroup()
        self.grp_in.addAnimation(self.anim_in)
        self.grp_in.addAnimation(self.fade_in)
        self.grp_in.start()

    def mousePressEvent(self, event):
        self.swipe_start_x = event.position().toPoint().x()
        
    def mouseReleaseEvent(self, event):
        if self.swipe_start_x is not None:
            dx = event.position().toPoint().x() - self.swipe_start_x
            if dx > 60:
                self.prev_face()
            elif dx < -60:
                self.next_face()
        self.swipe_start_x = None

    def apply(self):
        self.apply_callback(self.preview_stack.currentIndex())
        self.close_selector()
        
    def show_selector(self, current_idx):
        self.preview_stack.setCurrentIndex(current_idx)
        self.show()
        self.raise_()
        
        # Smooth slide-up animation replacing buggy opacity fade
        self.slide_anim = QPropertyAnimation(self.main_container, b"pos")
        self.slide_anim.setDuration(350)
        self.slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.slide_anim.setStartValue(QPoint(0, 600))
        self.slide_anim.setEndValue(QPoint(0, 0))
        self.slide_anim.start()
        
    def close_selector(self):
        # Smooth slide-down animation out of the way
        self.slide_anim = QPropertyAnimation(self.main_container, b"pos")
        self.slide_anim.setDuration(300)
        self.slide_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.slide_anim.setStartValue(QPoint(0, 0))
        self.slide_anim.setEndValue(QPoint(0, 600))
        self.slide_anim.finished.connect(self.hide)
        self.slide_anim.start()