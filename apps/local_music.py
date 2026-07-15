from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget


class LocalMusicPage(QWidget):
    """Native Module: Local MP3/Audio Player Interface."""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 20, 50, 40)

        title = QLabel("Local Music Player")
        title.setFont(QFont("Google Sans", 22, QFont.Weight.Bold))
        title.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(title)

        self.playlist = QListWidget()
        self.playlist.addItems([
            "Track 01 - Synthwave Chill.mp3", 
            "Track 02 - Midnight Drive.mp3", 
            "Track 03 - Ambient Loop.mp3",
            "Track 04 - Cyberpunk City.mp3"
        ])
        self.playlist.setStyleSheet("""
            QListWidget { background-color: #1E1E24; color: #FFFFFF; border: none; font-size: 16px; padding: 10px; border-radius: 10px; }
            QListWidget::item { padding: 12px; border-bottom: 1px solid #2D2D35; }
            QListWidget::item:selected { background-color: #3A3A45; border-radius: 8px; }
        """)
        layout.addWidget(self.playlist)

        controls_layout = QHBoxLayout()
        for text in ["⏮ Prev", "▶ Play", "Next ⏭"]:
            btn = QPushButton(text)
            btn.setFixedHeight(50)
            btn.setStyleSheet("background-color: #3A3A45; color: white; font-size: 16px; border-radius: 10px; font-weight: bold;")
            controls_layout.addWidget(btn)
        layout.addLayout(controls_layout)