import os
import sys
from contextlib import contextmanager
from PyQt6.QtCore import QThread, pyqtSignal
import speech_recognition as sr

# =================================================================
# DEEP C-LEVEL ERROR SUPPRESSOR (Hides JACK/ALSA Spam)
# =================================================================
@contextmanager
def silence_audio_warnings():
    """Temporarily redirects all C-level stderr to /dev/null during initialization."""
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    sys.stderr.flush()
    os.dup2(devnull, 2)
    try:
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(devnull)
        os.close(old_stderr)


# =================================================================
# VOICE ASSISTANT THREAD
# =================================================================
class VoiceAssistantThread(QThread):
    # Signals to communicate cleanly with the core Kiosk window
    command_recognized = pyqtSignal(str, str)  
    status_changed = pyqtSignal(str)          
    
    # New Signals for the visual overlay
    wake_word_detected = pyqtSignal()
    transcription_update = pyqtSignal(str)
    sleep_mode = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.is_running = True
        self.is_awake = False  

        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8

    def run(self):
        # We must silence BOTH the instantiation AND the stream opening!
        with silence_audio_warnings():
            self.microphone = sr.Microphone()
            source = self.microphone.__enter__()
            
        try:
            self.status_changed.emit("Calibrating microphone...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
            
            while self.is_running:
                try:
                    if not self.is_awake:
                        self.status_changed.emit("Waiting for 'Hey Ghost'...")
                        audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=3)
                        text = self.recognizer.recognize_google(audio, language="en-US").lower().strip()
                        
                        if "hey ghost" in text or "hi ghost" in text or "okay ghost" in text:
                            print("[Voice Assistant] Wake word detected!")
                            self.is_awake = True
                            self.wake_word_detected.emit() 
                            
                            # Did they say the command in the same breath?
                            wake_idx = text.find("ghost") + len("ghost")
                            remaining_command = text[wake_idx:].strip()
                            
                            if len(remaining_command) > 2:
                                self.transcription_update.emit(f'"{remaining_command.capitalize()}"')
                                self.msleep(1200) # Pause so the user can read the transcription on screen
                                self.parse_command(remaining_command)
                                self.is_awake = False
                                self.sleep_mode.emit() 
                            else:
                                self.transcription_update.emit("Listening...")
                                
                    else:
                        # We are fully awake, wait for the actual instruction
                        audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                        self.transcription_update.emit("Processing...")
                        text = self.recognizer.recognize_google(audio, language="en-US").lower().strip()
                        
                        self.transcription_update.emit(f'"{text.capitalize()}"')
                        self.msleep(1200) # Pause so the user can read the transcription on screen
                        
                        print(f"[Voice Assistant] Command: '{text}'")
                        self.parse_command(text)
                        
                        self.is_awake = False 
                        self.sleep_mode.emit()
                        
                except sr.WaitTimeoutError:
                    if self.is_awake:
                        self.transcription_update.emit("Canceled.")
                        self.msleep(1000)
                        self.is_awake = False
                        self.sleep_mode.emit()
                except sr.UnknownValueError:
                    if self.is_awake:
                        self.transcription_update.emit("Didn't catch that.")
                        self.msleep(1000)
                        self.is_awake = False
                        self.sleep_mode.emit()
                except sr.RequestError:
                    if self.is_awake:
                        self.transcription_update.emit("Offline.")
                        self.msleep(1000)
                        self.is_awake = False
                        self.sleep_mode.emit()
                except Exception as e:
                    if self.is_awake:
                        self.is_awake = False
                        self.sleep_mode.emit()
        finally:
            if self.microphone:
                self.microphone.__exit__(None, None, None)

    def stop(self):
        self.is_running = False

    def parse_command(self, phrase):
        """Intelligent Natural Language Router for Kiosk Functions."""
        
        # --- App Management Intents ---
        if "open" in phrase or "launch" in phrase:
            if "gallery" in phrase:
                self.command_recognized.emit("launch_app", "Gallery")
            elif "music" in phrase:
                self.command_recognized.emit("launch_app", "Local Music")
            elif "store" in phrase or "shop" in phrase:
                self.command_recognized.emit("launch_app", "App Store")
            elif "settings" in phrase:
                self.command_recognized.emit("launch_app", "Settings")
                
        elif "close" in phrase or "go home" in phrase or "exit" in phrase:
            self.command_recognized.emit("close_app", "")

        # --- Clockface Switching Intents ---
        elif "change clock" in phrase or "switch clock" in phrase or "show clock" in phrase:
            if "classic" in phrase or "digital" in phrase:
                self.command_recognized.emit("change_clock", "0")
            elif "stacked" in phrase or "bold" in phrase:
                self.command_recognized.emit("change_clock", "1")
            elif "analog" in phrase or "minimal" in phrase:
                self.command_recognized.emit("change_clock", "2")
            elif "neon" in phrase or "green" in phrase:
                self.command_recognized.emit("change_clock", "3")

        # --- System Action Intents ---
        elif "reboot" in phrase or "restart" in phrase:
            self.command_recognized.emit("system", "reboot")
        elif "shutdown" in phrase or "power off" in phrase:
            self.command_recognized.emit("system", "shutdown")