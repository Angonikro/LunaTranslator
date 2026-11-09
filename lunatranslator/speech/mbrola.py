"""Discoverable MBROLA voices and multilingual speech output via eSpeak NG."""
from __future__ import annotations

import re
import shutil
import subprocess
import threading
import tempfile
import json
from pathlib import Path

LANGUAGE_NAMES = {
    "af": "Afrikaans", "ar": "Arabisch", "br": "Bretonisch",
    "pt-br": "Brasilianisches Portugiesisch", "ca": "Katalanisch",
    "zh": "Chinesisch (Mandarin)", "hr": "Kroatisch", "cs": "Tschechisch",
    "de": "Deutsch", "et": "Estnisch", "en": "Englisch",
    "fr": "Französisch", "gl": "Galicisch", "el": "Griechisch",
    "hi": "Hindi", "hu": "Ungarisch", "is": "Isländisch",
    "it": "Italienisch", "ja": "Japanisch", "ko": "Koreanisch",
    "nl": "Niederländisch", "pl": "Polnisch", "pt": "Portugiesisch",
    "ro": "Rumänisch", "ru": "Russisch", "sk": "Slowakisch",
    "es": "Spanisch", "sv": "Schwedisch", "tr": "Türkisch",
    "cy": "Walisisch", "eu": "Baskisch", "no": "Norwegisch",
    "da": "Dänisch", "fi": "Finnisch",
}

# Language codes are taken from eSpeak NG's --voices=mb output where possible.
VOICE_LANGUAGE = {
    "af": "af", "ar": "ar", "br": "pt-br", "bz": "br", "ca": "fr",
    "cn": "zh", "cr": "hr", "cz": "cs", "de": "de", "ee": "et",
    "en": "en", "es": "es", "fr": "fr", "gr": "el", "hr": "hr",
    "hu": "hu", "is": "is", "it": "it", "jp": "ja", "la": "la",
    "nl": "nl", "pl": "pl", "pt": "pt", "ro": "ro", "ru": "ru",
    "sk": "sk", "sp": "es", "sw": "sv", "tr": "tr",
}
LANGUAGE_VOICES = {
    "de": "mb-de1", "en": "mb-en1", "fr": "mb-fr1",
    "it": "mb-it1", "nl": "mb-nl1", "es": "mb-es1",
}


def discover_mbrola_voices():
    """Return MBROLA voice definitions known to eSpeak NG and data availability."""
    espeak = shutil.which("espeak-ng")
    if not espeak:
        return []
    try:
        result = subprocess.run(
            [espeak, "--voices=mb"], capture_output=True, text=True,
            timeout=8, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    voices = {}
    for line in result.stdout.splitlines():
        match = re.search(r"\b(mb-[a-z0-9]+(?:-[a-z]+)?)\b", line, re.I)
        if not match:
            continue
        voice_id = match.group(1).lower()
        tokens = line.split()
        language_code = tokens[1].lower() if len(tokens) > 1 else ""
        base_code = voice_id[3:].split("-")[0]
        language = language_code if language_code not in ("mb", "misc") else VOICE_LANGUAGE.get(base_code[:2], base_code[:2])
        # eSpeak voice entries can exist even when the MBROLA diphone data is absent.
        voice_code = base_code
        candidates = [
            Path("/usr/share/mbrola") / voice_code / voice_code,
            Path("/usr/share/mbrola") / voice_code,
            Path("/usr/local/share/mbrola") / voice_code / voice_code,
            Path("/usr/local/share/mbrola") / voice_code,
        ]
        data_installed = any(p.is_file() and p.stat().st_size > 0 for p in candidates)
        gender = ""
        if len(tokens) > 2 and tokens[2].upper() in ("M", "F", "MALE", "FEMALE"):
            gender = {"M": "männlich", "F": "weiblich", "MALE": "männlich", "FEMALE": "weiblich"}[tokens[2].upper()]
        voices[voice_id] = {
            "id": voice_id,
            "module": voice_code,
            "language": language,
            "language_name": LANGUAGE_NAMES.get(language, language.upper()),
            "gender": gender,
            "installed": data_installed,
        }
    return sorted(voices.values(), key=lambda v: (v["language_name"], v["id"]))


def audio_backends():
    options = [("auto", "Automatisch (Systemstandard)")]
    if shutil.which("pw-play"):
        options.append(("pipewire", "PipeWire"))
    if shutil.which("paplay"):
        options.append(("pulse", "PulseAudio / PipeWire-Pulse"))
    if shutil.which("aplay"):
        options.append(("alsa", "ALSA"))
    return options


def audio_devices(backend="auto"):
    """Return selectable output devices for the chosen Linux audio backend."""
    devices = [("", "Systemstandard") ]
    if backend in ("auto", "pipewire", "pulse") and shutil.which("pactl"):
        try:
            result = subprocess.run(["pactl", "-f", "json", "list", "sinks"],
                                    capture_output=True, text=True, timeout=5, check=False)
            if result.returncode == 0:
                for sink in json.loads(result.stdout):
                    name = sink.get("name", "")
                    desc = sink.get("description") or name
                    if name:
                        devices.append((name, desc))
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
    if backend == "alsa" and shutil.which("aplay"):
        try:
            result = subprocess.run(["aplay", "-L"], capture_output=True, text=True, timeout=5, check=False)
            for line in result.stdout.splitlines():
                if line and not line[0].isspace() and line not in ("null",):
                    devices.append((line, line))
        except (OSError, subprocess.TimeoutExpired):
            pass
    # Preserve order while removing duplicates.
    seen = set()
    return [item for item in devices if not (item[0] in seen or seen.add(item[0]))]



def audio_input_devices(backend="auto"):
    """Return selectable microphone/input devices for the selected audio stack."""
    devices = [("", "Systemstandard / Standardmikrofon")]
    if backend in ("auto", "pipewire", "pulse") and shutil.which("pactl"):
        try:
            result = subprocess.run(["pactl", "-f", "json", "list", "sources"],
                                    capture_output=True, text=True, timeout=5, check=False)
            if result.returncode == 0:
                for source in json.loads(result.stdout):
                    name = source.get("name", "")
                    # Monitor sources are outputs looped back as inputs, not microphones.
                    if not name or name.endswith(".monitor"):
                        continue
                    desc = source.get("description") or name
                    devices.append((name, desc))
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
    if backend == "alsa" and shutil.which("arecord"):
        try:
            result = subprocess.run(["arecord", "-L"], capture_output=True, text=True,
                                    timeout=5, check=False)
            for line in result.stdout.splitlines():
                if line and not line[0].isspace() and line not in ("null",):
                    devices.append((line, line))
        except (OSError, subprocess.TimeoutExpired):
            pass
    seen = set()
    return [item for item in devices if not (item[0] in seen or seen.add(item[0]))]

def installed_voice_options():
    return [v for v in discover_mbrola_voices() if v["installed"]]


def voice_label(voice):
    suffix = f" · {voice['gender']}" if voice.get("gender") else ""
    return f"{voice['language_name']} – {voice['module']}{suffix}"


class MbrolaSpeech:
    def __init__(self):
        self._lock = threading.Lock()
        self._processes = []

    @staticmethod
    def _player(backend="auto", device=""):
        candidates = {
            "pipewire": ("pw-play",),
            "pulse": ("paplay",),
            "alsa": ("aplay",),
            "auto": ("pw-play", "paplay", "aplay"),
        }.get(backend, ("pw-play", "paplay", "aplay"))
        for command in candidates:
            path = shutil.which(command)
            if not path:
                continue
            args = [path]
            if command == "aplay":
                args.append("-q")
                if device:
                    args.extend(["-D", device])
            elif command == "paplay" and device:
                args.extend(["--device", device])
            elif command == "pw-play" and device:
                args.extend(["--target", device])
            return args, command
        raise RuntimeError("Der ausgewählte Audiotreiber ist nicht installiert oder nicht verfügbar.")

    @staticmethod
    def _normal_language(language):
        return (language or "en").lower().replace("_", "-").split("-")[0]

    @staticmethod
    def _select_voice(language, selected, voices):
        if selected and selected != "auto":
            voice = next((v for v in voices if v["id"] == selected), None)
            if voice is None:
                raise RuntimeError(
                    f"Das ausgewählte MBROLA-Modul {selected} ist nicht installiert. "
                    "Bitte in Einstellungen ein verfügbares Modul wählen."
                )
            return voice["id"]

        lang = MbrolaSpeech._normal_language(language)
        matches = [v for v in voices if v["language"] == lang]
        if matches:
            preferred = LANGUAGE_VOICES.get(lang)
            chosen = next((v for v in matches if v["id"] == preferred), matches[0])
            return chosen["id"]
        # If no MBROLA voice exists for the target language, use the native
        # eSpeak NG language voice rather than pronouncing it with another language.
        return None

    def speak(self, text, language="de", voice="auto", speed=155, backend="auto", device=""):
        text = (text or "").strip()
        if not text:
            raise RuntimeError("Es gibt keinen Text zum Vorlesen.")
        espeak = shutil.which("espeak-ng")
        if not espeak:
            raise RuntimeError("eSpeak NG ist nicht installiert. Bitte 'espeak-ng' installieren.")
        player, player_name = self._player(backend, device)
        voices = installed_voice_options()
        selected_voice = self._select_voice(language, voice, voices)
        selected_language = selected_voice or self._normal_language(language)
        command = [espeak, "-v", selected_language, "-s", str(int(speed)), "--stdout", text]

        # pw-play requires a filename; unlike paplay/aplay it does not reliably
        # consume WAV data from stdin. Use one temporary WAV for all players.
        wav_path = None
        try:
            with tempfile.NamedTemporaryFile(prefix="lunatranslator-", suffix=".wav", delete=False) as wav_file:
                wav_path = wav_file.name
                synth = subprocess.Popen(command, stdout=wav_file, stderr=subprocess.PIPE)
                with self._lock:
                    self._processes = [synth]
                _, synth_error = synth.communicate()
            if synth.returncode != 0:
                message = synth_error.decode("utf-8", "replace").strip()
                raise RuntimeError(message or "eSpeak NG konnte keine Audiodatei erzeugen.")
            if not Path(wav_path).is_file() or Path(wav_path).stat().st_size < 44:
                raise RuntimeError("eSpeak NG hat keine gültige WAV-Audiodatei erzeugt.")

            playback_command = list(player)
            playback_command.append(wav_path)
            try:
                playback = subprocess.Popen(
                    playback_command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
                )
            except OSError as exc:
                raise RuntimeError(f"Audioplayer konnte nicht gestartet werden: {exc}") from exc
            with self._lock:
                self._processes = [playback]
            _, player_error = playback.communicate()
            if playback.returncode != 0:
                message = (player_error or b"").decode("utf-8", "replace").strip()
                raise RuntimeError("Audiowiedergabe fehlgeschlagen" + (f": {message}" if message else ""))
            if selected_voice:
                return f"MBROLA-Modul: {selected_voice} · Audiotreiber: {player_name}"
            return f"eSpeak NG (Stimme {selected_language}) · Audiotreiber: {player_name}"
        except OSError as exc:
            raise RuntimeError(f"Sprachausgabe fehlgeschlagen: {exc}") from exc
        finally:
            with self._lock:
                self._processes = []
            if wav_path:
                try:
                    Path(wav_path).unlink(missing_ok=True)
                except OSError:
                    pass

    def stop(self):
        with self._lock:
            processes = list(self._processes)
        for process in reversed(processes):
            if process.poll() is None:
                try:
                    process.terminate()
                except OSError:
                    pass
