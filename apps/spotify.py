import os
import io
import re
import ssl
import json
import time
import urllib.request
import urllib.parse
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QUrl, QRect, QPropertyAnimation, QEasingCurve, QPoint, QSize
from PyQt6.QtGui import QFont, QFontDatabase, QPixmap, QPainter, QPainterPath, QColor, QIcon, QFontMetrics, QGuiApplication
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QSlider, QFrame, QProgressBar, QScrollArea, QStackedWidget, QScroller, QMenu, QSizePolicy
)

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False

SPOTIFY_CLIENT_ID = "a31b1c1688c947bb98baa2ab3e8c053f"
SPOTIFY_CLIENT_SECRET = "abce0502579346649aaf44549857971d"
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPE = "user-read-playback-state,user-modify-playback-state,user-read-currently-playing,playlist-read-private,user-library-read,user-library-modify"

LYRICS_FETCH_TIMEOUT = 4  
AUDIO_BUFFER_OFFSET_MS = -1200  


def get_scale_factor():
    """Dynamically detects active screen resolution and returns proportional scale factor."""
    screen = QGuiApplication.primaryScreen()
    return max(1.0, screen.size().width() / 1024.0) if screen else 1.0


def truncate_text(text, max_len=40):
    """Safely truncates text for list items."""
    if len(text) > max_len:
        return text[:max_len-3] + "..."
    return text


class ScrollLabel(QWidget):
    """Custom Marquee Label that prevents grid shifting and only scrolls overflowing text."""
    def __init__(self, text="", parent=None, align_center=False):
        super().__init__(parent)
        self.scale = get_scale_factor()
        self._text = text
        self._font = QFont("Google Sans", int(20 * self.scale))
        self._color = QColor(255, 255, 255)
        self._offset = 0.0
        self.align_center = align_center
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.tick)
        self._timer.setInterval(30) 
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(int(35 * self.scale)) 
        self._fm_width = 0

    def setFont(self, font):
        self._font = font
        fm = QFontMetrics(self._font)
        self.setFixedHeight(fm.height() + int(5 * self.scale))
        self.update_metrics()

    def setTextColor(self, color_hex):
        self._color = QColor(color_hex)
        self.update()

    def setText(self, text):
        if self._text != text:
            self._text = text
            self._offset = 0.0
            self.update_metrics()

    def sizeHint(self):
        return QSize(self._fm_width, self.height())

    def minimumSizeHint(self):
        return QSize(10, self.height())

    def update_metrics(self):
        fm = QFontMetrics(self._font)
        # We use a crude way to strip HTML for width calculation, or just use QFontMetrics on raw text if it's simple
        import re
        clean_text = re.sub(r'<[^>]+>', '', self._text)
        self._fm_width = fm.horizontalAdvance(clean_text)
        self.updateGeometry() 
        self.check_scroll()

    def check_scroll(self):
        if self._fm_width > self.width() + 2 and self.width() > 0:
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()
            self._offset = 0.0
        self.update()

    def resizeEvent(self, event):
        self.check_scroll()
        super().resizeEvent(event)

    def tick(self):
        self._offset -= 1.5
        gap = int(50 * self.scale)
        if abs(self._offset) >= self._fm_width + gap:
            self._offset = 0.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        from PyQt6.QtGui import QTextDocument
        doc = QTextDocument()
        doc.setDefaultFont(self._font)
        # Apply color via css
        doc.setDefaultStyleSheet(f"body {{ color: {self._color.name()}; white-space: nowrap; margin: 0px; }}")
        doc.setHtml(f"<body>{self._text}</body>")
        
        # calculate vertical centering
        y = (self.height() - int(doc.size().height())) // 2
        
        if self._timer.isActive():
            p.translate(int(self._offset), y)
            doc.drawContents(p)
            p.translate(-int(self._offset), -y)
            
            gap = int(50 * self.scale)
            p.translate(int(self._offset) + self._fm_width + gap, y)
            doc.drawContents(p)
            p.translate(-(int(self._offset) + self._fm_width + gap), -y)
        else:
            if self.align_center:
                x = max(0, (self.width() - self._fm_width) // 2)
                p.translate(x, y)
                doc.drawContents(p)
                p.translate(-x, -y)
            else:
                p.translate(0, y)
                doc.drawContents(p)
                p.translate(0, -y)
        p.end()


class ClickableProgressBar(QProgressBar):
    on_seek = pyqtSignal(int)
    def __init__(self):
        super().__init__()
        self._is_dragging = False
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.width() > 0:
            self._is_dragging = True
            val = int((event.position().x() / self.width()) * 100)
            self.setValue(max(0, min(100, val)))
        super().mousePressEvent(event)
    def mouseMoveEvent(self, event):
        if self._is_dragging and self.width() > 0:
            val = int((event.position().x() / self.width()) * 100)
            self.setValue(max(0, min(100, val)))
        super().mouseMoveEvent(event)
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_dragging and self.width() > 0:
            self._is_dragging = False
            val = int((event.position().x() / self.width()) * 100)
            self.setValue(max(0, min(100, val)))
            self.on_seek.emit(max(0, min(100, val)))
        super().mouseReleaseEvent(event)


class ClickableTrackRow(QWidget):
    clicked = pyqtSignal(int)
    def __init__(self, index):
        super().__init__()
        self.index = index
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)
        super().mouseReleaseEvent(event)


class ClickableStringRow(QWidget):
    clicked = pyqtSignal(str)
    def __init__(self, payload):
        super().__init__()
        self.payload = payload
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.payload)
        super().mouseReleaseEvent(event)


class ClickableLibraryRow(QWidget):
    clicked = pyqtSignal(dict)
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.data)
        super().mouseReleaseEvent(event)


class SpotifyStateThread(QThread):
    on_state_updated = pyqtSignal(dict)
    on_error = pyqtSignal(str)
    def __init__(self, sp_client):
        super().__init__()
        self.sp = sp_client
        self.is_running = True
    def run(self):
        while self.is_running:
            if not self.sp:
                time.sleep(2)
                continue
            try:
                current = self.sp.current_playback()
                if current:
                    self.on_state_updated.emit(current)
                else:
                    self.on_state_updated.emit({"is_playing": False, "item": None, "device": None})
            except Exception as e:
                self.on_error.emit(str(e))
            time.sleep(1.5)
    def stop(self):
        self.is_running = False
        self.wait()


class DeviceFetchThread(QThread):
    on_devices_ready = pyqtSignal(list)
    def __init__(self, sp_client):
        super().__init__()
        self.sp = sp_client
    def run(self):
        try:
            if not self.sp: return
            res = self.sp.devices()
            self.on_devices_ready.emit(res.get('devices', []))
        except Exception:
            self.on_devices_ready.emit([])


class TransferPlaybackThread(QThread):
    def __init__(self, sp_client, device_id):
        super().__init__()
        self.sp = sp_client
        self.device_id = device_id
    def run(self):
        try:
            if self.sp:
                self.sp.transfer_playback(device_id=self.device_id, force_play=True)
        except Exception:
            pass


class ImageDownloadThread(QThread):
    on_image_ready = pyqtSignal(QPixmap, QPixmap)
    def __init__(self, img_url, size=300):
        super().__init__()
        self.img_url = img_url
        self.size = size
    def run(self):
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(self.img_url, headers={'User-Agent': 'KioskOSPlayer/1.5'})
            with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                img_data = response.read()
                pixmap = QPixmap()
                pixmap.loadFromData(img_data)

                scaled = pixmap.scaled(self.size, self.size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                out_pix = QPixmap(self.size, self.size)
                out_pix.fill(Qt.GlobalColor.transparent)

                painter = QPainter(out_pix)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                clip = QPainterPath()
                clip.addRoundedRect(0, 0, self.size, self.size, 20, 20)
                painter.setClipPath(clip)
                painter.drawPixmap(0, 0, scaled)
                painter.end()

                tiny = pixmap.scaled(8, 8, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                bg_mesh = tiny.scaled(1800, 1800, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                painter_bg = QPainter(bg_mesh)
                painter_bg.fillRect(0, 0, 1800, 1800, QColor(0, 0, 0, 165))
                painter_bg.end()

                self.on_image_ready.emit(out_pix, bg_mesh)
        except Exception:
            pass


class QueueFetchThread(QThread):
    on_queue_ready = pyqtSignal(list)
    def __init__(self, sp_client):
        super().__init__()
        self.sp = sp_client
    def run(self):
        try:
            if not self.sp: return
            data = self.sp.queue()
            if data and "queue" in data:
                self.on_queue_ready.emit(data["queue"])
        except Exception:
            self.on_queue_ready.emit([])


class LibraryFetchThread(QThread):
    on_library_ready = pyqtSignal(list)
    def __init__(self, sp_client):
        super().__init__()
        self.sp = sp_client
    def run(self):
        try:
            if not self.sp: return
            res = self.sp.current_user_playlists(limit=30)
            self.on_library_ready.emit(res.get('items', []))
        except Exception:
            self.on_library_ready.emit([])


class PlaylistTracksFetchThread(QThread):
    on_tracks_ready = pyqtSignal(list)
    def __init__(self, sp_client, uri):
        super().__init__()
        self.sp = sp_client
        self.uri = uri
    def run(self):
        try:
            if not self.sp: return
            tracks = []
            if self.uri == "LIKED_SONGS":
                res = self.sp.current_user_saved_tracks(limit=50)
                tracks.extend([item['track'] for item in res.get('items', []) if item.get('track')])
                res2 = self.sp.current_user_saved_tracks(limit=50, offset=50)
                tracks.extend([item['track'] for item in res2.get('items', []) if item.get('track')])
            else:
                res = self.sp.playlist_tracks(self.uri, limit=100)
                tracks.extend([item['track'] for item in res.get('items', []) if item.get('track')])
                if res.get('next'):
                    res2 = self.sp.next(res)
                    tracks.extend([item['track'] for item in res2.get('items', []) if item.get('track')])
            self.on_tracks_ready.emit(tracks)
        except Exception as e:
            print(f"Playlist fetch error: {e}")
            self.on_tracks_ready.emit([])


class SkipQueueThread(QThread):
    def __init__(self, sp_client, skips):
        super().__init__()
        self.sp = sp_client
        self.skips = skips
    def run(self):
        try:
            for _ in range(self.skips):
                self.sp.next_track()
        except Exception:
            pass


class ImageBatchFetchThread(QThread):
    on_image_ready = pyqtSignal(int, QPixmap)
    def __init__(self, tasks, size=50):
        super().__init__()
        self.tasks = tasks
        self.size = size
    def run(self):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        for task in self.tasks:
            try:
                req = urllib.request.Request(task['url'], headers={'User-Agent': 'KioskOSPlayer'})
                with urllib.request.urlopen(req, timeout=3, context=ctx) as response:
                    img_data = response.read()
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_data)

                    scaled = pixmap.scaled(self.size, self.size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                    out_pix = QPixmap(self.size, self.size)
                    out_pix.fill(Qt.GlobalColor.transparent)

                    painter = QPainter(out_pix)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                    clip = QPainterPath()
                    clip.addRoundedRect(0, 0, self.size, self.size, 6, 6)
                    painter.setClipPath(clip)
                    painter.drawPixmap(0, 0, scaled)
                    painter.end()

                    self.on_image_ready.emit(task['index'], out_pix)
            except Exception:
                pass


class LyricsFetchThread(QThread):
    on_lyrics_ready = pyqtSignal(list)
    def __init__(self, title, artist, duration_ms):
        super().__init__()
        self.raw_title = title
        self.raw_artist = artist
        self.duration_sec = int(duration_ms / 1000) if duration_ms else 0
    def clean_string(self, text):
        text = re.sub(r'\(.*?\)|\[.*?\]', '', text)
        text = re.sub(r'\b(feat|ft)\..*', '', text, flags=re.IGNORECASE)
        return re.sub(r'\s+', ' ', text).strip()
    def run(self):
        try:
            clean_title = self.clean_string(self.raw_title)
            clean_artist = self.clean_string(self.raw_artist)
            headers = {'User-Agent': 'KioskOSPlayer/1.5'}
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            q_title = urllib.parse.quote(clean_title)
            q_artist = urllib.parse.quote(clean_artist)
            plain_backup = None

            url_get = f"https://lrclib.net/api/get?artist_name={q_artist}&track_name={q_title}&duration={self.duration_sec}"
            try:
                req = urllib.request.Request(url_get, headers=headers)
                with urllib.request.urlopen(req, timeout=LYRICS_FETCH_TIMEOUT, context=ctx) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    if data.get("syncedLyrics"):
                        parsed = self.parse_lrc(data.get("syncedLyrics"))
                        if parsed:
                            self.on_lyrics_ready.emit(parsed)
                            return
                    elif data.get("plainLyrics"):
                        plain_backup = data.get("plainLyrics")
            except Exception:
                pass

            url_search = f"https://lrclib.net/api/search?track_name={q_title}&artist_name={q_artist}"
            try:
                req_search = urllib.request.Request(url_search, headers=headers)
                with urllib.request.urlopen(req_search, timeout=LYRICS_FETCH_TIMEOUT, context=ctx) as resp:
                    results = json.loads(resp.read().decode('utf-8'))
                    if results and isinstance(results, list):
                        for hit in results:
                            if hit.get("syncedLyrics"):
                                parsed = self.parse_lrc(hit.get("syncedLyrics"))
                                if parsed:
                                    self.on_lyrics_ready.emit(parsed)
                                    return
                            elif not plain_backup and hit.get("plainLyrics"):
                                plain_backup = hit.get("plainLyrics")
            except Exception:
                pass

            if not plain_backup:
                url_ovh = f"https://api.lyrics.ovh/v1/{q_artist}/{q_title}"
                try:
                    req_ovh = urllib.request.Request(url_ovh, headers=headers)
                    with urllib.request.urlopen(req_ovh, timeout=LYRICS_FETCH_TIMEOUT, context=ctx) as resp:
                        ovh_data = json.loads(resp.read().decode('utf-8'))
                        if ovh_data.get("lyrics"):
                            plain_backup = ovh_data.get("lyrics")
                except Exception:
                    pass

            if plain_backup:
                parsed_plain = self.parse_plain_lyrics(plain_backup)
                if parsed_plain:
                    self.on_lyrics_ready.emit(parsed_plain)
                    return
            self.on_lyrics_ready.emit([(0, "No synchronized lyrics found.", [])])
        except Exception:
            self.on_lyrics_ready.emit([(0, "Lyrics currently unavailable offline.", [])])

    def parse_plain_lyrics(self, text):
        lines = [line.strip() for line in text.strip().split('\n') if line.strip() and "Paroles de la chanson" not in line]
        if not lines: return []
        lyrics_list = []
        total_ms = (self.duration_sec * 1000) if self.duration_sec > 0 else (len(lines) * 3500)
        step_ms = max(1500, int((total_ms * 0.85) / max(len(lines), 1)))
        for i, line in enumerate(lines):
            lyrics_list.append((i * step_ms, line, []))
        return lyrics_list

    def parse_lrc(self, lrc_string):
        lines = lrc_string.strip().split('\n')
        lyrics_list = []
        line_pattern = re.compile(r'\[(\d+):(\d+)\.(\d+)\]\s*(.*)')
        word_pattern = re.compile(r'<(\d+):(\d+)\.(\d+)>\s*([^<]+)')

        for line in lines:
            match = line_pattern.match(line)
            if match:
                mins = int(match.group(1))
                secs = int(match.group(2))
                frac = int(match.group(3))
                raw_text = match.group(4).strip()
                ms = frac * 10 if len(match.group(3)) == 2 else frac
                line_ms = (mins * 60 * 1000) + (secs * 1000) + ms

                words = []
                word_matches = list(word_pattern.finditer(raw_text))
                if word_matches:
                    clean_text = ""
                    for w_match in word_matches:
                        w_mins = int(w_match.group(1))
                        w_secs = int(w_match.group(2))
                        w_frac = int(w_match.group(3))
                        w_word = w_match.group(4).strip()
                        w_ms_val = w_frac * 10 if len(w_match.group(3)) == 2 else w_frac
                        total_w_ms = (w_mins * 60 * 1000) + (w_secs * 1000) + w_ms_val
                        words.append((total_w_ms, w_word))
                        clean_text += w_word + " "
                    clean_text = clean_text.strip()
                else:
                    clean_text = re.sub(r'<[^>]+>', '', raw_text).strip()

                if clean_text:
                    lyrics_list.append((line_ms, clean_text, words))
        return sorted(lyrics_list, key=lambda x: x[0])


class QueuePanel(QScrollArea):
    on_track_clicked = pyqtSignal(int)
    def __init__(self):
        super().__init__()
        self.scale = get_scale_factor()
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.viewport().setStyleSheet("background: transparent;")
        QScroller.grabGesture(self.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(int(15 * self.scale), int(20 * self.scale), int(15 * self.scale), int(180 * self.scale))
        self.layout.setSpacing(0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setWidget(self.container)
        self.image_labels = {}
        self.img_fetcher = None
        self._retiring_threads = []

    def _retire_thread(self, thread):
        if thread is None: return
        try:
            if thread.isRunning():
                thread.blockSignals(True)
                self._retiring_threads.append(thread)
                thread.finished.connect(lambda t=thread: self._cleanup_retired(t))
            else:
                thread.deleteLater()
        except RuntimeError: pass

    def _cleanup_retired(self, thread):
        if thread in self._retiring_threads: self._retiring_threads.remove(thread)
        try: thread.deleteLater()
        except RuntimeError: pass

    def set_queue(self, tracks):
        self._retire_thread(getattr(self, 'img_fetcher', None))

        for i in reversed(range(self.layout.count())):
            item = self.layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()

        self.image_labels.clear()
        image_tasks = []

        if not tracks:
            lbl = QLabel("Queue is empty.")
            lbl.setFont(QFont("Google Sans", int(18 * self.scale)))
            lbl.setStyleSheet("color: #888890; background: transparent;")
            self.layout.addWidget(lbl)
        else:
            limit = min(len(tracks), 25)
            for i, track in enumerate(tracks[:limit]):
                name = track.get("name", "Unknown")
                artists = ", ".join([a["name"] for a in track.get("artists", [])])
                images = track.get("album", {}).get("images", [])
                img_url = images[-1]["url"] if images else None

                row = ClickableTrackRow(i)
                row.setStyleSheet("background: transparent;")
                row.clicked.connect(self.on_track_clicked.emit) 
                
                hlay = QHBoxLayout(row)
                hlay.setContentsMargins(0, int(10 * self.scale), 0, int(10 * self.scale))
                hlay.setSpacing(int(15 * self.scale))

                img_size = int(50 * self.scale)
                img_lbl = QLabel()
                img_lbl.setFixedSize(img_size, img_size)
                img_lbl.setStyleSheet("background-color: rgba(26, 26, 34, 150); border-radius: 6px;")
                self.image_labels[i] = img_lbl
                if img_url: image_tasks.append({'index': i, 'url': img_url})

                vlay = QVBoxLayout()
                vlay.setContentsMargins(0, 0, 0, 0)
                vlay.setSpacing(2)
                vlay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

                t_lbl = QLabel(truncate_text(name, 40))
                t_lbl.setFont(QFont("Google Sans", int(16 * self.scale), QFont.Weight.Bold))
                t_lbl.setStyleSheet("color: #FFFFFF; background: transparent;")
                
                a_lbl = QLabel(truncate_text(artists, 50))
                a_lbl.setFont(QFont("Google Sans", int(13 * self.scale)))
                a_lbl.setStyleSheet("color: #DDDDDD; background: transparent;")

                vlay.addWidget(t_lbl)
                vlay.addWidget(a_lbl)
                hlay.addWidget(img_lbl)
                hlay.addLayout(vlay)
                self.layout.addWidget(row)
                
                if i < limit - 1:
                    line = QFrame()
                    line.setFrameShape(QFrame.Shape.HLine)
                    line.setFixedHeight(1)
                    line.setStyleSheet(f"background-color: rgba(255, 255, 255, 25); border: none; margin-left: {int(65 * self.scale)}px;")
                    self.layout.addWidget(line)
        self.layout.addStretch()
        
        if image_tasks:
            self.img_fetcher = ImageBatchFetchThread(image_tasks, size=int(50 * self.scale))
            self.img_fetcher.on_image_ready.connect(self.update_image)
            self.img_fetcher.start()

    def update_image(self, index, pixmap):
        if index in self.image_labels:
            self.image_labels[index].setPixmap(pixmap)
            self.image_labels[index].setStyleSheet("background-color: transparent;")


class LibraryPanel(QScrollArea):
    on_item_clicked = pyqtSignal(dict)
    def __init__(self):
        super().__init__()
        self.scale = get_scale_factor()
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.viewport().setStyleSheet("background: transparent;")
        QScroller.grabGesture(self.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(int(15 * self.scale), int(20 * self.scale), int(15 * self.scale), int(180 * self.scale))
        self.layout.setSpacing(0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setWidget(self.container)
        
        self.image_labels = {}
        self.img_fetcher = None
        self._retiring_threads = []

    def _retire_thread(self, thread):
        if thread is None: return
        try:
            if thread.isRunning():
                thread.blockSignals(True)
                self._retiring_threads.append(thread)
                thread.finished.connect(lambda t=thread: self._cleanup_retired(t))
            else:
                thread.deleteLater()
        except RuntimeError: pass

    def _cleanup_retired(self, thread):
        if thread in self._retiring_threads: self._retiring_threads.remove(thread)
        try: thread.deleteLater()
        except RuntimeError: pass

    def set_library(self, playlists):
        self._retire_thread(getattr(self, 'img_fetcher', None))

        for i in reversed(range(self.layout.count())):
            item = self.layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()

        self.image_labels.clear()
        image_tasks = []

        liked_data = {"uri": "LIKED_SONGS", "name": "Liked Songs", "image_url": None, "is_liked": True}
        row_liked = ClickableLibraryRow(liked_data)
        row_liked.setStyleSheet("background: transparent;")
        row_liked.clicked.connect(self.on_item_clicked.emit) 
        
        hlay_liked = QHBoxLayout(row_liked)
        hlay_liked.setContentsMargins(0, int(10 * self.scale), 0, int(10 * self.scale))
        hlay_liked.setSpacing(int(15 * self.scale))

        img_size = int(50 * self.scale)
        img_liked = QLabel("♥")
        img_liked.setFont(QFont("Google Sans", int(24 * self.scale)))
        img_liked.setStyleSheet("color: white; background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4E1E8B, stop:1 #8E54E9); border-radius: 6px;")
        img_liked.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_liked.setFixedSize(img_size, img_size)

        vlay_liked = QVBoxLayout()
        vlay_liked.setContentsMargins(0, 0, 0, 0)
        vlay_liked.setSpacing(2)
        vlay_liked.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        t_lbl_liked = QLabel("Liked Songs")
        t_lbl_liked.setFont(QFont("Google Sans", int(16 * self.scale), QFont.Weight.Bold))
        t_lbl_liked.setStyleSheet("color: #FFFFFF; background: transparent;")
        
        a_lbl_liked = QLabel("My Library")
        a_lbl_liked.setFont(QFont("Google Sans", int(13 * self.scale)))
        a_lbl_liked.setStyleSheet("color: #DDDDDD; background: transparent;")

        vlay_liked.addWidget(t_lbl_liked)
        vlay_liked.addWidget(a_lbl_liked)
        hlay_liked.addWidget(img_liked)
        hlay_liked.addLayout(vlay_liked)
        self.layout.addWidget(row_liked)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: rgba(255, 255, 255, 25); border: none; margin-left: {int(65 * self.scale)}px;")
        self.layout.addWidget(line)

        for i, pl in enumerate(playlists):
            idx = i + 1  
            name = pl.get("name", "Unknown Playlist")
            owner = pl.get("owner", {}).get("display_name", "Spotify")
            images = pl.get("images", [])
            img_url = images[-1]["url"] if images else None
            uri = pl.get("uri", "")

            pl_data = {"uri": uri, "name": name, "image_url": img_url, "is_liked": False}
            row = ClickableLibraryRow(pl_data)
            row.setStyleSheet("background: transparent;")
            row.clicked.connect(self.on_item_clicked.emit) 
            
            hlay = QHBoxLayout(row)
            hlay.setContentsMargins(0, int(10 * self.scale), 0, int(10 * self.scale))
            hlay.setSpacing(int(15 * self.scale))

            img_lbl = QLabel()
            img_lbl.setFixedSize(img_size, img_size)
            img_lbl.setStyleSheet("background-color: rgba(26, 26, 34, 150); border-radius: 6px;")
            self.image_labels[idx] = img_lbl
            if img_url: image_tasks.append({'index': idx, 'url': img_url})

            vlay = QVBoxLayout()
            vlay.setContentsMargins(0, 0, 0, 0)
            vlay.setSpacing(2)
            vlay.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            
            t_lbl = QLabel(truncate_text(name, 40))
            t_lbl.setFont(QFont("Google Sans", int(16 * self.scale), QFont.Weight.Bold))
            t_lbl.setStyleSheet("color: #FFFFFF; background: transparent;")
            
            a_lbl = QLabel(truncate_text(owner, 50))
            a_lbl.setFont(QFont("Google Sans", int(13 * self.scale)))
            a_lbl.setStyleSheet("color: #DDDDDD; background: transparent;")

            vlay.addWidget(t_lbl)
            vlay.addWidget(a_lbl)
            hlay.addWidget(img_lbl)
            hlay.addLayout(vlay)
            self.layout.addWidget(row)
            
            if i < len(playlists) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setFixedHeight(1)
                line.setStyleSheet(f"background-color: rgba(255, 255, 255, 25); border: none; margin-left: {int(65 * self.scale)}px;")
                self.layout.addWidget(line)
        self.layout.addStretch()
        
        if image_tasks:
            self.img_fetcher = ImageBatchFetchThread(image_tasks, size=img_size)
            self.img_fetcher.on_image_ready.connect(self.update_image)
            self.img_fetcher.start()

    def update_image(self, index, pixmap):
        if index in self.image_labels:
            self.image_labels[index].setPixmap(pixmap)
            self.image_labels[index].setStyleSheet("background-color: transparent;")


class PlaylistDetailsPanel(QScrollArea):
    on_back = pyqtSignal()
    on_play_all = pyqtSignal(str)
    on_play_track = pyqtSignal(str, int) 

    def __init__(self):
        super().__init__()
        self.scale = get_scale_factor()
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.viewport().setStyleSheet("background: transparent;")
        QScroller.grabGesture(self.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(int(15 * self.scale), int(10 * self.scale), int(15 * self.scale), int(180 * self.scale))
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setWidget(self.container)

        self.btn_back = QPushButton("◀ Library")
        self.btn_back.setFixedSize(int(100 * self.scale), int(30 * self.scale))
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setStyleSheet("background: rgba(255,255,255,20); color: white; border-radius: 15px; font-weight: bold;")
        self.btn_back.clicked.connect(self.on_back.emit)

        header_container = QWidget()
        h_layout = QVBoxLayout(header_container)
        h_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_layout.setSpacing(int(15 * self.scale))

        img_size = int(160 * self.scale)
        self.lbl_image = QLabel()
        self.lbl_image.setFixedSize(img_size, img_size)
        self.lbl_image.setStyleSheet("background-color: rgba(26, 26, 34, 150); border-radius: 12px;")
        self.lbl_image.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_title = ScrollLabel("", align_center=True)
        self.lbl_title.setFont(QFont("Google Sans", int(22 * self.scale), QFont.Weight.Bold))
        self.lbl_title.setTextColor("#FFFFFF")

        self.btn_play_all = QPushButton("Play Playlist")
        self.btn_play_all.setFixedSize(int(170 * self.scale), int(45 * self.scale))
        self.btn_play_all.setFont(QFont("Google Sans", int(14 * self.scale), QFont.Weight.Bold))
        self.btn_play_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play_all.setStyleSheet("background-color: #1ED760; color: #0E0E12; border-radius: 22px;")
        self.btn_play_all.clicked.connect(lambda: self.on_play_all.emit(self.current_uri))

        h_layout.addWidget(self.lbl_image, alignment=Qt.AlignmentFlag.AlignCenter)
        h_layout.addWidget(self.lbl_title, alignment=Qt.AlignmentFlag.AlignCenter)
        h_layout.addWidget(self.btn_play_all, alignment=Qt.AlignmentFlag.AlignCenter)

        self.layout.addWidget(self.btn_back)
        self.layout.addWidget(header_container)
        
        self.tracks_widget = QWidget()
        self.tracks_layout = QVBoxLayout(self.tracks_widget)
        self.tracks_layout.setContentsMargins(0, int(20 * self.scale), 0, 0)
        self.tracks_layout.setSpacing(0)
        self.layout.addWidget(self.tracks_widget)

        self.current_uri = ""
        self.image_labels = {}
        self.img_fetcher = None
        self.header_img_fetcher = None
        self._retiring_threads = []

    def _retire_thread(self, thread):
        if thread is None: return
        try:
            if thread.isRunning():
                thread.blockSignals(True)
                self._retiring_threads.append(thread)
                thread.finished.connect(lambda t=thread: self._cleanup_retired(t))
            else:
                thread.deleteLater()
        except RuntimeError: pass

    def _cleanup_retired(self, thread):
        if thread in self._retiring_threads: self._retiring_threads.remove(thread)
        try: thread.deleteLater()
        except RuntimeError: pass

    def set_header(self, data):
        self.current_uri = data.get('uri', '')
        self.lbl_title.setText(data.get('name', ''))
        self.lbl_image.setText("")
        self.lbl_image.setPixmap(QPixmap()) 
        
        img_url = data.get('image_url')
        is_liked = data.get('is_liked', False)

        if is_liked:
            self.lbl_image.setText("♥")
            self.lbl_image.setFont(QFont("Google Sans", int(70 * self.scale)))
            self.lbl_image.setStyleSheet("color: white; background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4E1E8B, stop:1 #8E54E9); border-radius: 12px;")
        else:
            self.lbl_image.setStyleSheet("background-color: rgba(26, 26, 34, 150); border-radius: 12px;")
            if img_url:
                self._retire_thread(getattr(self, 'header_img_fetcher', None))
                self.header_img_fetcher = ImageBatchFetchThread([{'index': 999, 'url': img_url}], size=int(160 * self.scale))
                self.header_img_fetcher.on_image_ready.connect(self.set_header_image)
                self.header_img_fetcher.start()

        for i in reversed(range(self.tracks_layout.count())):
            item = self.tracks_layout.itemAt(i)
            if item.widget(): item.widget().deleteLater()

    def set_header_image(self, idx, pixmap):
        self.lbl_image.setPixmap(pixmap)

    def set_tracks(self, tracks):
        self._retire_thread(getattr(self, 'img_fetcher', None))

        for i in reversed(range(self.tracks_layout.count())):
            item = self.tracks_layout.itemAt(i)
            if item.widget(): item.widget().deleteLater()

        self.image_labels.clear()
        image_tasks = []

        if not tracks:
            lbl = QLabel("No tracks found.")
            lbl.setFont(QFont("Google Sans", int(16 * self.scale)))
            lbl.setStyleSheet("color: #888890; background: transparent;")
            self.tracks_layout.addWidget(lbl)
        else:
            for i, track in enumerate(tracks):
                name = track.get("name", "Unknown")
                artists = ", ".join([a["name"] for a in track.get("artists", [])])
                images = track.get("album", {}).get("images", [])
                img_url = images[-1]["url"] if images else None

                row = ClickableTrackRow(i)
                row.setStyleSheet("background: transparent;")
                row.clicked.connect(lambda idx=i: self.on_play_track.emit(self.current_uri, idx))
                
                hlay = QHBoxLayout(row)
                hlay.setContentsMargins(0, int(10 * self.scale), 0, int(10 * self.scale))
                hlay.setSpacing(int(15 * self.scale))

                img_lbl = QLabel()
                img_size = int(40 * self.scale)
                img_lbl.setFixedSize(img_size, img_size)
                img_lbl.setStyleSheet("background-color: rgba(26, 26, 34, 150); border-radius: 4px;")
                self.image_labels[i] = img_lbl
                if img_url: image_tasks.append({'index': i, 'url': img_url})

                vlay = QVBoxLayout()
                vlay.setContentsMargins(0, 0, 0, 0)
                vlay.setSpacing(2)
                vlay.setAlignment(Qt.AlignmentFlag.AlignVCenter)
                
                t_lbl = QLabel(truncate_text(name, 40))
                t_lbl.setFont(QFont("Google Sans", int(14 * self.scale), QFont.Weight.Bold))
                t_lbl.setStyleSheet("color: #FFFFFF; background: transparent;")
                
                a_lbl = QLabel(truncate_text(artists, 50))
                a_lbl.setFont(QFont("Google Sans", int(12 * self.scale)))
                a_lbl.setStyleSheet("color: #DDDDDD; background: transparent;")

                vlay.addWidget(t_lbl)
                vlay.addWidget(a_lbl)
                hlay.addWidget(img_lbl)
                hlay.addLayout(vlay)
                self.tracks_layout.addWidget(row)
                
                if i < len(tracks) - 1:
                    line = QFrame()
                    line.setFrameShape(QFrame.Shape.HLine)
                    line.setFixedHeight(1)
                    line.setStyleSheet(f"background-color: rgba(255, 255, 255, 25); border: none; margin-left: {int(55 * self.scale)}px;")
                    self.tracks_layout.addWidget(line)

        if image_tasks:
            self.img_fetcher = ImageBatchFetchThread(image_tasks, size=int(40 * self.scale))
            self.img_fetcher.on_image_ready.connect(self.update_image)
            self.img_fetcher.start()

    def update_image(self, index, pixmap):
        if index in self.image_labels:
            self.image_labels[index].setPixmap(pixmap)
            self.image_labels[index].setStyleSheet("background-color: transparent;")


class LyricsPanel(QScrollArea):
    def __init__(self):
        super().__init__()
        self.scale = get_scale_factor()
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.viewport().setStyleSheet("background: transparent;")
        QScroller.grabGesture(self.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(int(15 * self.scale), int(180 * self.scale), int(15 * self.scale), int(180 * self.scale))
        self.layout.setSpacing(int(24 * self.scale))
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setWidget(self.container)

        self.lyric_data = []
        self.active_index = -1
        self.scroll_anim = QPropertyAnimation(self.verticalScrollBar(), b"value")
        self.scroll_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.scroll_anim.setDuration(450)

    def set_lyrics(self, lyrics_list):
        for i in reversed(range(self.layout.count())):
            item = self.layout.itemAt(i)
            if item.widget(): item.widget().deleteLater()
        self.lyric_data.clear()
        self.active_index = -1
        for time_ms, text, words in lyrics_list:
            lbl = ScrollLabel(text, align_center=True)
            lbl.setFont(QFont("Google Sans", int(20 * self.scale), QFont.Weight.Bold))
            lbl.setTextColor("#646464")
            self.layout.addWidget(lbl)
            self.lyric_data.append([time_ms, lbl, words, -1])
        self.layout.addStretch()

    def update_sync(self, current_time_ms):
        if not self.lyric_data: return
        new_index = -1
        for idx, item in enumerate(self.lyric_data):
            if current_time_ms >= item[0]: new_index = idx
            else: break
        if new_index != self.active_index and new_index != -1:
            self.active_index = new_index
            for idx, item in enumerate(self.lyric_data):
                lbl = item[1]
                if idx == new_index:
                    lbl.setTextColor("#FFFFFF")
                    lbl.setFont(QFont("Google Sans", int(26 * self.scale), QFont.Weight.Bold))
                elif abs(idx - new_index) == 1:
                    lbl.setTextColor("#B4B4B4")
                    lbl.setFont(QFont("Google Sans", int(22 * self.scale), QFont.Weight.Bold))
                else:
                    lbl.setTextColor("#646464")
                    lbl.setFont(QFont("Google Sans", int(20 * self.scale), QFont.Weight.Bold))

            active_widget = self.lyric_data[new_index][1]
            target_y = active_widget.pos().y() - (self.height() // 2) + (active_widget.height() // 2)
            self.scroll_anim.stop()
            self.scroll_anim.setStartValue(self.verticalScrollBar().value())
            self.scroll_anim.setEndValue(max(0, target_y))
            self.scroll_anim.start()

        if self.active_index != -1:
            active_item = self.lyric_data[self.active_index]
            words = active_item[2]
            if words:
                curr_word_idx = -1
                for w_idx, (w_ms, _) in enumerate(words):
                    if current_time_ms >= w_ms: curr_word_idx = w_idx
                    else: break
                if curr_word_idx != active_item[3] and curr_word_idx != -1:
                    active_item[3] = curr_word_idx
                    lbl = active_item[1]
                    spoken = " ".join([w[1] for w in words[:curr_word_idx + 1]])
                    unspoken = " ".join([w[1] for w in words[curr_word_idx + 1:]])
                    lbl.setText(f"<span style='color: #FFFFFF;'>{spoken}</span> <span style='color: rgba(255,255,255,140);'>{unspoken}</span>")


class SpotifyPage(QWidget):
    def __init__(self, on_close=None):
        super().__init__()
        self.scale = get_scale_factor()
        
        font_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")
        if os.path.exists(font_dir):
            for filename in os.listdir(font_dir):
                if filename.endswith(".ttf") or filename.endswith(".otf"):
                    QFontDatabase.addApplicationFont(os.path.join(font_dir, filename))

        app_font = QFont("Google Sans")
        QApplication.setFont(app_font)

        self.on_close = on_close
        self.sp = None
        self.sp_auth = None
        self.is_demo_mode = False
        self.current_track_id = None
        self.track_duration_ms = 0
        self.track_progress_ms = 0
        self.is_playing = False
        self.is_liked = False
        
        self.queue_panel = None
        self.lib_panel = None
        self.playlist_details_panel = None
        self.lyrics_panel = None
        
        self.lyrics_fetcher = None
        self.img_fetcher = None
        self.queue_fetcher = None
        self.lib_fetcher = None
        self.pl_tracks_fetcher = None
        self.skip_fetcher = None
        self.device_fetcher = None
        self.transfer_thread = None
        self._retiring_threads = []

        self.sync_offset_ms = AUDIO_BUFFER_OFFSET_MS  
        self.last_api_time = time.time()
        self.last_api_progress = 0

        self.setObjectName("MainWindow")
        self.setStyleSheet("""
            #MainWindow { background-color: #0A0A0A; } 
            QLabel { color: white; background: transparent; }
            QScrollArea { background: transparent; border: none; }
        """)

        self.bg_label = QLabel(self)
        self.bg_label.setGeometry(-200, -200, 1800, 1800)
        self.bg_label.lower() 
        self.bg_anim = QPropertyAnimation(self.bg_label, b"pos")
        self.bg_anim.setDuration(30000) 
        self.bg_anim.setKeyValues([
            (0.0, QPoint(0, 0)),
            (0.5, QPoint(-250, -250)),
            (1.0, QPoint(0, 0))
        ])
        self.bg_anim.setLoopCount(-1)

        self.init_spotify()

        if not self.is_demo_mode and self.sp_auth and not self.sp_auth.get_cached_token():
            self.init_touch_login_ui()
        else:
            self.init_ui()
            self.start_polling()

        self.ticker = QTimer(self)
        self.ticker.timeout.connect(self.tick_progress)
        self.ticker.start(100) 

    def _clear_layout(self, layout=None):
        """Recursively destroys all widgets and nested sub-layouts to prevent duplicate Home buttons."""
        if layout is None:
            layout = self.layout()
        if not layout:
            return
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def get_icon(self, name, color_hex="#FFFFFF", size=60):
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(color_hex))
        p.setPen(Qt.PenStyle.NoPen)

        if name == "play":
            path = QPainterPath()
            path.moveTo(size * 0.36, size * 0.30)
            path.lineTo(size * 0.36, size * 0.70)
            path.lineTo(size * 0.70, size * 0.50)
            p.drawPath(path)
        elif name == "pause":
            w = size * 0.10
            h = size * 0.40
            p.drawRect(int(size * 0.35), int(size * 0.30), int(w), int(h))
            p.drawRect(int(size * 0.55), int(size * 0.30), int(w), int(h))
        elif name == "next":
            path = QPainterPath()
            path.moveTo(size * 0.28, size * 0.31)
            path.lineTo(size * 0.28, size * 0.69)
            path.lineTo(size * 0.60, size * 0.50)
            p.drawPath(path)
            p.drawRect(int(size * 0.64), int(size * 0.31), int(size * 0.08), int(size * 0.38))
        elif name == "prev":
            p.drawRect(int(size * 0.28), int(size * 0.31), int(size * 0.08), int(size * 0.38))
            path = QPainterPath()
            path.moveTo(size * 0.72, size * 0.31)
            path.lineTo(size * 0.72, size * 0.69)
            path.lineTo(size * 0.40, size * 0.50)
            p.drawPath(path)
        
        p.end()
        return QIcon(pix)

    def _retire_thread(self, thread):
        if thread is None: return
        try:
            if thread.isRunning():
                thread.blockSignals(True)
                self._retiring_threads.append(thread)
                thread.finished.connect(lambda t=thread: self._cleanup_retired(t))
            else:
                thread.deleteLater()
        except RuntimeError: pass

    def _cleanup_retired(self, thread):
        if thread in self._retiring_threads: self._retiring_threads.remove(thread)
        try: thread.deleteLater()
        except RuntimeError: pass

    def init_spotify(self):
        if not SPOTIPY_AVAILABLE or SPOTIFY_CLIENT_ID == "YOUR_CLIENT_ID_HERE":
            self.is_demo_mode = True
            return
        try:
            self.sp_auth = SpotifyOAuth(
                client_id=SPOTIFY_CLIENT_ID,
                client_secret=SPOTIFY_CLIENT_SECRET,
                redirect_uri=SPOTIFY_REDIRECT_URI,
                scope=SCOPE,
                open_browser=False
            )
            token_info = self.sp_auth.get_cached_token()
            if token_info:
                self.sp = spotipy.Spotify(auth_manager=self.sp_auth)
        except Exception as e:
            self.is_demo_mode = True

    def start_polling(self):
        if hasattr(self, 'poller') and self.poller: self.poller.stop()
        self.poller = SpotifyStateThread(self.sp)
        self.poller.on_state_updated.connect(self.update_player_state)
        self.poller.on_error.connect(self.handle_api_error)
        self.poller.start()

    def init_touch_login_ui(self):
        self._clear_layout()
        if not self.layout(): layout = QVBoxLayout(self)
        else: layout = self.layout()
        
        layout.setContentsMargins(int(40 * self.scale), int(20 * self.scale), int(40 * self.scale), int(20 * self.scale))
        layout.setSpacing(int(15 * self.scale))
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_bar = QHBoxLayout()
        btn_exit = QPushButton("✕")
        btn_size = int(50 * self.scale)
        btn_exit.setFixedSize(btn_size, btn_size)
        btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_exit.setStyleSheet(f"""
            QPushButton {{ background-color: rgba(28, 28, 36, 200); color: #AAAAAA; font-size: {int(20 * self.scale)}px; font-weight: bold; border-radius: {btn_size//2}px; border: 1px solid rgba(255,255,255,50); }}
            QPushButton:hover {{ background-color: #E24A4A; color: white; border-color: #E24A4A; }}
        """)
        if self.on_close: btn_exit.clicked.connect(self.exit_app)
        top_bar.addWidget(btn_exit)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        title = QLabel("Connect Your Spotify Account")
        title.setFont(QFont("Google Sans", int(28 * self.scale), QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        if WEBENGINE_AVAILABLE:
            btn_login = QPushButton("Log In on Touchscreen")
            btn_login.setFixedSize(int(360 * self.scale), int(65 * self.scale))
            btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_login.setStyleSheet(f"""
                QPushButton {{ background-color: #1ED760; color: #0E0E12; font-size: {int(19 * self.scale)}px; font-weight: bold; border-radius: {int(32 * self.scale)}px; }}
                QPushButton:hover {{ background-color: #1FDF64; }}
            """)
            btn_login.clicked.connect(self.open_login_browser)
            layout.addWidget(btn_login, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_skip = QPushButton("Skip Login (Use Universal Wi-Fi Mode)")
        btn_skip.setFixedSize(int(360 * self.scale), int(42 * self.scale))
        btn_skip.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_skip.setStyleSheet(f"background-color: rgba(40, 40, 50, 180); color: #CCCCCC; font-size: {int(13 * self.scale)}px; font-weight: bold; border-radius: 8px;")
        btn_skip.clicked.connect(self.skip_to_demo)
        layout.addWidget(btn_skip, alignment=Qt.AlignmentFlag.AlignCenter)

    def open_login_browser(self):
        self.auth_browser = QWebEngineView(self)
        self.auth_browser.setGeometry(int(30 * self.scale), int(20 * self.scale), int(964 * self.scale), int(560 * self.scale))
        self.auth_browser.setStyleSheet("border-radius: 12px; border: 2px solid #1ED760; background-color: white;")
        self.auth_browser.urlChanged.connect(self.handle_auth_redirect)
        self.auth_browser.setUrl(QUrl(self.sp_auth.get_authorize_url()))
        self.auth_browser.show()
        self.auth_browser.raise_()

    def handle_auth_redirect(self, qurl):
        url_str = qurl.toString()
        if url_str.startswith(SPOTIFY_REDIRECT_URI) or "code=" in url_str:
            if hasattr(self, 'auth_browser') and self.auth_browser:
                self.auth_browser.hide()
                self.auth_browser.deleteLater()
                self.auth_browser = None  
            
            query = urllib.parse.urlparse(url_str).query
            params = urllib.parse.parse_qs(query)
            if 'code' in params:
                try:
                    self.sp_auth.get_access_token(params['code'][0])
                    self.sp = spotipy.Spotify(auth_manager=self.sp_auth)
                    self._clear_layout()
                    self.init_ui()
                    self.start_polling()
                except Exception: pass

    def skip_to_demo(self):
        self.is_demo_mode = True
        self._clear_layout()
        self.init_ui()

    def init_ui(self):
        self._clear_layout()
        if not self.layout(): layout = QVBoxLayout(self)
        else: layout = self.layout()
        layout.setContentsMargins(int(30 * self.scale), int(15 * self.scale), int(30 * self.scale), int(20 * self.scale))
        layout.setSpacing(int(15 * self.scale))

        top_bar = QHBoxLayout()
        self.btn_exit = QPushButton("✕")
        btn_size = int(45 * self.scale)
        self.btn_exit.setFixedSize(btn_size, btn_size)
        self.btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exit.setStyleSheet(f"""
            QPushButton {{ background-color: rgba(28, 28, 36, 150); color: #AAAAAA; font-size: {int(20 * self.scale)}px; font-weight: bold; border-radius: {btn_size//2}px; border: 1px solid rgba(255,255,255,30); }}
            QPushButton:hover {{ background-color: #E24A4A; color: white; border-color: #E24A4A; }}
        """)
        if self.on_close: self.btn_exit.clicked.connect(self.exit_app)
        top_bar.addWidget(self.btn_exit)

        self.btn_logout = QPushButton("Log Out")
        self.btn_logout.setFixedSize(int(90 * self.scale), int(38 * self.scale))
        self.btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_logout.setStyleSheet(f"background-color: rgba(40, 40, 50, 150); color: #DDDDDD; font-size: {int(12 * self.scale)}px; font-weight: bold; border-radius: 8px;")
        self.btn_logout.clicked.connect(self.logout_user)
        top_bar.addWidget(self.btn_logout)

        top_bar.addStretch()

        self.btn_device = QPushButton("🎧 Connect")
        self.btn_device.setFont(QFont("Google Sans", int(13 * self.scale), QFont.Weight.Bold))
        self.btn_device.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_device.setStyleSheet("color: #1ED760; background: transparent; border: none; text-align: left;")
        self.btn_device.clicked.connect(self.show_device_menu)
        top_bar.addWidget(self.btn_device)

        lbl_vol_icon = QLabel("−")
        lbl_vol_icon.setFont(QFont("Google Sans", int(22 * self.scale), QFont.Weight.Bold))
        top_bar.addWidget(lbl_vol_icon)

        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setFixedSize(int(120 * self.scale), int(20 * self.scale))
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(80)
        self.vol_slider.setStyleSheet("""
            QSlider { background: transparent; }
            QSlider::groove:horizontal { height: 4px; background: rgba(255, 255, 255, 50); border-radius: 2px; }
            QSlider::sub-page:horizontal { background: #FFFFFF; border-radius: 2px; }
            QSlider::handle:horizontal { width: 12px; margin: -4px 0; background: white; border-radius: 6px; }
        """)
        self.vol_slider.sliderReleased.connect(self.change_volume)
        top_bar.addWidget(self.vol_slider)

        lbl_vol_max = QLabel("+")
        lbl_vol_max.setFont(QFont("Google Sans", int(20 * self.scale), QFont.Weight.Bold))
        top_bar.addWidget(lbl_vol_max)
        layout.addLayout(top_bar)

        main_body = QHBoxLayout()
        main_body.setSpacing(int(40 * self.scale))

        left_col = QVBoxLayout()
        left_col.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        left_col.setSpacing(int(14 * self.scale))

        art_size = int(240 * self.scale)
        self.lbl_art = QLabel()
        self.lbl_art.setFixedSize(art_size, art_size)
        self.lbl_art.setStyleSheet("background-color: rgba(26, 26, 34, 150); border-radius: 20px; border: 1px solid rgba(255,255,255,20);")
        self.lbl_art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_art.setText("")
        self.lbl_art.setFont(QFont("Google Sans", int(18 * self.scale)))
        left_col.addWidget(self.lbl_art)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(5, 0, 5, 0)
        meta_box = QVBoxLayout()
        meta_box.setSpacing(2)
        
        self.lbl_title = ScrollLabel("")
        self.lbl_title.setFont(QFont("Google Sans", int(20 * self.scale), QFont.Weight.Bold))
        self.lbl_title.setTextColor("#FFFFFF")
        meta_box.addWidget(self.lbl_title)

        self.lbl_artist = ScrollLabel("Spotify Player")
        self.lbl_artist.setFont(QFont("Google Sans", int(15 * self.scale)))
        self.lbl_artist.setTextColor("#DDDDDD")
        meta_box.addWidget(self.lbl_artist)
        
        title_row.addLayout(meta_box)
        title_row.addStretch()

        self.btn_star = QPushButton("♡")
        star_size = int(36 * self.scale)
        self.btn_star.setFixedSize(star_size, star_size)
        self.btn_star.setFont(QFont("Google Sans", int(24 * self.scale)))
        self.btn_star.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_star.setStyleSheet("background: transparent; color: #DDDDDD; border: none;")
        self.btn_star.clicked.connect(self.toggle_like)
        title_row.addWidget(self.btn_star)

        left_col.addLayout(title_row)

        scrub_layout = QVBoxLayout()
        scrub_layout.setSpacing(6)
        self.progress_bar = ClickableProgressBar()
        self.progress_bar.setFixedHeight(int(6 * self.scale))
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: rgba(255, 255, 255, 50); border: none; border-radius: 3px; }
            QProgressBar::chunk { background-color: #1ED760; border-radius: 3px; }
        """)
        self.progress_bar.on_seek.connect(self.handle_seek)
        scrub_layout.addWidget(self.progress_bar)

        time_row = QHBoxLayout()
        self.lbl_curr_time = QLabel("0:00")
        self.lbl_curr_time.setFont(QFont("Google Sans", int(11 * self.scale)))
        self.lbl_curr_time.setStyleSheet("color: rgba(255,255,255,150);")
        time_row.addWidget(self.lbl_curr_time)
        time_row.addStretch()

        lbl_badge = QLabel(" Lossless ")
        lbl_badge.setFont(QFont("Google Sans", int(9 * self.scale), QFont.Weight.Bold))
        lbl_badge.setStyleSheet("color: rgba(255,255,255,180); background-color: rgba(255,255,255,20); border: 1px solid rgba(255,255,255,40); border-radius: 4px; padding: 2px 4px;")
        time_row.addWidget(lbl_badge)
        time_row.addStretch()

        self.lbl_total_time = QLabel("-0:00")
        self.lbl_total_time.setFont(QFont("Google Sans", int(11 * self.scale)))
        self.lbl_total_time.setStyleSheet("color: rgba(255,255,255,150);")
        time_row.addWidget(self.lbl_total_time)

        scrub_layout.addLayout(time_row)
        left_col.addLayout(scrub_layout)

        controls_row = QHBoxLayout()
        controls_row.setSpacing(int(20 * self.scale))
        controls_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_shuffle = QPushButton("Shuffle")
        self.btn_shuffle.setFont(QFont("Google Sans", int(12 * self.scale), QFont.Weight.Bold))
        self.btn_shuffle.setFixedHeight(int(35 * self.scale))
        self.btn_shuffle.setStyleSheet("color: #DDDDDD; background: transparent; border: none;")
        self.btn_shuffle.clicked.connect(lambda: self.send_command("shuffle"))
        controls_row.addWidget(self.btn_shuffle)

        self.btn_prev = QPushButton()
        btn_prev_size = int(45 * self.scale)
        self.btn_prev.setFixedSize(btn_prev_size, btn_prev_size)
        self.btn_prev.setIcon(self.get_icon("prev", "#FFFFFF", btn_prev_size))
        self.btn_prev.setIconSize(self.btn_prev.size())
        self.btn_prev.setStyleSheet("background: transparent; border: none;")
        self.btn_prev.clicked.connect(lambda: self.send_command("prev"))
        controls_row.addWidget(self.btn_prev)

        self.btn_play = QPushButton()
        btn_play_size = int(64 * self.scale)
        self.btn_play.setFixedSize(btn_play_size, btn_play_size)
        self.btn_play.setIcon(self.get_icon("play", "#0E0E12", btn_play_size))
        self.btn_play.setIconSize(self.btn_play.size())
        self.btn_play.setStyleSheet(f"""
            QPushButton {{ background-color: #FFFFFF; border-radius: {btn_play_size//2}px; border: none; }}
            QPushButton:hover {{ background-color: #E0E0E0; }}
        """)
        self.btn_play.clicked.connect(lambda: self.send_command("toggle"))
        controls_row.addWidget(self.btn_play)

        self.btn_next = QPushButton()
        self.btn_next.setFixedSize(btn_prev_size, btn_prev_size)
        self.btn_next.setIcon(self.get_icon("next", "#FFFFFF", btn_prev_size))
        self.btn_next.setIconSize(self.btn_next.size())
        self.btn_next.setStyleSheet("background: transparent; border: none;")
        self.btn_next.clicked.connect(lambda: self.send_command("next"))
        controls_row.addWidget(self.btn_next)

        self.btn_repeat = QPushButton("Repeat")
        self.btn_repeat.setFont(QFont("Google Sans", int(12 * self.scale), QFont.Weight.Bold))
        self.btn_repeat.setFixedHeight(int(35 * self.scale))
        self.btn_repeat.setStyleSheet("color: #DDDDDD; background: transparent; border: none;")
        self.btn_repeat.clicked.connect(lambda: self.send_command("repeat"))
        controls_row.addWidget(self.btn_repeat)

        for btn in [self.btn_shuffle, self.btn_prev, self.btn_play, self.btn_next, self.btn_repeat]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        left_col.addLayout(controls_row)
        main_body.addLayout(left_col, stretch=4)

        right_col = QVBoxLayout()
        right_col.setSpacing(int(10 * self.scale))
        lyrics_header = QHBoxLayout()
        self.lbl_lyr_title = QLabel("Live Lyrics")
        self.lbl_lyr_title.setFont(QFont("Google Sans", int(16 * self.scale), QFont.Weight.Bold))
        self.lbl_lyr_title.setStyleSheet("color: rgba(255,255,255,200);")
        lyrics_header.addWidget(self.lbl_lyr_title)

        lyrics_header.addSpacing(int(15 * self.scale))
        self.btn_sync_minus = QPushButton("-")
        btn_sync_size = int(28 * self.scale)
        self.btn_sync_minus.setFixedSize(btn_sync_size, btn_sync_size)
        self.btn_sync_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sync_minus.setStyleSheet("background: rgba(40,40,50,150); color: #DDDDDD; border-radius: 4px; font-weight: bold;")
        self.btn_sync_minus.clicked.connect(lambda: self.adjust_sync(-200))

        self.lbl_sync = QLabel(f"{self.sync_offset_ms}ms")
        self.lbl_sync.setFont(QFont("Google Sans", int(11 * self.scale)))
        self.lbl_sync.setStyleSheet("color: rgba(255,255,255,150);")
        self.lbl_sync.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_sync.setFixedWidth(int(55 * self.scale))

        self.btn_sync_plus = QPushButton("+")
        self.btn_sync_plus.setFixedSize(btn_sync_size, btn_sync_size)
        self.btn_sync_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sync_plus.setStyleSheet("background: rgba(40,40,50,150); color: #DDDDDD; border-radius: 4px; font-weight: bold;")
        self.btn_sync_plus.clicked.connect(lambda: self.adjust_sync(200))

        lyrics_header.addWidget(self.btn_sync_minus)
        lyrics_header.addWidget(self.lbl_sync)
        lyrics_header.addWidget(self.btn_sync_plus)
        lyrics_header.addStretch()

        btn_tab_w = int(70 * self.scale)
        btn_tab_h = int(30 * self.scale)
        self.btn_view_lyr = QPushButton("Lyrics")
        self.btn_view_lyr.setFixedSize(btn_tab_w, btn_tab_h)
        self.btn_view_lyr.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.btn_view_queue = QPushButton("Queue")
        self.btn_view_queue.setFixedSize(btn_tab_w, btn_tab_h)
        self.btn_view_queue.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.btn_view_lib = QPushButton("Library")
        self.btn_view_lib.setFixedSize(btn_tab_w, btn_tab_h)
        self.btn_view_lib.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.tab_active_style = "background: rgba(255,255,255,40); color: white; border-radius: 15px; font-weight: bold;"
        self.tab_inactive_style = "background: transparent; color: rgba(255,255,255,150); border-radius: 15px; font-weight: bold;"
        
        self.btn_view_lyr.setStyleSheet(self.tab_active_style)
        self.btn_view_queue.setStyleSheet(self.tab_inactive_style)
        self.btn_view_lib.setStyleSheet(self.tab_inactive_style)
        
        self.btn_view_lyr.clicked.connect(lambda: self.switch_right_view(0))
        self.btn_view_queue.clicked.connect(lambda: self.switch_right_view(1))
        self.btn_view_lib.clicked.connect(lambda: self.switch_right_view(2))

        lyrics_header.addWidget(self.btn_view_lyr)
        lyrics_header.addWidget(self.btn_view_queue)
        lyrics_header.addWidget(self.btn_view_lib)
        right_col.addLayout(lyrics_header)

        self.right_stack = QStackedWidget()
        self.right_stack.setStyleSheet("background: transparent;")
        
        self.lyrics_panel = LyricsPanel()
        
        self.queue_panel = QueuePanel()
        self.queue_panel.on_track_clicked.connect(self.play_specific_track)
        
        self.lib_panel = LibraryPanel()
        self.lib_panel.on_item_clicked.connect(self.open_playlist_details)

        self.playlist_details_panel = PlaylistDetailsPanel()
        self.playlist_details_panel.on_back.connect(lambda: self.switch_right_view(2))
        self.playlist_details_panel.on_play_all.connect(self.play_playlist_all)
        self.playlist_details_panel.on_play_track.connect(self.play_playlist_track)
        
        self.right_stack.addWidget(self.lyrics_panel)   
        self.right_stack.addWidget(self.queue_panel)    
        self.right_stack.addWidget(self.lib_panel)      
        self.right_stack.addWidget(self.playlist_details_panel) 

        right_col.addWidget(self.right_stack)
        main_body.addLayout(right_col, stretch=5)
        layout.addLayout(main_body)

        if self.is_demo_mode:
            self.load_demo_state()

    def update_artwork(self, crisp_pix, bg_pix):
        self.lbl_art.setPixmap(crisp_pix)
        self.bg_label.setPixmap(bg_pix)
        if self.bg_anim.state() != QPropertyAnimation.State.Running:
            self.bg_anim.start()

    def show_device_menu(self):
        if self.is_demo_mode or not self.sp: return
        self.btn_device.setText("🎧 Searching...")
        self._retire_thread(getattr(self, 'device_fetcher', None))
        fetcher = DeviceFetchThread(self.sp)
        fetcher.on_devices_ready.connect(self.display_device_menu)
        fetcher.finished.connect(fetcher.deleteLater)
        fetcher.start()
        self.device_fetcher = fetcher

    def display_device_menu(self, devices):
        if not devices:
            self.btn_device.setText("🎧 No Devices Found")
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: rgba(28, 28, 36, 240); color: white; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 30); padding: 5px; }
            QMenu::item { padding: 12px 24px; font-family: 'Google Sans'; font-size: 14px; border-radius: 4px; margin: 4px; }
            QMenu::item:selected { background-color: #1ED760; color: #0E0E12; font-weight: bold; }
        """)
        
        for dev in devices:
            name = dev.get('name', 'Unknown Device')
            dev_id = dev.get('id')
            is_active = dev.get('is_active', False)
            icon = "🔊" if dev.get('type') == 'Speaker' else ("💻" if dev.get('type') == 'Computer' else "📱")
            display_text = f"{icon} {name}" + (" (Active)" if is_active else "")
            
            action = menu.addAction(display_text)
            action.setData(dev_id)
        
        pos = self.btn_device.mapToGlobal(QPoint(0, self.btn_device.height()))
        selected_action = menu.exec(pos)
        
        if selected_action:
            target_id = selected_action.data()
            self._retire_thread(getattr(self, 'transfer_thread', None))
            transfer = TransferPlaybackThread(self.sp, target_id)
            transfer.finished.connect(transfer.deleteLater)
            transfer.start()
            self.transfer_thread = transfer

    def play_specific_track(self, queue_index):
        if self.is_demo_mode or not self.sp: return
        skips_required = queue_index + 1
        self._retire_thread(getattr(self, 'skip_fetcher', None))
        fetcher = SkipQueueThread(self.sp, skips_required)
        fetcher.finished.connect(fetcher.deleteLater)
        fetcher.finished.connect(lambda: QTimer.singleShot(800, self.fetch_queue))
        fetcher.start()
        self.skip_fetcher = fetcher

    def open_playlist_details(self, data):
        self.right_stack.setCurrentIndex(3)
        self.playlist_details_panel.set_header(data)
        
        self.btn_view_lyr.setStyleSheet(self.tab_inactive_style)
        self.btn_view_queue.setStyleSheet(self.tab_inactive_style)
        self.btn_view_lib.setStyleSheet(self.tab_active_style) 
        self.lbl_lyr_title.setText("Playlist")
        self.btn_sync_minus.hide()
        self.lbl_sync.hide()
        self.btn_sync_plus.hide()

        self._retire_thread(getattr(self, 'pl_tracks_fetcher', None))
        fetcher = PlaylistTracksFetchThread(self.sp, data['uri'])
        fetcher.on_tracks_ready.connect(self.playlist_details_panel.set_tracks)
        fetcher.finished.connect(fetcher.deleteLater)
        fetcher.start()
        self.pl_tracks_fetcher = fetcher

    def play_playlist_all(self, uri):
        if self.is_demo_mode or not self.sp: return
        try:
            if uri == "LIKED_SONGS":
                user_id = self.sp.me()['id']
                uri = f"spotify:user:{user_id}:collection"
                
            self.sp.start_playback(context_uri=uri)
            QTimer.singleShot(600, self.fetch_queue)
        except Exception as e:
            print(f"Play All Error: {e}")

    def play_playlist_track(self, playlist_uri, track_index):
        if self.is_demo_mode or not self.sp: return
        try:
            if playlist_uri == "LIKED_SONGS":
                user_id = self.sp.me()['id']
                playlist_uri = f"spotify:user:{user_id}:collection"
                
            self.sp.start_playback(context_uri=playlist_uri)
            
            if track_index > 0:
                self._retire_thread(getattr(self, 'skip_fetcher', None))
                fetcher = SkipQueueThread(self.sp, track_index)
                fetcher.finished.connect(fetcher.deleteLater)
                fetcher.finished.connect(lambda: QTimer.singleShot(800, self.fetch_queue))
                fetcher.start()
                self.skip_fetcher = fetcher
            else:
                QTimer.singleShot(600, self.fetch_queue)
                
        except Exception as e:
            print(f"Play Track Error: {e}")

    def adjust_sync(self, delta):
        self.sync_offset_ms += delta
        self.lbl_sync.setText(f"{self.sync_offset_ms}ms")

    def switch_right_view(self, index):
        self.right_stack.setCurrentIndex(index)
        self.btn_view_lyr.setStyleSheet(self.tab_inactive_style)
        self.btn_view_queue.setStyleSheet(self.tab_inactive_style)
        self.btn_view_lib.setStyleSheet(self.tab_inactive_style)
        
        if index == 0:
            self.lbl_lyr_title.setText("Live Lyrics")
            self.btn_view_lyr.setStyleSheet(self.tab_active_style)
            self.btn_sync_minus.show()
            self.lbl_sync.show()
            self.btn_sync_plus.show()
        elif index == 1:
            self.lbl_lyr_title.setText("Up Next")
            self.btn_view_queue.setStyleSheet(self.tab_active_style)
            self.btn_sync_minus.hide()
            self.lbl_sync.hide()
            self.btn_sync_plus.hide()
            self.fetch_queue()
        else:
            self.lbl_lyr_title.setText("My Library")
            self.btn_view_lib.setStyleSheet(self.tab_active_style)
            self.btn_sync_minus.hide()
            self.lbl_sync.hide()
            self.btn_sync_plus.hide()
            self.fetch_library()

    def fetch_queue(self):
        if self.is_demo_mode: return
        self._retire_thread(getattr(self, 'queue_fetcher', None))
        fetcher = QueueFetchThread(self.sp)
        fetcher.on_queue_ready.connect(self.queue_panel.set_queue)
        fetcher.finished.connect(fetcher.deleteLater)
        fetcher.start()
        self.queue_fetcher = fetcher

    def fetch_library(self):
        if self.is_demo_mode: return
        self._retire_thread(getattr(self, 'lib_fetcher', None))
        fetcher = LibraryFetchThread(self.sp)
        fetcher.on_library_ready.connect(self.lib_panel.set_library)
        fetcher.finished.connect(fetcher.deleteLater)
        fetcher.start()
        self.lib_fetcher = fetcher

    def logout_user(self):
        if os.path.exists(".cache"):
            try: os.remove(".cache")
            except Exception: pass
        if hasattr(self, 'poller') and self.poller: self.poller.stop()

        self._retire_thread(getattr(self, 'lyrics_fetcher', None))
        self._retire_thread(getattr(self, 'img_fetcher', None))
        self._retire_thread(getattr(self, 'queue_fetcher', None))
        self._retire_thread(getattr(self, 'lib_fetcher', None))
        self._retire_thread(getattr(self, 'pl_tracks_fetcher', None))
        self._retire_thread(getattr(self, 'skip_fetcher', None))
        self._retire_thread(getattr(self, 'device_fetcher', None))
        self._retire_thread(getattr(self, 'transfer_thread', None))
        
        queue_panel = getattr(self, 'queue_panel', None)
        if queue_panel:
            self._retire_thread(getattr(queue_panel, 'img_fetcher', None))
            
        lib_panel = getattr(self, 'lib_panel', None)
        if lib_panel:
            self._retire_thread(getattr(lib_panel, 'img_fetcher', None))
            
        pl_panel = getattr(self, 'playlist_details_panel', None)
        if pl_panel:
            self._retire_thread(getattr(pl_panel, 'header_img_fetcher', None))
            self._retire_thread(getattr(pl_panel, 'img_fetcher', None))

        self._clear_layout()
        self.is_demo_mode = False
        self.init_spotify()
        self.init_touch_login_ui()

    def update_player_state(self, data):
        if self.is_demo_mode or not data: return
        is_playing = data.get("is_playing", False)
        item = data.get("item", {})
        device = data.get("device", {})

        if device:
            dev_name = device.get("name", "Speaker")
            vol = device.get("volume_percent", 80)
            self.btn_device.setText(f"🎧 {dev_name}")
            self.vol_slider.blockSignals(True)
            self.vol_slider.setValue(vol)
            self.vol_slider.blockSignals(False)
        else:
            self.btn_device.setText("🎧 Select Device")

        self.is_playing = is_playing
        
        btn_play_size = int(64 * self.scale)
        if is_playing: self.btn_play.setIcon(self.get_icon("pause", "#0E0E12", btn_play_size))
        else: self.btn_play.setIcon(self.get_icon("play", "#0E0E12", btn_play_size))

        is_shuff = data.get("shuffle_state", False)
        self.btn_shuffle.setStyleSheet("color: #1ED760; background: transparent; border: none;" if is_shuff else "color: #DDDDDD; background: transparent; border: none;")

        rep = data.get("repeat_state", "off")
        if rep == "context":
            self.btn_repeat.setText("Repeat")
            self.btn_repeat.setStyleSheet("color: #1ED760; background: transparent; border: none;")
        elif rep == "track":
            self.btn_repeat.setText("Repeat 1")
            self.btn_repeat.setStyleSheet("color: #1ED760; background: transparent; border: none;")
        else:
            self.btn_repeat.setText("Repeat")
            self.btn_repeat.setStyleSheet("color: #DDDDDD; background: transparent; border: none;")

        if not item: return

        track_id = item.get("id")
        if track_id != self.current_track_id:
            self.current_track_id = track_id
            self.lbl_title.setText(item.get("name", "Unknown Title"))
            artists = ", ".join([a["name"] for a in item.get("artists", [])])
            self.lbl_artist.setText(artists)

            try:
                liked_list = self.sp.current_user_saved_tracks_contains([track_id])
                self.is_liked = liked_list[0] if liked_list else False
                self.btn_star.setText("♥" if self.is_liked else "♡")
                self.btn_star.setStyleSheet("color: #1ED760; background: transparent; border: none;" if self.is_liked else "color: #DDDDDD; background: transparent; border: none;")
            except Exception: pass

            images = item.get("album", {}).get("images", [])
            if images:
                self._retire_thread(getattr(self, 'img_fetcher', None))
                fetcher = ImageDownloadThread(images[0]["url"], size=int(300 * self.scale))
                fetcher.on_image_ready.connect(self.update_artwork)
                fetcher.finished.connect(fetcher.deleteLater)
                fetcher.start()
                self.img_fetcher = fetcher

            track_duration = item.get("duration_ms", 0)
            self.load_song_lyrics(item.get("name", ""), artists, track_duration)
            if self.right_stack.currentIndex() == 1: self.fetch_queue()

        self.track_duration_ms = item.get("duration_ms", 1)
        self.last_api_progress = data.get("progress_ms", 0)
        self.last_api_time = time.time()
        self.refresh_progress_display()

    def tick_progress(self):
        if self.is_playing and self.track_duration_ms > 0:
            elapsed_since_api = (time.time() - self.last_api_time) * 1000
            calculated_ms = int(self.last_api_progress + elapsed_since_api) + self.sync_offset_ms
            self.track_progress_ms = max(0, min(calculated_ms, self.track_duration_ms))
            self.refresh_progress_display()

    def refresh_progress_display(self):
        if self.track_duration_ms <= 0: return
        pct = int((self.track_progress_ms / self.track_duration_ms) * 100)
        if not getattr(self.progress_bar, '_is_dragging', False):
            self.progress_bar.setValue(pct)

        curr_sec = (self.track_progress_ms // 1000) % 60
        curr_min = (self.track_progress_ms // 1000) // 60
        rem_ms = self.track_duration_ms - self.track_progress_ms
        rem_sec = (rem_ms // 1000) % 60
        rem_min = (rem_ms // 1000) // 60

        self.lbl_curr_time.setText(f"{curr_min}:{curr_sec:02d}")
        self.lbl_total_time.setText(f"-{rem_min}:{rem_sec:02d}")
        self.lyrics_panel.update_sync(self.track_progress_ms)

    def handle_seek(self, pct):
        if self.is_demo_mode: return
        if not self.sp or self.track_duration_ms <= 0: return
        seek_ms = int((pct / 100.0) * self.track_duration_ms)
        try:
            self.sp.seek_track(seek_ms)
            self.track_progress_ms = seek_ms
            self.last_api_progress = seek_ms - self.sync_offset_ms
            self.last_api_time = time.time()
            self.refresh_progress_display()
        except Exception as e: print(f"Seek error: {e}")

    def send_command(self, cmd):
        if self.is_demo_mode: return
        try:
            if cmd == "toggle":
                if self.is_playing: self.sp.pause_playback()
                else: self.sp.start_playback()
            elif cmd == "next": self.sp.next_track()
            elif cmd == "prev": self.sp.previous_track()
            elif cmd == "shuffle":
                curr = self.sp.current_playback()
                if curr:
                    self.sp.shuffle(not curr.get("shuffle_state", False))
                    QTimer.singleShot(600, self.fetch_queue)
            elif cmd == "repeat":
                curr = self.sp.current_playback()
                if curr:
                    rep = curr.get("repeat_state", "off")
                    next_rep = {"off": "context", "context": "track", "track": "off"}.get(rep, "off")
                    self.sp.repeat(next_rep)
        except Exception as e: print(f"Command '{cmd}' error: {e}")

    def change_volume(self):
        vol = self.vol_slider.value()
        if not self.is_demo_mode and self.sp:
            try: self.sp.volume(vol)
            except Exception as e: print(f"Volume error: {e}")

    def toggle_like(self):
        self.is_liked = not self.is_liked
        self.btn_star.setText("♥" if self.is_liked else "♡")
        self.btn_star.setStyleSheet("color: #1ED760; background: transparent; border: none;" if self.is_liked else "color: #DDDDDD; background: transparent; border: none;")
        if not self.is_demo_mode and self.sp and self.current_track_id:
            try:
                if self.is_liked: self.sp.current_user_saved_tracks_add([self.current_track_id])
                else: self.sp.current_user_saved_tracks_delete([self.current_track_id])
            except Exception as e: print(f"Like error: {e}")

    def handle_api_error(self, err_msg):
        self.btn_device.setText("Waiting for Wi-Fi Speaker...")

    def exit_app(self):
        self.ticker.stop()
        if hasattr(self, 'poller') and self.poller: self.poller.stop()
        self._retire_thread(getattr(self, 'lyrics_fetcher', None))
        self._retire_thread(getattr(self, 'img_fetcher', None))
        self._retire_thread(getattr(self, 'queue_fetcher', None))
        self._retire_thread(getattr(self, 'lib_fetcher', None))
        self._retire_thread(getattr(self, 'pl_tracks_fetcher', None))
        self._retire_thread(getattr(self, 'skip_fetcher', None))
        self._retire_thread(getattr(self, 'device_fetcher', None))
        self._retire_thread(getattr(self, 'transfer_thread', None))
        
        queue_panel = getattr(self, 'queue_panel', None)
        if queue_panel:
            self._retire_thread(getattr(queue_panel, 'img_fetcher', None))
            
        lib_panel = getattr(self, 'lib_panel', None)
        if lib_panel:
            self._retire_thread(getattr(lib_panel, 'img_fetcher', None))
            
        pl_panel = getattr(self, 'playlist_details_panel', None)
        if pl_panel:
            self._retire_thread(getattr(pl_panel, 'header_img_fetcher', None))
            self._retire_thread(getattr(pl_panel, 'img_fetcher', None))

        for t in list(self._retiring_threads):
            try: t.wait(200)
            except RuntimeError: pass
            
        try:
            if getattr(self, 'auth_browser', None):
                self.auth_browser.close()
                self.auth_browser = None
        except RuntimeError:
            pass

        if self.on_close: self.on_close()

    def load_song_lyrics(self, title, artist, duration_ms=0):
        self._retire_thread(getattr(self, 'lyrics_fetcher', None))
        self.lyrics_panel.set_lyrics([(0, f"🔍 Searching lyrics for {title}...", [])])
        fetcher = LyricsFetchThread(title, artist, duration_ms)
        fetcher.on_lyrics_ready.connect(self.lyrics_panel.set_lyrics)
        fetcher.finished.connect(fetcher.deleteLater)
        fetcher.start()
        self.lyrics_fetcher = fetcher

    def load_demo_state(self):
        self.btn_device.setText("🎧 AirPlay / Connect Ready")
        self.lbl_title.setText("")
        self.lbl_artist.setText("Spotify Player")
        self.is_playing = False
        btn_play_size = int(64 * self.scale)
        self.btn_play.setIcon(self.get_icon("play", "#0E0E12", btn_play_size))
        self.track_duration_ms = 0
        self.track_progress_ms = 0

        self.is_liked = False
        self.btn_star.setText("♡")
        self.btn_star.setStyleSheet("color: #DDDDDD; background: transparent; border: none;")

        self.refresh_progress_display()
        self.lyrics_panel.set_lyrics([(0, "", [])])

        art_size = int(300 * self.scale)
        pix = QPixmap(art_size, art_size)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            clip = QPainterPath()
            clip.addRoundedRect(0, 0, art_size, art_size, 20, 20)
            painter.setClipPath(clip)
            painter.fillRect(0, 0, art_size, art_size, QColor(26, 26, 34, 150))
        finally:
            painter.end()

        bg_pix = QPixmap(1800, 1800)
        bg_pix.fill(QColor(0, 0, 0))

        self.update_artwork(pix, bg_pix)