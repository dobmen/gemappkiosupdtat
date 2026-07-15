import os
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QLabel, QProgressBar, QFrame
)

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False


class BrowserPage(QWidget):
    """Touchscreen Web Browser downloaded from GitHub App Store."""
    def __init__(self, on_close=None):
        super().__init__()
        self.on_close = on_close
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # -------------------------------------------------------------
        # 1. TOP NAVIGATION BAR (60px height)
        # -------------------------------------------------------------
        nav_bar = QFrame()
        nav_bar.setFixedHeight(60)
        nav_bar.setStyleSheet("background-color: #16161A; border-bottom: 1px solid #282830;")
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(15, 8, 15, 8)
        nav_layout.setSpacing(10)

        # Return to Kiosk Home Button
        self.btn_exit = QPushButton("🏠 Home")
        self.btn_exit.setFixedSize(90, 42)
        self.btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exit.setStyleSheet("""
            QPushButton { background-color: #E24A4A; color: white; font-size: 15px; font-weight: bold; border-radius: 8px; }
            QPushButton:hover { background-color: #C0392B; }
        """)
        if self.on_close:
            self.btn_exit.clicked.connect(self.on_close)
        nav_layout.addWidget(self.btn_exit)

        # Back, Forward & Reload Buttons
        self.btn_back = QPushButton("◀")
        self.btn_back.setFixedSize(45, 42)
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.btn_forward = QPushButton("▶")
        self.btn_forward.setFixedSize(45, 42)
        self.btn_forward.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_reload = QPushButton("🔄")
        self.btn_reload.setFixedSize(45, 42)
        self.btn_reload.setCursor(Qt.CursorShape.PointingHandCursor)

        nav_btn_style = """
            QPushButton { background-color: #282830; color: white; font-size: 18px; font-weight: bold; border-radius: 8px; }
            QPushButton:hover { background-color: #383845; }
            QPushButton:disabled { color: #555555; background-color: #1E1E24; }
        """
        for btn in [self.btn_back, self.btn_forward, self.btn_reload]:
            btn.setStyleSheet(nav_btn_style)
            nav_layout.addWidget(btn)

        # Address / Search Bar
        self.url_bar = QLineEdit()
        self.url_bar.setFixedHeight(42)
        self.url_bar.setPlaceholderText("Search Google or enter a website URL...")
        self.url_bar.setFont(QFont("Google Sans", 14))
        self.url_bar.setStyleSheet("""
            QLineEdit {
                background-color: #22222A;
                color: white;
                border: 2px solid #2E2E38;
                border-radius: 8px;
                padding-left: 15px;
                padding-right: 15px;
            }
            QLineEdit:focus {
                border-color: #5A8DEF;
                background-color: #1C1C22;
            }
        """)
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        nav_layout.addWidget(self.url_bar)

        # Go / Search Button
        self.btn_go = QPushButton("🔍 Go")
        self.btn_go.setFixedSize(80, 42)
        self.btn_go.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_go.setStyleSheet("""
            QPushButton { background-color: #5A8DEF; color: white; font-size: 15px; font-weight: bold; border-radius: 8px; }
            QPushButton:hover { background-color: #4A7DDF; }
        """)
        self.btn_go.clicked.connect(self.navigate_to_url)
        nav_layout.addWidget(self.btn_go)

        layout.addWidget(nav_bar)

        # -------------------------------------------------------------
        # 2. QUICK BOOKMARKS BAR (45px height)
        # -------------------------------------------------------------
        bm_bar = QFrame()
        bm_bar.setFixedHeight(45)
        bm_bar.setStyleSheet("background-color: #121215; border-bottom: 1px solid #22222A;")
        bm_layout = QHBoxLayout(bm_bar)
        bm_layout.setContentsMargins(15, 6, 15, 6)
        bm_layout.setSpacing(10)

        lbl_bm = QLabel("⭐ Quick Links:")
        lbl_bm.setFont(QFont("Google Sans", 13, QFont.Weight.Bold))
        lbl_bm.setStyleSheet("color: #AAAAAA; border: none;")
        bm_layout.addWidget(lbl_bm)

        bookmarks = [
            ("Google", "https://www.google.com"),
            ("YouTube", "https://www.youtube.com"),
            ("Wikipedia", "https://www.wikipedia.org"),
            ("GitHub", "https://www.github.com"),
            ("Reddit", "https://www.reddit.com"),
            ("DuckDuckGo", "https://duckduckgo.com")
        ]

        for title, url in bookmarks:
            btn_bm = QPushButton(title)
            btn_bm.setFixedHeight(30)
            btn_bm.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_bm.setStyleSheet("""
                QPushButton { background-color: #22222A; color: #CCCCCC; font-size: 13px; font-weight: bold; border-radius: 6px; padding: 0 12px; }
                QPushButton:hover { background-color: #383845; color: white; }
            """)
            btn_bm.clicked.connect(lambda checked, u=url: self.load_url_string(u))
            bm_layout.addWidget(btn_bm)

        bm_layout.addStretch()
        layout.addWidget(bm_bar)

        # -------------------------------------------------------------
        # 3. LOADING PROGRESS BAR
        # -------------------------------------------------------------
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { background: #121215; border: none; } QProgressBar::chunk { background: #5A8DEF; }")
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # -------------------------------------------------------------
        # 4. WEB ENGINE VIEW OR FALLBACK
        # -------------------------------------------------------------
        if WEBENGINE_AVAILABLE:
            self.web = QWebEngineView()
            self.web.setUrl(QUrl("https://www.google.com"))
            
            # Connect navigation signals
            self.btn_back.clicked.connect(self.web.back)
            self.btn_forward.clicked.connect(self.web.forward)
            self.btn_reload.clicked.connect(self.web.reload)
            
            self.web.urlChanged.connect(self.update_url_bar)
            self.web.loadStarted.connect(lambda: self.progress_bar.show())
            self.web.loadProgress.connect(self.progress_bar.setValue)
            self.web.loadFinished.connect(self.on_load_finished)
            
            layout.addWidget(self.web)
        else:
            fallback = QWidget()
            fb_layout = QVBoxLayout(fallback)
            fb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            title = QLabel("Web Engine Missing")
            title.setFont(QFont("Google Sans", 32, QFont.Weight.Bold))
            title.setStyleSheet("color: white;")
            
            desc = QLabel("Please install 'PyQt6-WebEngine' in your virtual environment to render websites.")
            desc.setStyleSheet("color: #E24A4A; font-size: 18px; margin-top: 10px;")
            
            fb_layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
            fb_layout.addWidget(desc, alignment=Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(fallback)

    def load_url_string(self, url_str):
        """Loads a URL string directly into the browser and updates the address bar."""
        self.url_bar.setText(url_str)
        if WEBENGINE_AVAILABLE:
            self.web.setUrl(QUrl(url_str))

    def navigate_to_url(self):
        """Checks if text is a URL or search query, then navigates."""
        text = self.url_bar.text().strip()
        if not text:
            return
            
        # If it looks like a web domain (e.g. 'bbc.com'), add https:// automatically
        if "." in text and not " " in text:
            if not text.startswith("http://") and not text.startswith("https://"):
                text = "https://" + text
        else:
            # Treat plain words as a Google search query
            query = text.replace(" ", "+")
            text = f"https://www.google.com/search?q={query}"
            
        self.load_url_string(text)

    def update_url_bar(self, qurl):
        """Updates the URL input bar text whenever the webpage navigates via clicked links."""
        self.url_bar.setText(qurl.toString())

    def on_load_finished(self):
        """Hides progress bar and updates Back/Forward button enabled states."""
        self.progress_bar.hide()
        if WEBENGINE_AVAILABLE:
            self.btn_back.setEnabled(self.web.history().canGoBack())
            self.btn_forward.setEnabled(self.web.history().canGoForward())


def create_web_app_view(url, title, on_close):
    """Creates a locked-down web view for specific web apps (like Character.ai)."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    # Top Navigation Bar
    nav_bar = QFrame()
    nav_bar.setFixedHeight(60)
    nav_bar.setStyleSheet("background-color: #16161A; border-bottom: 1px solid #282830;")
    nav_layout = QHBoxLayout(nav_bar)
    nav_layout.setContentsMargins(15, 8, 15, 8)
    
    btn_exit = QPushButton("🏠 Home")
    btn_exit.setFixedSize(90, 42)
    btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_exit.setStyleSheet("""
        QPushButton { background-color: #E24A4A; color: white; font-size: 15px; font-weight: bold; border-radius: 8px; }
        QPushButton:hover { background-color: #C0392B; }
    """)
    btn_exit.clicked.connect(on_close)
    
    lbl_title = QLabel(title)
    lbl_title.setFont(QFont("Google Sans", 18, QFont.Weight.Bold))
    lbl_title.setStyleSheet("color: white;")
    
    nav_layout.addWidget(btn_exit)
    nav_layout.addStretch()
    nav_layout.addWidget(lbl_title)
    nav_layout.addStretch()
    # Add a spacer on the right so the title stays perfectly centered
    nav_layout.addSpacing(90) 
    
    layout.addWidget(nav_bar)
    
    if WEBENGINE_AVAILABLE:
        web = QWebEngineView()
        web.setUrl(QUrl(url))
        layout.addWidget(web)
    else:
        fallback = QLabel("WebEngine not available.\nInstall PyQt6-WebEngine via pip.")
        fallback.setFont(QFont("Google Sans", 18))
        fallback.setStyleSheet("color: #E24A4A;")
        fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(fallback)
        
    return widget