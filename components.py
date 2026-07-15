from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget
from utils import load_app_icon


class AppIconWidget(QWidget):
    """Google Nest style app icon: A circular icon button with text underneath."""
    def __init__(self, app_name, icon_path, click_callback):
        super().__init__()
        self.setFixedSize(140, 150)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_icon = QPushButton()
        self.btn_icon.setFixedSize(80, 80)
        self.btn_icon.setIcon(load_app_icon(icon_path, size=80))
        self.btn_icon.setIconSize(QSize(80, 80))
        self.btn_icon.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_icon.setStyleSheet("""
            QPushButton {
                background-color: #22222A;
                border: 2px solid #2E2E38;
                border-radius: 40px;
            }
            QPushButton:hover {
                background-color: #2E2E38;
                border-color: #5A8DEF;
            }
            QPushButton:pressed {
                background-color: #383845;
            }
        """)
        self.btn_icon.clicked.connect(lambda: click_callback(app_name))

        self.lbl_name = QLabel(app_name)
        self.lbl_name.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        self.lbl_name.setStyleSheet("color: #E0E0E0; border: none;")
        self.lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_name.setWordWrap(True)

        layout.addWidget(self.btn_icon, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_name, alignment=Qt.AlignmentFlag.AlignCenter)


class SlidingPanel(QFrame):
    """A widget that tracks the finger and snaps smoothly with OutCubic easing."""
    def __init__(self, parent, start_rect, end_rect):
        super().__init__(parent)
        self.start_rect = start_rect
        self.end_rect = end_rect
        self.setGeometry(start_rect)
        self.is_visible = False

        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def snap_to(self, target_rect, visible_state):
        self.raise_()
        self.anim.stop()
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(target_rect)
        self.anim.start()
        self.is_visible = visible_state

    def slide_in(self):
        self.snap_to(self.end_rect, True)

    def slide_out(self):
        self.snap_to(self.start_rect, False)