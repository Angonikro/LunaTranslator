import json
from pathlib import Path

APP_DIR = Path.home() / ".config" / "LunaTranslator"
SETTINGS_FILE = APP_DIR / "settings.json"

DEFAULTS = {
    "language": "de",
    "provider": "Google Übersetzer",
    "source_language": "auto",
    "target_language": "en",
    "mymemory_email": "",
    "theme": "graphite",
    "mbrola_voice": "auto",
    "audio_backend": "auto",
    "audio_device": "",
    "microphone_device": "",
}

def load_settings():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    data = dict(DEFAULTS)
    try:
        stored = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        if isinstance(stored, dict):
            data.update(stored)
            # Migrate the original 0.1.0 demo endpoint, which returned HTTP 400.
            # Migrate configurations that selected providers requiring credentials.
            if data.get("provider") in ("LibreTranslate", "DeepL", "Apertium", "Argos Translate"):
                data["provider"] = "Google Übersetzer"
            for obsolete in ("deepl_api_key", "libretranslate_api_key", "libretranslate_url"):
                data.pop(obsolete, None)
    except (OSError, json.JSONDecodeError):
        pass
    return data

def save_settings(data):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    SETTINGS_FILE.chmod(0o600)
