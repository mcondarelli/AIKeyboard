# src/aikeyboard/speech.py
from typing import Optional
import pyaudio
from vosk import Model, KaldiRecognizer
import json
import time
import logging
from PySide6.QtCore import QObject, Signal, Slot, QThread


class SpeechWorker(QObject):
    state_changed = Signal(str)  # "listening", "processing", "idle"
    partial_result = Signal(str)
    recognized = Signal(str)  # Signal emitted when text is recognized
    finished = Signal()       # Signal emitted when thread finishes
    error = Signal(str)       # Signal emitted on errors

    def __init__(self, device_index=None):
        super().__init__()
        self.device_index = device_index
        self._stop_requested = False
        self.model = Model("vosk-model-small-it-0.22")
        self.rec = KaldiRecognizer(self.model, 16000)
        self.pa = pyaudio.PyAudio()
        self.stream = None

    @Slot()
    def start_listening(self):
        """Start the speech recognition loop"""
        try:
            self.state_changed.emit("listening")
            self.stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=8192,
                input_device_index=self.device_index
            )
            
            self.last_audio_time = 0
            self.state_changed.emit("listening")
            
            while not self._stop_requested:
                data = self.stream.read(4096, exception_on_overflow=False)
                self.last_audio_time = time.time()
                
                if self.rec.AcceptWaveform(data):
                    result = json.loads(self.rec.Result())
                    text = result.get("text", "").strip()
                    if text:
                        self.state_changed.emit("processing")
                        self.recognized.emit(text)
                        self.state_changed.emit("listening")
                
                # Handle partial results and pause detection
                partial = json.loads(self.rec.PartialResult())
                if partial.get("partial", ""):
                    self.partial_result.emit(partial['partial'])
                    if time.time() - self.last_audio_time > 1.0:  # 1 second pause
                        self.state_changed.emit("processing")
                        self.recognized.emit(partial['partial'].strip())
                        self.state_changed.emit("listening")

        except Exception as e:
            self.state_changed.emit("idle")
            self.error.emit(str(e))
        finally:
            self.state_changed.emit("idle")
            self._cleanup()
            self.finished.emit()

    @Slot()
    def stop_listening(self):
        """Request the thread to stop"""
        self._stop_requested = True

    def _cleanup(self):
        """Clean up audio resources"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        self.pa.terminate()



class SpeechRecognizer(QObject):
    worker_created = Signal(object)

    def __init__(self, device_index=None):
        super().__init__()
        self.device_index = device_index
        self.worker: Optional[SpeechWorker] = None
        self.thread: Optional[QThread] = None

    def __del__(self):
        self.stop_listening()  # Ensure cleanup on deletion

    def start_listening(self):
        """Start speech recognition in a QThread"""
        if self.thread and self.thread.isRunning():
            self.stop_listening()

        # Setup worker and thread
        self.worker = SpeechWorker(self.device_index)
        self.thread = QThread()

        # Emit signal after worker is created
        self.worker_created.emit(self.worker)
        
        # Move worker to thread
        self.worker.moveToThread(self.thread)
        
        # Connect signals
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(lambda e: logging.error(f"Speech error: {e}"))
        
        # Start the thread
        self.thread.started.connect(self.worker.start_listening)
        self.thread.finished.connect(self.worker.deleteLater)

        self.thread.started.connect(lambda: logging.debug("Thread started"))        # for debugging only
        self.thread.finished.connect(lambda: logging.debug("Thread finished"))      # for debugging only

        self.thread.start()

    def stop_listening(self):
        """Stop the speech recognition thread"""
        if self.worker:
            self.worker.stop_listening()
            self.worker = None            
        if self.thread:
            self.thread.quit()
            self.thread.wait(500)
            if self.thread.isRunning():
                self.thread.terminate()
            self.thread.deleteLater()
            self.thread = None
            
