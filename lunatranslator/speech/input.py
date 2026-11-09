"""Microphone capture with SpeechRecognition/PyAudio and Google STT."""
from __future__ import annotations

import threading


LANGUAGE_LOCALES = {
    "de": "de-DE", "en": "en-US", "fr": "fr-FR", "it": "it-IT",
    "nl": "nl-NL", "es": "es-ES", "pt": "pt-PT", "pl": "pl-PL",
    "ru": "ru-RU", "ja": "ja-JP", "zh": "zh-CN",
}


def microphone_devices():
    """Return PortAudio input device indices and names exposed by PyAudio."""
    try:
        import pyaudio
        pa = pyaudio.PyAudio()
        devices = [("", "Systemstandard / Standardmikrofon")]
        try:
            for index in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(index)
                if int(info.get("maxInputChannels", 0)) > 0:
                    name = str(info.get("name") or f"Mikrofon {index}").strip()
                    devices.append((str(index), f"{index}: {name}"))
        finally:
            pa.terminate()
        return devices
    except Exception:
        return [("", "Systemstandard / Standardmikrofon")]


class SpeechInput:
    """Record phrase chunks in a dedicated thread and transcribe them online."""

    def __init__(self):
        self.recognizer = None
        self.microphone = None
        self._thread = None
        self._stop_event = threading.Event()
        self._chunks = []
        self._error = None
        self._lock = threading.Lock()

    def start(self, device=""):
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("Eine Mikrofonaufnahme läuft bereits.")
        try:
            import speech_recognition
        except ImportError as exc:
            raise RuntimeError(
                "SpeechRecognition fehlt. Bitte mit derselben Python-Installation wie LunaTranslator installieren."
            ) from exc

        self._stop_event.clear()
        self._chunks = []
        self._error = None
        try:
            device_index = int(device) if str(device).strip() else None
            self.recognizer = speech_recognition.Recognizer()
            # Let PortAudio choose a supported rate for the selected device.
            self.microphone = speech_recognition.Microphone(device_index=device_index)
            self._thread = threading.Thread(target=self._record_loop, args=(), daemon=True)
            self._thread.start()
        except Exception as exc:
            self.microphone = None
            raise RuntimeError(f"Mikrofon konnte nicht geöffnet werden: {exc}") from exc
        return "Aufnahme läuft · Mikrofon wird eingepegelt …"

    def _record_loop(self):
        import speech_recognition
        try:
            with self.microphone as source:
                # Calibrate against room noise before listening, as in the supplied
                # Sprachassistent project. Do not force a device sample rate.
                self.recognizer.adjust_for_ambient_noise(source, duration=0.6)
                while not self._stop_event.is_set():
                    try:
                        audio = self.recognizer.listen(
                            source, timeout=1, phrase_time_limit=8
                        )
                    except speech_recognition.WaitTimeoutError:
                        continue
                    with self._lock:
                        self._chunks.append(audio)
        except Exception as exc:
            self._error = exc
        finally:
            self.microphone = None

    def stop(self):
        # Import here as well: stop() constructs AudioData after the recording
        # thread has finished, and its local imports are not shared across methods.
        import speech_recognition

        thread = self._thread
        if thread is None:
            raise RuntimeError("Es läuft keine Mikrofonaufnahme.")
        self._stop_event.set()
        thread.join(timeout=12)
        if thread.is_alive():
            raise RuntimeError("Mikrofonaufnahme konnte nicht rechtzeitig beendet werden. Bitte erneut versuchen.")
        self._thread = None
        if self._error is not None:
            raise RuntimeError(f"Fehler bei der Mikrofonaufnahme: {self._error}") from self._error
        with self._lock:
            chunks = list(self._chunks)
        if not chunks:
            raise RuntimeError(
                "Keine Sprache aufgenommen. Prüfe in den Einstellungen das richtige Mikrofon, "
                "die Mikrofonlautstärke und die Aufnahmeberechtigung. Sprich nach dem Start, "
                "warte kurz und drücke dann Stopp."
            )
        # Preserve every spoken phrase captured during the recording session.
        first = chunks[0]
        raw = b"".join(chunk.get_raw_data() for chunk in chunks)
        return speech_recognition.AudioData(raw, first.sample_rate, first.sample_width)

    @staticmethod
    def transcribe(audio, language="auto"):
        import speech_recognition
        locale = LANGUAGE_LOCALES.get((language or "auto").lower(), "de-DE")
        try:
            text = speech_recognition.Recognizer().recognize_google(audio, language=locale)
        except speech_recognition.UnknownValueError as exc:
            raise RuntimeError("Die Aufnahme enthielt Sprache, aber Google konnte sie nicht verstehen. Bitte deutlicher und näher am Mikrofon sprechen.") from exc
        except speech_recognition.RequestError as exc:
            raise RuntimeError(f"Google-Spracherkennung nicht erreichbar: {exc}") from exc
        text = (text or "").strip()
        if not text:
            raise RuntimeError("Es wurde kein verständlicher Text erkannt.")
        return text
