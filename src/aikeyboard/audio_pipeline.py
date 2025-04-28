# === DO NOT CLEANUP OR REFACTOR UNLESS EXPLICITLY REQUESTED ===
# This file is under minimal-diff development policy:
# - Keep existing structure, names, and logic intact.
# - Only add/change lines that are necessary for the requested feature.
# - Avoid reordering, renaming, or reformatting.
# Cleanup passes will be done separately.

import json
from PySide6.QtCore import QObject, QThread, Signal, Slot
import sounddevice as sd
import numpy as np
from vosk import Model, KaldiRecognizer

VOSK_MODEL = "vosk-model-small-it-0.22"

class AudioCaptureWorker(QObject):
    SAMPLE_RATE = 16000
    BLOCK_DURATION = 0.2                            # 100ms
    BLOCK_SIZE = int(SAMPLE_RATE * BLOCK_DURATION)
    SILENCE_THRESHOLD = 400000                      # Energy threshold
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

    def _callback(self, indata, frames, time, status):
        if self.running:
            self.audio_data.emit(bytes(indata))     # unused
            audio_data = np.squeeze(indata.copy())
            energy = np.sum(np.abs(audio_data))
            print(f"{energy:7d}  ({len(self._buffer):5d};{self._silence_blocks:5d};{self._sent_chunks:5d};{self.received_chunks:5d})", end='\r')

            if energy >= self.SILENCE_THRESHOLD:
                self._buffer.append(audio_data)
                self._silence_blocks = 0
            elif self._buffer:
                self._silence_blocks += 1
                if self._silence_blocks >= self.MAX_SILENCE_BLOCKS:
                    chunk = np.concatenate(self._buffer)
                    self.audio_chunk.emit(chunk)
                    self._buffer.clear()
                    self._silence_blocks = 0
                    self._sent_chunks += 1

                    
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
        while data:
            if self.rec.AcceptWaveform(data):
                result = json.loads(self.rec.Result())
                text = result.get("text", "")
                self.transcription.emit(result)
                self.t.received_chunks += 1
                data = []
            else:
                partial = json.loads(self.rec.PartialResult())
                text = partial.get("partial", "")
                print("[PARTIAL]", text)
                blocks = max(len(data) / AudioCaptureWorker.BLOCK_SIZE, AudioCaptureWorker.MAX_SILENCE_BLOCKS) -1
                data = data[-blocks*AudioCaptureWorker.BLOCK_SIZE:]


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
    from PySide6.QtWidgets import QApplication
    import sys
    import signal

    app = QApplication(sys.argv)
    pipeline = AudioPipeline()

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("Stopping...")
        pipeline.shutdown()
        sys.exit(0)
        