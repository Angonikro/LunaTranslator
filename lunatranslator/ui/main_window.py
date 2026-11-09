from PySide6.QtCore import Qt, QObject, Signal, QRunnable, QThreadPool
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QComboBox, QPlainTextEdit, QStackedWidget, QListWidget,
    QListWidgetItem, QMessageBox, QLineEdit, QDialog, QFormLayout, QDialogButtonBox,
    QSplitter, QFrame, QProgressBar, QMenu
)
from lunatranslator.core.config import load_settings, save_settings
from lunatranslator.core.history import History
from lunatranslator.engines.online import GoogleTranslateEngine, MyMemoryEngine
from lunatranslator.speech.mbrola import MbrolaSpeech, discover_mbrola_voices, installed_voice_options, voice_label, audio_backends, audio_devices, audio_input_devices
from lunatranslator.speech.input import SpeechInput, microphone_devices
from version import VERSION

STYLE = """
QMainWindow, QWidget { background: #252a32; color: #e7eaf0; font-family: 'Noto Sans'; font-size: 10pt; }
QFrame#sidebar { background: #1d2229; border: 0; }
QPushButton { background: #343c49; border: 1px solid #465163; border-radius: 7px; padding: 9px 13px; color: #edf0f7; }
QPushButton:hover { background: #46536b; }
QPushButton:pressed { background: #526de5; }
QPushButton#primary { background: #526de5; border: 0; font-weight: bold; }
QLineEdit, QPlainTextEdit, QComboBox, QListWidget { background: #1c222a; border: 1px solid #414b5a; border-radius: 7px; padding: 8px; selection-background-color: #526de5; }
QComboBox QAbstractItemView { background: #1c222a; selection-background-color: #526de5; }
QLabel#muted { color: #a5afbf; }
QProgressBar { border: 1px solid #414b5a; border-radius: 5px; text-align: center; }
QProgressBar::chunk { background: #526de5; border-radius: 4px; }
"""


class GermanContextMenuMixin:
    """Provides an explicitly localized German editing context menu."""

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(STYLE)
        actions = [
            ("Rückgängig", "undo"),
            ("Wiederholen", "redo"),
            (None, None),
            ("Ausschneiden", "cut"),
            ("Kopieren", "copy"),
            ("Einfügen", "paste"),
            ("Löschen", "delete"),
            (None, None),
            ("Alles auswählen", "selectAll"),
        ]
        for label, method in actions:
            if label is None:
                menu.addSeparator()
                continue
            action = menu.addAction(label)
            callback = getattr(self, method, None)
            if method == "delete":
                callback = self.delete_selected_text
            action.triggered.connect(callback if callable(callback) else (lambda: None))
            if method in ("cut", "copy", "delete"):
                selected = self.hasSelectedText() if hasattr(self, "hasSelectedText") else bool(self.textCursor().hasSelection())
                action.setEnabled(selected and not getattr(self, "isReadOnly", lambda: False)())
            if method == "paste":
                action.setEnabled(not getattr(self, "isReadOnly", lambda: False)())
            if method in ("undo", "redo") and hasattr(self, "isUndoAvailable"):
                action.setEnabled(self.isUndoAvailable() if method == "undo" else self.isRedoAvailable())
        menu.exec(event.globalPos())


class GermanPlainTextEdit(GermanContextMenuMixin, QPlainTextEdit):
    def delete_selected_text(self):
        cursor = self.textCursor()
        cursor.removeSelectedText()
        self.setTextCursor(cursor)


class GermanLineEdit(GermanContextMenuMixin, QLineEdit):
    def hasSelectedText(self):
        return bool(super().selectedText())

    def delete_selected_text(self):
        self.insert("")


class WorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(str)
    completed = Signal()

class Worker(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = self.fn()
        except Exception as exc:
            self.signals.error.emit(str(exc))
        else:
            self.signals.finished.emit(result)
        finally:
            self.signals.completed.emit()


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Einstellungen")
        self.settings = dict(settings)
        self.mbrola_voices = discover_mbrola_voices()
        form = QFormLayout(self)
        self.provider = QComboBox()
        self.provider.addItems(["Google Übersetzer", "MyMemory"])
        selected_provider = settings.get("provider", "Google Übersetzer")
        if selected_provider not in [self.provider.itemText(i) for i in range(self.provider.count())]:
            selected_provider = "Google Übersetzer"
        self.provider.setCurrentText(selected_provider)
        self.email = GermanLineEdit(settings.get("mymemory_email", ""))
        self.email.setPlaceholderText("Optional – erhöht das Tageslimit")
        form.addRow("Übersetzungsdienst", self.provider)
        form.addRow("MyMemory Kontakt-E-Mail (optional)", self.email)

        self.mbrola_voice = QComboBox()
        self.mbrola_voice.addItem("Automatisch passend zur Zielsprache", "auto")
        installed_ids = set()
        for voice in self.mbrola_voices:
            if voice["installed"]:
                self.mbrola_voice.addItem(voice_label(voice), voice["id"])
                installed_ids.add(voice["id"])
        selected_voice = settings.get("mbrola_voice", "auto")
        if selected_voice not in installed_ids and selected_voice != "auto":
            selected_voice = "auto"
        self.mbrola_voice.setCurrentIndex(max(0, self.mbrola_voice.findData(selected_voice)))
        form.addRow("MBROLA-Modul", self.mbrola_voice)

        self.audio_backend = QComboBox()
        for backend_id, backend_label in audio_backends():
            self.audio_backend.addItem(backend_label, backend_id)
        saved_backend = settings.get("audio_backend", "auto")
        backend_index = self.audio_backend.findData(saved_backend)
        self.audio_backend.setCurrentIndex(max(0, backend_index))
        self.audio_device = QComboBox()
        self._refresh_audio_devices()
        self.audio_backend.currentIndexChanged.connect(self._refresh_audio_devices)
        form.addRow("Audiotreiber", self.audio_backend)
        form.addRow("Soundkarte / Ausgabe", self.audio_device)

        self.microphone_device = QComboBox()
        self._refresh_microphone_devices()
        form.addRow("Mikrofon / Eingabe", self.microphone_device)
        mic_note = QLabel("Spracheingabe nutzt SpeechRecognition und PyAudio; die Erkennung erfolgt online über Google.")
        mic_note.setWordWrap(True)
        mic_note.setObjectName("muted")
        form.addRow(mic_note)

        self.voice_info = QLabel()
        self.voice_info.setWordWrap(True)
        self.voice_info.setObjectName("muted")
        if not self.mbrola_voices:
            info = (
                "Keine MBROLA-Stimmen erkannt. Installiere eSpeak NG und MBROLA-Stimmen. "
                "Die automatische Sprachausgabe kann ersatzweise die native eSpeak-NG-Stimme verwenden."
            )
        else:
            installed = [v for v in self.mbrola_voices if v["installed"]]
            missing = [v for v in self.mbrola_voices if not v["installed"]]
            languages = sorted({v["language_name"] for v in self.mbrola_voices})
            info = (
                f"Erkannte MBROLA-Sprachen: {', '.join(languages)}. "
                f"{len(installed)} Modul(e) installiert, {len(missing)} Modul(e) ohne MBROLA-Daten."
            )
            if missing:
                info += " Nicht installierte Module werden nicht zur Auswahl angeboten."
        self.voice_info.setText(info)
        form.addRow("Sprachmodule", self.voice_info)

        refresh = QPushButton("MBROLA-Module neu erkennen")
        refresh.clicked.connect(self.refresh_mbrola)
        form.addRow(refresh)
        note = QLabel("Automatik wählt eine Stimme passend zur Zielsprache. Ist keine passende MBROLA-Stimme installiert, wird eSpeak NG mit einer nativen Stimme dieser Sprache verwendet. Ein manuell gewähltes Modul überschreibt die Automatik.")
        note.setWordWrap(True)
        note.setObjectName("muted")
        form.addRow(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        # Qt-Standardtexte explizit auf Deutsch setzen; nicht von der
        # installierten Qt-/System-Lokalisierung abhängig machen.
        buttons.button(QDialogButtonBox.Save).setText("Speichern")
        buttons.button(QDialogButtonBox.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _refresh_audio_devices(self):
        backend = self.audio_backend.currentData() or "auto"
        previous = self.audio_device.currentData() if self.audio_device.count() else self.settings.get("audio_device", "")
        self.audio_device.clear()
        for device_id, label in audio_devices(backend):
            self.audio_device.addItem(label, device_id)
        index = self.audio_device.findData(previous)
        self.audio_device.setCurrentIndex(max(0, index))

    def _refresh_microphone_devices(self):
        previous = (self.microphone_device.currentData() if self.microphone_device.count()
                    else self.settings.get("microphone_device", ""))
        self.microphone_device.clear()
        for device_id, label in microphone_devices():
            self.microphone_device.addItem(label, device_id)
        index = self.microphone_device.findData(previous)
        self.microphone_device.setCurrentIndex(max(0, index))

    def refresh_mbrola(self):
        current = self.mbrola_voice.currentData() or "auto"
        self.mbrola_voices = discover_mbrola_voices()
        self.mbrola_voice.clear()
        self.mbrola_voice.addItem("Automatisch passend zur Zielsprache", "auto")
        for voice in self.mbrola_voices:
            if voice["installed"]:
                self.mbrola_voice.addItem(voice_label(voice), voice["id"])
        index = self.mbrola_voice.findData(current)
        self.mbrola_voice.setCurrentIndex(max(0, index))
        installed = [v for v in self.mbrola_voices if v["installed"]]
        languages = sorted({v["language_name"] for v in self.mbrola_voices})
        self.voice_info.setText(
            f"Erkannte MBROLA-Sprachen: {', '.join(languages) or 'keine'}. "
            f"{len(installed)} Modul(e) installiert."
        )

    def values(self):
        self.settings.update({
            "provider": self.provider.currentText(),
            "mymemory_email": self.email.text().strip(),
            "mbrola_voice": self.mbrola_voice.currentData() or "auto",
            "audio_backend": self.audio_backend.currentData() or "auto",
            "audio_device": self.audio_device.currentData() or "",
            "microphone_device": self.microphone_device.currentData() or "",
        })
        for key in ("deepl_api_key", "libretranslate_api_key", "libretranslate_url"):
            self.settings.pop(key, None)
        return self.settings


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.history = History()
        self.pool = QThreadPool.globalInstance()
        # Keep Python wrappers alive while QRunnable instances execute.
        self._active_workers = set()
        self.speech = MbrolaSpeech()
        self.speech_input = SpeechInput()
        self.recording = False
        self.setWindowTitle(f"LunaTranslator {VERSION}")
        self.resize(1120, 720)
        self.setMinimumSize(820, 560)
        self.setStyleSheet(STYLE)
        self._build_ui()
        self._build_menu()
        # Keep the last selected language pair across restarts, even if the
        # application is closed without performing a translation.
        self.source_lang.currentTextChanged.connect(self.save_language_selection)
        self.target_lang.currentTextChanged.connect(self.save_language_selection)

    def _build_ui(self):
        root = QWidget()
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(205)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(15, 20, 15, 15)
        brand = QLabel("◈  LunaTranslator")
        brand.setStyleSheet("font-size: 13pt; font-weight: 700; color: #ffffff; padding: 8px 2px 20px;")
        brand.setToolTip("LunaTranslator")
        side.addWidget(brand)
        self.nav_translate = QPushButton("  Übersetzen")
        self.nav_history = QPushButton("  Verlauf")
        self.nav_settings = QPushButton("  Einstellungen")
        for button in (self.nav_translate, self.nav_history, self.nav_settings):
            button.setCursor(Qt.PointingHandCursor)
            side.addWidget(button)
        side.addStretch(1)
        side.addWidget(QLabel("Goldisoft · 2026"))
        outer.addWidget(sidebar)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._translation_page())
        self.pages.addWidget(self._history_page())
        self.nav_translate.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        self.nav_history.clicked.connect(self.refresh_history)
        self.nav_history.clicked.connect(lambda: self.pages.setCurrentIndex(1))
        self.nav_settings.clicked.connect(self.open_settings)
        outer.addWidget(self.pages, 1)
        self.setCentralWidget(root)

    def _build_menu(self):
        settings_menu = self.menuBar().addMenu("Datei")
        quit_action = QAction("Beenden", self)
        quit_action.triggered.connect(self.close)
        settings_menu.addAction(quit_action)
        menu = self.menuBar().addMenu("Einstellungen")
        action = QAction("Einstellungen öffnen", self)
        action.triggered.connect(self.open_settings)
        menu.addAction(action)

    def _translation_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 25, 28, 25)
        title = QLabel("Textübersetzung")
        title.setStyleSheet("font-size: 21pt; font-weight: 700;")
        subtitle = QLabel("Google und MyMemory für Online-Übersetzung sowie MBROLA-Sprachausgabe.")
        subtitle.setObjectName("muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        bar = QHBoxLayout()
        self.source_lang = QComboBox()
        self.source_lang.addItems(["auto", "de", "en", "fr", "it", "nl", "es", "pt", "pl", "ru", "ja", "zh"])
        self.source_lang.setCurrentText(self.settings.get("source_language", "auto"))
        self.target_lang = QComboBox()
        self.target_lang.addItems(["en", "de", "fr", "it", "nl", "es", "pt", "pl", "ru", "ja", "zh"])
        self.target_lang.setCurrentText(self.settings.get("target_language", "en"))
        swap = QPushButton("⇄")
        swap.setFixedWidth(48)
        swap.clicked.connect(self.swap_languages)
        bar.addWidget(QLabel("Von"))
        bar.addWidget(self.source_lang)
        bar.addWidget(swap)
        bar.addWidget(QLabel("Nach"))
        bar.addWidget(self.target_lang)
        bar.addStretch(1)
        self.provider_label = QLabel(self.settings.get("provider", "Google Übersetzer"))
        self.provider_label.setObjectName("muted")
        bar.addWidget(self.provider_label)
        layout.addLayout(bar)

        splitter = QSplitter(Qt.Horizontal)
        self.input_text = GermanPlainTextEdit()
        self.input_text.setPlaceholderText("Text zum Übersetzen eingeben …")
        self.output_text = GermanPlainTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("Die Übersetzung erscheint hier …")
        splitter.addWidget(self._panel("QUELLTEXT", self.input_text))
        splitter.addWidget(self._panel("ÜBERSETZUNG", self.output_text))
        layout.addWidget(splitter, 1)

        self.speech_voice = QComboBox()
        self._populate_speech_voices()
        saved_voice = self.settings.get("mbrola_voice", "auto")
        voice_index = self.speech_voice.findData(saved_voice)
        self.speech_voice.setCurrentIndex(max(0, voice_index))
        self.speech_voice.currentIndexChanged.connect(self.save_speech_voice)
        self.speak_button = QPushButton("Vorlesen")
        self.speak_button.clicked.connect(self.speak_translation)
        self.stop_speech_button = QPushButton("Stopp")
        self.stop_speech_button.clicked.connect(self.stop_speech)
        self.speech_module_label = QLabel("Verwendetes Modul: wird bei Vorlesen angezeigt")
        self.speech_module_label.setObjectName("muted")
        speech_row = QHBoxLayout()
        speech_row.addWidget(QLabel("MBROLA-Stimme"))
        speech_row.addWidget(self.speech_voice)
        speech_row.addWidget(self.speak_button)
        speech_row.addWidget(self.stop_speech_button)
        speech_row.addStretch(1)
        layout.addLayout(speech_row)
        layout.addWidget(self.speech_module_label)

        input_row = QHBoxLayout()
        self.record_button = QPushButton("🎙 Spracheingabe starten")
        self.record_button.setObjectName("primary")
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_status = QLabel("Mikrofon bereit · Online-Spracherkennung")
        self.record_status.setObjectName("muted")
        input_row.addWidget(self.record_button)
        input_row.addWidget(self.record_status, 1)
        layout.addLayout(input_row)

        actions = QHBoxLayout()
        self.status = QLabel("Bereit")
        self.status.setObjectName("muted")
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        translate = QPushButton("Übersetzen")
        translate.setObjectName("primary")
        translate.clicked.connect(self.translate)
        copy = QPushButton("Ergebnis kopieren")
        copy.clicked.connect(lambda: QApplication.clipboard().setText(self.output_text.toPlainText()))
        clear = QPushButton("Leeren")
        clear.clicked.connect(self.clear_text)
        actions.addWidget(self.status)
        actions.addWidget(self.progress)
        actions.addStretch(1)
        actions.addWidget(clear)
        actions.addWidget(copy)
        actions.addWidget(translate)
        layout.addLayout(actions)
        return page

    def _panel(self, heading, editor):
        panel = QWidget()
        box = QVBoxLayout(panel)
        label = QLabel(heading)
        label.setObjectName("muted")
        box.addWidget(label)
        box.addWidget(editor, 1)
        return panel

    def _history_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 25, 28, 25)
        title = QLabel("Übersetzungsverlauf")
        title.setStyleSheet("font-size: 21pt; font-weight: 700;")
        self.history_search = GermanLineEdit()
        self.history_search.setPlaceholderText("Verlauf durchsuchen …")
        self.history_search.textChanged.connect(self.refresh_history)
        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self.restore_history_item)
        clear = QPushButton("Verlauf löschen")
        clear.clicked.connect(self.clear_history)
        layout.addWidget(title)
        layout.addWidget(self.history_search)
        layout.addWidget(self.history_list, 1)
        layout.addWidget(clear, 0, Qt.AlignRight)
        return page

    def _populate_speech_voices(self):
        self.speech_voice.clear()
        self.speech_voice.addItem("Automatisch nach Zielsprache", "auto")
        for voice in installed_voice_options():
            self.speech_voice.addItem(voice_label(voice), voice["id"])

    def save_speech_voice(self, *_args):
        if not hasattr(self, "speech_voice"):
            return
        self.settings["mbrola_voice"] = self.speech_voice.currentData() or "auto"
        try:
            save_settings(self.settings)
        except OSError as exc:
            self.statusBar().showMessage(f"MBROLA-Einstellung konnte nicht gespeichert werden: {exc}", 6000)

    def speak_translation(self):
        text = self.output_text.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Vorlesen", "Bitte zuerst einen Text übersetzen.")
            return
        language = self.target_lang.currentText()
        voice = self.speech_voice.currentData() or "auto"
        self.speak_button.setEnabled(False)
        self.status.setText("Sprachausgabe läuft …")
        backend = self.settings.get("audio_backend", "auto")
        device = self.settings.get("audio_device", "")
        self.speech_module_label.setText("Verwendetes Modul: wird ermittelt …")
        worker = Worker(lambda: self.speech.speak(text, language, voice, backend=backend, device=device))
        self._active_workers.add(worker)
        worker.signals.finished.connect(self._speech_done)
        worker.signals.error.connect(self._speech_error)
        worker.signals.completed.connect(lambda w=worker: self._release_worker(w))
        self.pool.start(worker)

    def _speech_done(self, module_info):
        self.speak_button.setEnabled(True)
        self.speech_module_label.setText(f"Verwendetes Modul: {module_info}")
        self.status.setText("Vorlesen abgeschlossen")

    def _speech_error(self, message):
        self.speak_button.setEnabled(True)
        self.status.setText("Sprachausgabe nicht verfügbar")
        QMessageBox.warning(self, "MBROLA – Vorlesefehler", message)

    def stop_speech(self):
        self.speech.stop()
        self.speak_button.setEnabled(True)
        self.status.setText("Sprachausgabe gestoppt")

    def toggle_recording(self):
        if not self.recording:
            device = self.settings.get("microphone_device", "")
            try:
                message = self.speech_input.start(device=device)
            except Exception as exc:
                QMessageBox.warning(self, "Spracheingabe", str(exc))
                return
            self.recording = True
            self.record_button.setText("■ Aufnahme stoppen")
            self.record_status.setText(message)
            self.status.setText("Mikrofonaufnahme läuft …")
            return

        self.record_button.setEnabled(False)
        self.record_status.setText("Aufnahme wird verarbeitet …")
        try:
            audio_data = self.speech_input.stop()
        except Exception as exc:
            self.recording = False
            self.record_button.setEnabled(True)
            self.record_button.setText("🎙 Spracheingabe starten")
            QMessageBox.warning(self, "Spracheingabe", str(exc))
            return
        self.recording = False
        self.record_button.setText("🎙 Spracheingabe starten")
        language = self.settings.get("source_language", "auto")
        worker = Worker(lambda: SpeechInput.transcribe(audio_data, language=language))
        self._active_workers.add(worker)
        worker.signals.finished.connect(self._speech_input_done)
        worker.signals.error.connect(self._speech_input_error)
        worker.signals.completed.connect(lambda w=worker: self._release_worker(w))
        self.pool.start(worker)

    def _speech_input_done(self, recognized_text):
        self.record_button.setEnabled(True)
        self.input_text.setPlainText(recognized_text)
        self.input_text.setFocus()
        self.record_status.setText("Sprache erkannt · Text ins Quelltextfeld übernommen")
        self.status.setText("Spracheingabe abgeschlossen")

    def _speech_input_error(self, message):
        self.record_button.setEnabled(True)
        self.record_status.setText("Spracheingabe fehlgeschlagen")
        self.status.setText("Spracherkennung fehlgeschlagen")
        QMessageBox.warning(self, "Spracheingabe", message)

    def save_language_selection(self, *_args):
        if not hasattr(self, "source_lang") or not hasattr(self, "target_lang"):
            return
        self.settings["source_language"] = self.source_lang.currentText()
        self.settings["target_language"] = self.target_lang.currentText()
        try:
            save_settings(self.settings)
        except OSError as exc:
            self.statusBar().showMessage(f"Spracheinstellungen konnten nicht gespeichert werden: {exc}", 6000)

    def swap_languages(self):
        src, dst = self.source_lang.currentText(), self.target_lang.currentText()
        if src != "auto":
            self.source_lang.setCurrentText(dst)
            self.target_lang.setCurrentText(src)
            self.save_language_selection()

    def _release_worker(self, worker):
        self._active_workers.discard(worker)

    def clear_text(self):
        self.input_text.clear()
        self.output_text.clear()

    def _engine(self):
        provider = self.settings.get("provider", "Google Übersetzer")
        if provider == "MyMemory":
            return MyMemoryEngine(self.settings.get("mymemory_email", ""))
        return GoogleTranslateEngine()

    def translate(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "LunaTranslator", "Bitte zuerst einen Text eingeben.")
            return
        source, target = self.source_lang.currentText(), self.target_lang.currentText()
        engine = self._engine()
        # Jede neue Anfrage beginnt mit einem leeren Ergebnisfeld. So bleibt
        # bei einem Fehler niemals die Übersetzung des vorherigen Auftrags stehen.
        self.output_text.clear()
        self.status.setText("Übersetzung läuft …")
        self.progress.show()
        def translate_with_fallback():
            # Anbieterwahl ist verbindlich: Bei Auswahl von MyMemory darf
            # niemals stillschweigend Google als Ersatzdienst einspringen.
            # Fehler werden an _translation_error weitergereicht.
            return engine.translate(text, source, target), engine.name, ""

        worker = Worker(translate_with_fallback)
        self._active_workers.add(worker)
        worker.signals.finished.connect(
            lambda payload: self._translation_done(
                payload[0], text, source, target, payload[1], payload[2]
            )
        )
        worker.signals.error.connect(self._translation_error)
        worker.signals.completed.connect(lambda w=worker: self._release_worker(w))
        self.pool.start(worker)

    def _translation_done(self, result, source_text, source, target, provider, notice=""):
        self.progress.hide()
        self.output_text.setPlainText(result)
        self.status.setText(notice or "Übersetzung abgeschlossen")
        try:
            self.history.add(source, target, source_text, result, provider)
        except Exception as exc:
            self.status.setText(f"Übersetzt; Verlauf konnte nicht gespeichert werden: {exc}")

    def _translation_error(self, message):
        self.progress.hide()
        # Fehlerzustand explizit anzeigen und keine alte Ausgabe stehen lassen.
        self.output_text.clear()
        self.status.setText("Übersetzung fehlgeschlagen")
        QMessageBox.warning(self, "Übersetzungsfehler", message)

    def refresh_history(self):
        if not hasattr(self, "history_list"):
            return
        term = self.history_search.text().strip()
        rows = self.history.search(term) if term else self.history.recent()
        self.history_list.clear()
        for created, source, target, original, translated, provider in rows:
            item = QListWidgetItem(f"{created[:19].replace('T', ' ')}  ·  {source} → {target}  ·  {provider}\n{original[:110]}  →  {translated[:110]}")
            item.setData(Qt.UserRole, (original, translated, source, target))
            self.history_list.addItem(item)

    def restore_history_item(self, item):
        original, translated, source, target = item.data(Qt.UserRole)
        self.input_text.setPlainText(original)
        self.output_text.setPlainText(translated)
        self.source_lang.setCurrentText(source if source in [self.source_lang.itemText(i) for i in range(self.source_lang.count())] else "auto")
        self.target_lang.setCurrentText(target)

    def clear_history(self):
        answer = QMessageBox.question(self, "Verlauf löschen", "Möchtest du den gesamten Übersetzungsverlauf löschen?")
        if answer == QMessageBox.Yes:
            self.history.clear()
            self.refresh_history()

    def open_settings(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            self.settings = dialog.values()
            save_settings(self.settings)
            self.provider_label.setText(self.settings.get("provider", "Google Übersetzer"))
            self._populate_speech_voices()
            index = self.speech_voice.findData(self.settings.get("mbrola_voice", "auto"))
            self.speech_voice.setCurrentIndex(max(0, index))
            self.statusBar().showMessage("Einstellungen gespeichert", 4000)
