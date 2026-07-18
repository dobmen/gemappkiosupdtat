import os
from PyQt6.QtCore import QThread, pyqtSignal
import speech_recognition as sr

class VoiceAssistantThread(QThread):
    # Signals to communicate cleanly with the core Kiosk window
    command_recognized = pyqtSignal(str, str)  # (intent, argument)
    status_changed = pyqtSignal(str)          # For updating UI listening status

    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_running = True
        self.is_awake = False  # State tracker for the wake word

        # Tweak thresholds for ambient kiosk background noise
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8

    def run(self):
        with self.microphone as source:
            # Calibrate for environmental acoustics before entering the loop
            self.status_changed.emit("Calibrating microphone...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
            
            while self.is_running:
                try:
                    if not self.is_awake:
                        self.status_changed.emit("Waiting for 'Hey Ghost'...")
                        # Listen in short bursts so we don't hold the microphone open forever
                        audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=3)
                        text = self.recognizer.recognize_google(audio, language="en-US").lower().strip()
                        
                        # Check for variations of the wake word
                        if "hey ghost" in text or "hi ghost" in text or "okay ghost" in text:
                            print("[Voice Assistant] Wake word detected!")
                            self.is_awake = True
                            
                            # Did they say the command in the same breath? (e.g., "Hey Ghost open gallery")
                            wake_idx = text.find("ghost") + len("ghost")
                            remaining_command = text[wake_idx:].strip()
                            
                            if len(remaining_command) > 2:
                                self.parse_command(remaining_command)
                                self.is_awake = False  # Go back to sleep immediately
                            else:
                                self.status_changed.emit("Listening for command...")
                                
                    else:
                        # We are fully awake, wait for the actual instruction
                        audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                        self.status_changed.emit("Processing...")
                        text = self.recognizer.recognize_google(audio, language="en-US").lower().strip()
                        
                        print(f"[Voice Assistant] Command: '{text}'")
                        self.parse_command(text)
                        
                        # Go back to sleep after executing the command
                        self.is_awake = False 
                        
                except sr.WaitTimeoutError:
                    # If they woke the assistant but didn't say anything, go back to sleep
                    if self.is_awake:
                        print("[Voice Assistant] Command timeout. Going back to sleep.")
                        self.is_awake = False
                except sr.UnknownValueError:
                    # Speech was detected but wasn't clear enough to parse
                    if self.is_awake:
                        self.is_awake = False
                except sr.RequestError:
                    self.status_changed.emit("API Connection Offline")
                    self.msleep(5000)
                except Exception as e:
                    self.is_awake = False

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