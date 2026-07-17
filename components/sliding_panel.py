from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtWidgets import QFrame

class SlidingPanel(QFrame):
    """A smooth, hardware-accelerated sliding panel for the App Drawer and Control Center."""
    def __init__(self, parent, hidden_rect, visible_rect):
        super().__init__(parent)
        self.hidden_rect = hidden_rect
        self.visible_rect = visible_rect
        self.setGeometry(self.hidden_rect)
        self.is_visible = False

        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(350)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def slide_in(self):
        """Slides the panel onto the screen."""
        self.show()
        self.raise_()
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(self.visible_rect)
        self.anim.start()
        self.is_visible = True

    def slide_out(self):
        """Slides the panel off the screen."""
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(self.hidden_rect)
        self.anim.start()
        self.is_visible = False