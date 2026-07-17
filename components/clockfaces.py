import os
from PyQt6.QtCore import Qt, QTime, QDate, QPoint, QRect, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QFont, QPainter, QPainterPath, QPen, QColor, QBrush, QPolygon
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QPushButton

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

        painter.setPen(QPen(QColor(40, 40, 50), 6))
        painter.drawEllipse(QPoint(0,0), 145, 145)

        painter.setPen(QPen(QColor(255, 255, 255, 150), 3))
        for i in range(12):
            painter.drawLine(0, -125, 0, -135)
            painter.rotate(30.0)

        hour_hand = QPolygon([QPoint(6, 12), QPoint(-6, 12), QPoint(0, -75)])
        painter.setBrush(QBrush(QColor(255, 255, 255)))
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

        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(QPoint(0,0), 6, 6)
        painter.end()


# Mapped list defining the display names for each class
CLOCKFACES = [
    ("Classic Digital", ClassicClock),
    ("Stacked Bold", StackedClock),
    ("Minimal Analog", AnalogClock)
]


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

        self.lbl_name = QLabel("", self.main_container)
        self.lbl_name.setGeometry(0, 50, 1024, 40)
        self.lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_name.setFont(QFont("Google Sans", 24, QFont.Weight.Bold))
        self.lbl_name.setStyleSheet("color: white; background: transparent;")
        self.lbl_name.hide()
        
        self.current_idx = 0
        self.previews = []
        self.wrappers = []
        
        # True Wear OS Side-by-Side Carousel Generation
        for i, (name, Cls) in enumerate(CLOCKFACES):
            inst = Cls()
            wrapper = QFrame(self.main_container)
            wrapper.setStyleSheet("background-color: #1A1A22; border-radius: 36px;")
            
            l = QVBoxLayout(wrapper)
            l.setContentsMargins(0, 0, 0, 0)
            l.addWidget(inst)
            
            self.previews.append(inst)
            self.wrappers.append(wrapper)
            wrapper.hide()

        self.btn_close = QPushButton("✕", self.main_container)
        self.btn_close.setGeometry(30, 30, 50, 50)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet("background: rgba(255,255,255,10); color: white; border-radius: 25px; font-size: 20px; border: none;")
        self.btn_close.clicked.connect(self.close_selector)
        self.btn_close.hide()
        
        self.swipe_start_x = None
        self.is_swiping = False
        self.saved_idx = 0

    def update_time(self, t, d):
        for p in self.previews:
            p.update_time(t, d)
            
    def update_labels(self, idx):
        self.lbl_name.setText(CLOCKFACES[idx][0])

    def slide_to(self, idx):
        self.current_idx = idx
        self.update_labels(idx)
        
        self.grp_slide = QParallelAnimationGroup()
        for i, wrapper in enumerate(self.wrappers):
            offset = i - self.current_idx
            target_x = 162 + (offset * 740) # 740 = 700 width + 40 spacing
            
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
        self.swipe_start_x = event.position().toPoint().x()
        self.is_swiping = False
        
    def mouseMoveEvent(self, event):
        if self.swipe_start_x is not None:
            dx = event.position().toPoint().x() - self.swipe_start_x
            if abs(dx) > 15:
                self.is_swiping = True
                
    def mouseReleaseEvent(self, event):
        if self.swipe_start_x is not None:
            dx = event.position().toPoint().x() - self.swipe_start_x
            if dx > 60:
                self.prev_face()
            elif dx < -60:
                self.next_face()
            elif not self.is_swiping:
                # Tap to apply
                rect = self.wrappers[self.current_idx].geometry()
                if rect.contains(event.position().toPoint()):
                    self.apply()
        self.swipe_start_x = None
        self.is_swiping = False

    def apply(self):
        """Zooms the selected clockface back to full screen and applies it to OS."""
        self.lbl_title.hide()
        self.lbl_name.hide()
        self.btn_close.hide()
        
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
        """Starts full screen and smoothly 'backs up' into the carousel viewer."""
        self.saved_idx = current_idx
        self.current_idx = current_idx
        self.update_labels(current_idx)
        
        self.bg_fade.alpha = 0
        self.bg_fade.show()
        
        for i, wrapper in enumerate(self.wrappers):
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
        self.lbl_name.show()
        self.btn_close.show()
        
    def close_selector(self):
        """Cancels out of edit mode, returning to the originally saved clockface."""
        self.lbl_title.hide()
        self.lbl_name.hide()
        self.btn_close.hide()
        
        # Snap back to the originally active clock before zooming out
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