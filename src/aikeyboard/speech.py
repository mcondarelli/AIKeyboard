# src/aikeyboard/speech.py
import json
import logging
import time
from typing import Optional

import pyaudio
import numpy as np
from scipy.signal import resample_poly

from PySide6.QtCore import Property, QObject, QThread, Signal, Slot
from vosk import KaldiRecognizer, Model

from aikeyboard.model_cache import model_cache


class SpeechWorker(QObject):
    state_changed = Signal(str)  # "listening", "processing", "idle"
    partial_result = Signal(str)
    recognized = Signal(str)     # Signal emitted when text is recognized
    finished = Signal()          # Signal emitted when thread finishes
    error = Signal(str)          # Signal emitted on errors

    def __init__(self, device_index=None):
        super().__init__()
        self.device_index: Optional[int] = device_index
        self._stop_requested = False
        self._state = "idle"

    @Property(str, notify=state_changed) # type: ignore[call-arg]
    def state(self) -> str: # type: ignore
        return self._state
    
    @state.setter
    def state(self, state: str) -> None:
        if self._state != state:
            self._state = state
            self.state_changed.emit(self._state)

    @Slot()
    def start_listening(self):
        """Start the speech recognition loop"""
        output_rate = 16000
        self.state = "uninitialized" # type: ignore
        try:
            if self.device_index is None:
                raise ValueError("device_index is not set")
            # Initialization
            stream = None
            model_path = model_cache.ensure_model()
            model = Model(model_path)
            time.sleep(0.25)
            rec = KaldiRecognizer(model, output_rate)
            time.sleep(0.25)
            pa = pyaudio.PyAudio()

            # Query actual rate of the selected input device
            device_info = pa.get_device_info_by_index(self.device_index)
            input_rate = int(device_info['defaultSampleRate'])
            logging.info(f"Input rate for device {self.device_index}-{device_info['name']}: {input_rate} Hz")
            if device_info.get("maxInputChannels", 0) == 0:
                raise RuntimeError(f"Device {self.device_index} does not support input!")
        
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=input_rate,
                input=True,
                frames_per_buffer=8192,
                input_device_index=self.device_index
            )

            # Main loop
            self.state = "listening" # type: ignore
            while not self._stop_requested:
                try:
                    data = stream.read(4096, exception_on_overflow=False)
                except Exception as e:
                    logging.warning(f"Audio read error: {e}")
                    continue

                # Downsample to 16000 if needed
                if input_rate != output_rate:
                    try:
                        # data = audioop.ratecv(data, 2, 1, input_rate, 16000, None)[0]

                        # Convert bytes to numpy array (16-bit mono audio)
                        audio = np.frombuffer(data, dtype=np.int16)

                        # Calculate GCD for rational resample
                        gcd = np.gcd(input_rate, output_rate)
                        up = output_rate // gcd
                        down = input_rate // gcd

                        # Perform polyphase resampling
                        resampled = resample_poly(audio, up, down)

                        # Convert back to bytes
                        data = resampled.astype(np.int16).tobytes()

                    except Exception as e:
                        logging.warning(f"Resample error: {e}")
                        continue                

                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").strip()
                    if text:
                        self.recognized.emit(text)
                    self.state = "listening" # type: ignore
                else:
                    # Handle partial results and pause detection
                    partial = json.loads(rec.PartialResult())
                    if partial.get("partial", ""):
                        self.partial_result.emit(partial['partial'])
                        self.state= "processing" # type: ignore
                
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.state = "idle" # type: ignore
            # Clean up audio resources
            if stream:
                stream.stop_stream()
                stream.close()
            pa.terminate()
            self.finished.emit()

    @Slot()
    def stop_listening(self):
        """Request the thread to stop"""
        self._stop_requested = True


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
            
