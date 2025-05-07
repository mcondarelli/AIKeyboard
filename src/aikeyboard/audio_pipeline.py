# === DO NOT CLEANUP OR REFACTOR UNLESS EXPLICITLY REQUESTED ===
# This file is under minimal-diff development policy:
# - Keep existing structure, names, and logic intact.
# - Only add/change lines that are necessary for the requested feature.
# - Avoid reordering, renaming, or reformatting.
# Cleanup passes will be done separately.

import json
import time

import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, QThread, Signal, Slot
from vosk import KaldiRecognizer, Model

VOSK_MODEL = "vosk-model-small-it-0.22"


class SilenceDetector:
    def __init__(self, calibration_duration=2.0, sample_rate=16000, margin_db=3.0):
        self.calibration_duration = calibration_duration
        self.sample_rate = sample_rate
        self.margin_db = margin_db
        self.calibration_buffer = []
        self.calibrated = False
        self.noise_floor_db = -40.0
        self.start_time = time.monotonic()

    def _dbfs(self, float_data: np.ndarray) -> float:
        rms = np.sqrt(np.mean(float_data ** 2))
        return 20 * np.log10(rms + 1e-10)

    def is_silence(self, indata: np.ndarray) -> bool:
        # normalize int16 → float32 in -1.0 ... +1.0
        audio_data = np.squeeze(indata).astype(np.float32) / 32768.0

        now = time.monotonic()

        if not self.calibrated:
            self.calibration_buffer.append(audio_data)
            if now - self.start_time >= self.calibration_duration:
                rms_values = [np.sqrt(np.mean(chunk ** 2)) for chunk in self.calibration_buffer]
                rms_median = np.median(rms_values)
                self.noise_floor_db = 20 * np.log10(rms_median + 1e-10)
                self.calibrated = True
                print(f"[Calibration] Noise floor estimated at {self.noise_floor_db:.1f} dBFS")
            return True  # assume silence during calibration

        # Check current block against noise floor
        current_db = self._dbfs(audio_data)
        silence_threshold = max(self.noise_floor_db + self.margin_db, -40.0)
        print(f'is_silence(): current_db({current_db}) < silence_threshold({silence_threshold})', end='\r')
        return current_db < silence_threshold



class AudioCaptureWorker(QObject):
    SAMPLE_RATE = 16000
    BLOCK_DURATION = 0.2                            # 200ms
    BLOCK_SIZE = int(SAMPLE_RATE * BLOCK_DURATION)  # 3200
    SILENCE_THRESHOLD = 900000                      # Energy threshold
    MAX_SILENCE_BLOCKS = int(1.0 / BLOCK_DURATION)  # 1s silence

    audio_data = Signal(bytes)                      # emitted but not connected
    audio_chunk = Signal(np.ndarray)
    error_occurred = Signal(str)

    def __init__(self, device=None, samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE):
        super().__init__()
        self.device = device
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.running = False
        self.stream = None
        self._buffer = []
        self._silence_blocks = 0
        self._sent_chunks = 0
        self.received_chunks = 0
        self.silence_detector = SilenceDetector()

    def start(self):
        try:
            self.stream = sd.InputStream(
                samplerate=self.samplerate,
                blocksize=self.blocksize,
                dtype='int16',
                channels=1,
                callback=self._callback,
                device=self.device
            )
            self.stream.start()
            self.running = True
        except Exception as e:
            self.error_occurred.emit(e)

    def _callback(self, indata, _frames, _time, _status):
        if self.running:
            self.audio_data.emit(bytes(indata))     # unused
            
            if not self.silence_detector.calibrated:
               self.silence_detector.is_silence(indata)
               print(f'_callback(): {time.monotonic() - self.silence_detector.start_time} >= {self.silence_detector.calibration_duration}', end='\r')
               return 
            
            if self.silence_detector.is_silence(indata):
                self._buffer.append(np.squeeze(indata.copy()))
                self._silence_blocks = 0
            elif self._buffer:
                self._silence_blocks += 1
                if self._silence_blocks > self.MAX_SILENCE_BLOCKS:
                    chunk = np.concatenate(self._buffer)
                    self.audio_chunk.emit(chunk)
                    self._buffer.clear()
                    self._silence_blocks = 0
                    self._sent_chunks += 1
                else:
                    self._buffer.append(np.squeeze(indata.copy()))

    def stop(self):
        self.running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None


class Transcriber(QObject):
    transcription = Signal(str)

    def __init__(self, samplerate,t):
        super().__init__()
        self.t = t
        self.model = Model(VOSK_MODEL)
        self.rec = KaldiRecognizer(self.model, samplerate)

    @Slot(np.ndarray)
    def receive_audio(self, data):
        self.t.received_chunks += 1
        data = data.tobytes()
        print(f"[DEBUG] Utterance buffer size: {len(data)} bytes ({len(data)/AudioCaptureWorker.BLOCK_SIZE} blocks -> {len(data)/16000/2:.2f} sec)")
        while data:
            if self.rec.AcceptWaveform(data):
                result = json.loads(self.rec.FinalResult())
                print("[DEBUG] Raw recognizer.Result():", result)
                self.transcription.emit(result.get('text'))
                self.t.received_chunks += 1
                break
            else:
                blocks = min(len(data) // AudioCaptureWorker.BLOCK_SIZE, AudioCaptureWorker.MAX_SILENCE_BLOCKS) -1
                print(f'[PARTIAL] ({blocks}->{blocks*AudioCaptureWorker.BLOCK_SIZE}) "{self.rec.PartialResult()}"')
                if blocks > 0:
                    data = data[-blocks*AudioCaptureWorker.BLOCK_SIZE:]
                else:
                    self.rec.FinalResult()
                    break


class AudioPipeline(QObject):
    def __init__(self):
        super().__init__()
        # Threads
        self.capture_thread = QThread()
        self.transcriber_thread = QThread()

        # Workers
        self.capture_worker = AudioCaptureWorker("USB Device 0x46d:0x9a4")
        self.transcriber = Transcriber(self.capture_worker.samplerate, self.capture_worker)

        # Move to threads
        self.capture_worker.moveToThread(self.capture_thread)
        self.transcriber.moveToThread(self.transcriber_thread)

        # Connect signals
        self.capture_thread.started.connect(self.capture_worker.start)
        self.capture_worker.audio_chunk.connect(self.transcriber.receive_audio)

        self.transcriber.transcription.connect(self.handle_transcription)

        # Start threads
        self.capture_thread.start()
        self.transcriber_thread.start()

    @Slot(str)
    def handle_transcription(self, result):
        print("[TRANSCRIBED]", result)

    def shutdown(self):
        self.capture_worker.stop()
        self.capture_thread.quit()
        self.capture_thread.wait()
        self.transcriber_thread.quit()
        self.transcriber_thread.wait()



if __name__ == "__main__":
    import signal
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    pipeline = AudioPipeline()

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("Stopping...")
        pipeline.shutdown()
        sys.exit(0)
        