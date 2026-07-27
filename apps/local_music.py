import os
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget

def get_scale_factor():
    screen = QGuiApplication.primaryScreen()
    return max(1.0, screen.size().width() / 1024.0) if screen else 1.0


class LocalMusicPage(QWidget):
    """Native Module: Local MP3/Audio Player Interface."""
    def __init__(self, on_close=None):
        super().__init__()
        self.setStyleSheet("background-color: #0C0C0E;")
        self.on_close = on_close
        scale = get_scale_factor()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(int(50 * scale), int(20 * scale), int(50 * scale), int(40 * scale))
        layout.setSpacing(int(15 * scale))

        title = QLabel("Local Music Player")
        title.setFont(QFont("Google Sans", int(22 * scale), QFont.Weight.Bold))
        title.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(title)

        self.playlist = QListWidget()
        self.playlist.addItems([
            "Track 01 - Synthwave Chill.mp3", 
            "Track 02 - Midnight Drive.mp3", 
            "Track 03 - Ambient Loop.mp3",
            "Track 04 - Cyberpunk City.mp3"
        ])
        self.playlist.setStyleSheet(f"""
            QListWidget {{ background-color: #1E1E24; color: #FFFFFF; border: none; font-size: {int(16 * scale)}px; padding: {int(10 * scale)}px; border-radius: 10px; }}
            QListWidget::item {{ padding: {int(12 * scale)}px; border-bottom: 1px solid #2D2D35; }}
            QListWidget::item:selected {{ background-color: #3A3A45; border-radius: 8px; }}
        """)
        layout.addWidget(self.playlist)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(int(15 * scale))
        for text in ["⏮ Prev", "▶ Play", "Next ⏭"]:
            btn = QPushButton(text)
            btn.setFixedHeight(int(50 * scale))
            btn.setStyleSheet(f"background-color: #3A3A45; color: white; font-size: {int(16 * scale)}px; border-radius: 10px; font-weight: bold;")
            controls_layout.addWidget(btn)
        layout.addLayout(controls_layout)