import re
import requests
from .base import TranslationEngine

GOOGLE_CODES = {"zh": "zh-CN"}

class GoogleTranslateEngine(TranslationEngine):
    """Google Translate web endpoint (no API key; unofficial endpoint)."""
    name = "Google Übersetzer"

    def translate(self, text, source, target):
        params = {
            "client": "gtx",
            "sl": "auto" if source == "auto" else GOOGLE_CODES.get(source, source),
            "tl": GOOGLE_CODES.get(target, target),
            "dt": "t",
            "q": text,
        }
        response = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params=params,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=45,
        )
        response.raise_for_status()
        data = response.json()
        try:
            result = "".join(part[0] for part in data[0] if part and part[0])
        except (TypeError, IndexError, KeyError) as exc:
            raise RuntimeError("Google Übersetzer hat eine unerwartete Antwort geliefert.") from exc
        if not result:
            raise RuntimeError("Google Übersetzer hat keinen Übersetzungstext geliefert.")
        return result


class MyMemoryEngine(TranslationEngine):
    """MyMemory REST translation-memory service with explicit MT enabled."""
    name = "MyMemory"

    def __init__(self, contact_email=""):
        self.contact_email = (contact_email or "").strip()

    @staticmethod
    def _chunks(text, max_bytes=450):
        chunks, current = [], ""
        for paragraph in text.splitlines() or [text]:
            words = paragraph.split()
            if not words:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.append("")
                continue
            for word in words:
                candidate = word if not current else current + " " + word
                if len(candidate.encode("utf-8")) > max_bytes and current:
                    chunks.append(current)
                    current = word
                else:
                    current = candidate
        if current:
            chunks.append(current)
        return chunks or [text]

    @staticmethod
    def _looks_wrong_target_language(translated, source, target):
        """Catch MyMemory hits that are fluent but still in the source language.

        This deliberately uses conservative stop-word signatures instead of
        guessing from one token. It is a fallback guard, not full language ID.
        """
        signatures = {
            "de": {"der", "die", "das", "und", "ist", "sind", "nicht", "ich", "du", "dir", "geht", "es", "wie", "gut", "hallo"},
            "en": {"the", "and", "is", "are", "not", "you", "your", "how", "hello", "good", "what", "do", "does"},
            "fr": {"le", "la", "les", "et", "est", "sont", "pas", "vous", "tu", "bonjour", "comment"},
            "es": {"el", "la", "los", "las", "y", "es", "son", "no", "hola", "como", "estás"},
            "it": {"il", "lo", "la", "gli", "e", "è", "sono", "non", "ciao", "come"},
            "nl": {"de", "het", "een", "en", "is", "niet", "je", "jij", "hallo", "hoe"},
        }
        source_words = signatures.get(source)
        target_words = signatures.get(target)
        if not source_words or not target_words:
            return False
        tokens = set(re.findall(r"[^\W\d_]+", translated.casefold(), flags=re.UNICODE))
        source_hits = len(tokens & source_words)
        target_hits = len(tokens & target_words)
        return source_hits >= 2 and target_hits == 0

    @staticmethod
    def _looks_unrelated(original, translated):
        """Reject malformed placeholders and obvious unrelated TM hits."""
        # MyMemory sometimes returns masked/redacted memory fragments such as
        # "Hallo xxxxx !!!!!". These are not valid translations and must never
        # be displayed to the user.
        if re.search(r"(?i)(?:[x*#]{2,}|\?{3,}|!{4,}|_{3,})", translated):
            return True
        src_words = len(original.split())
        dst_words = len(translated.split())
        if not src_words or not dst_words:
            return False
        # A short phrase receiving a much longer, unrelated catalogue-style
        # title is a common false positive from fuzzy translation memories.
        if src_words <= 5 and dst_words >= 3:
            ratio = len(translated.strip()) / max(1, len(original.strip()))
            if ratio > 2.6 and dst_words > src_words + 1:
                return True
        return False

    def translate(self, text, source, target):
        if source == "auto":
            raise RuntimeError(
                "MyMemory benötigt eine festgelegte Quellsprache. "
                "Bitte statt 'auto' die Sprache auswählen."
            )
        if source == target:
            return text

        results = []
        for chunk in self._chunks(text):
            if not chunk:
                results.append("")
                continue
            params = {
                "q": chunk,
                "langpair": f"{source}|{target}",
                "mt": 1,  # Explicitly enable machine translation in addition to memory matches.
            }
            if self.contact_email:
                params["de"] = self.contact_email
            try:
                response = requests.get(
                    "https://api.mymemory.translated.net/get",
                    params=params,
                    headers={"User-Agent": "LunaTranslator/0.2.16"},
                    timeout=(8, 30),
                )
                response.raise_for_status()
                data = response.json()
            except requests.Timeout as exc:
                raise RuntimeError(
                    "Zeitüberschreitung bei MyMemory. Bitte Verbindung prüfen "
                    "oder Eingabe und Sprachpaar prüfen oder MyMemory später erneut versuchen."
                ) from exc
            except requests.RequestException as exc:
                raise RuntimeError(f"MyMemory-Verbindungsfehler: {exc}") from exc
            except ValueError as exc:
                raise RuntimeError("MyMemory hat keine gültige JSON-Antwort geliefert.") from exc

            if not isinstance(data, dict):
                raise RuntimeError("MyMemory hat eine unerwartete Antwort geliefert.")
            status = data.get("responseStatus")
            if status not in (200, "200"):
                detail = data.get("responseDetails") or f"MyMemory-Fehler (Status {status})."
                raise RuntimeError(str(detail))
            if data.get("quotaFinished"):
                raise RuntimeError(
                    "Das tägliche kostenlose MyMemory-Kontingent ist aufgebraucht. "
                    "Bitte später erneut versuchen oder Eingabe und Sprachpaar prüfen oder MyMemory später erneut versuchen."
                )

            response_data = data.get("responseData")
            translated = (
                response_data.get("translatedText")
                if isinstance(response_data, dict) else None
            )
            if not isinstance(translated, str) or not translated.strip():
                raise RuntimeError("MyMemory hat keinen gültigen Übersetzungstext geliefert.")
            translated = translated.strip()

            normalize = lambda value: " ".join(value.casefold().split())
            if normalize(translated) == normalize(chunk):
                raise RuntimeError(
                    "MyMemory hat den Originaltext unverändert zurückgegeben. "
                    "Für dieses Sprachpaar ist gerade keine Übersetzung verfügbar. "
                    "Bitte Google Übersetzer auswählen."
                )
            if self._looks_wrong_target_language(translated, source, target):
                raise RuntimeError(
                    "MyMemory hat den Text offenbar nicht in die gewünschte Zielsprache "
                    "übersetzt. Die Antwort wurde verworfen; bitte MyMemory später erneut versuchen."
                )
            if self._looks_unrelated(chunk, translated):
                match = response_data.get("match", 0) if isinstance(response_data, dict) else 0
                raise RuntimeError(
                    "MyMemory hat eine offensichtlich unpassende Übersetzungs-Erinnerung "
                    f"zurückgegeben (Trefferwert: {match}). Das ist ein Fehler des "
                    "MyMemory-Dienstes, kein Übersetzungsergebnis. Bitte Eingabe und Sprachpaar prüfen oder MyMemory später erneut versuchen."
                )
            results.append(translated)

        return "\n".join(results)
