# Changelog

## 0.2.18
- Zweisprachige Benutzeroberfläche auf Deutsch und Englisch ergänzt.
- Sprachumschaltung über das Menü „Sprache / Language“; Auswahl wird in den Einstellungen gespeichert.
- Beschriftungen, Navigation, Übersetzungsansicht, Verlauf, Einstellungen und Bearbeitungskontextmenüs werden entsprechend der UI-Sprache angezeigt.
- Die gewählte UI-Sprache ist unabhängig von Quell- und Zielsprache der Übersetzung.

## 0.2.17
- Überschrift „LunaTranslator“ in der Seitenleiste verkleinert, damit der vollständige Programmname auch bei der festen Seitenleistenbreite sichtbar bleibt.
- Schaltflächen im Einstellungsdialog fest auf Deutsch gesetzt: „Speichern“ und „Abbrechen“.
- Änderungsprotokoll vollständig ins Deutsche übertragen; technische Bezeichnungen und Programmnamen bleiben unverändert.

## 0.2.16
- MyMemory-Diagnoseprotokollierung vollständig entfernt. Es werden keine Anfragedaten, Texte, Antworten oder Fehler in einer Diagnose-Logdatei gespeichert.
- README vollständig auf Deutsch überarbeitet.
- Installations- und Startanleitung ohne virtuelle Umgebung als Standard dokumentiert; venv nur noch als optionale Alternative.

## 0.2.15
- Ergebnisfeld wird zu Beginn jedes Übersetzungsauftrags geleert, damit bei Fehlern keine alte Übersetzung sichtbar bleibt.
- MyMemory-API-Diagnose wird lokal unter `~/.cache/LunaTranslator/mymemory-diagnostic.log` protokolliert (Zeitpunkt, Anfrageparameter, HTTP-Status und API-Antwort; Kontakt-E-Mail wird maskiert).
- Bei ausgewähltem MyMemory-Dienst wird Google nicht verwendet.

## 0.2.14
- Automatischen Wechsel zu Google Übersetzer bei ausgewähltem MyMemory-Dienst entfernt.
- Die Dienstauswahl wird strikt beachtet; MyMemory-Fehler werden angezeigt, statt unbemerkt zu einem anderen Dienst zu wechseln.
- MyMemory-Fehlermeldungen angepasst, damit sie keinen automatischen Wechsel zu Google mehr ankündigen.

## 0.2.13
- Automatische Google-Ausweichübersetzung nach ungültigen MyMemory-Antworten zentralisiert. (In 0.2.14 wieder entfernt.)

## 0.2.12
- Vorsichtige Prüfung der Zielsprache bei MyMemory-Ergebnissen für häufige Sprachen ergänzt.
- Ergebnisse in der Quellsprache werden erkannt und automatisch erneut über Google Übersetzer angefragt. (Das automatische Ausweichen wurde später wieder entfernt.)

## 0.2.11
- MyMemory-Antworten mit offensichtlichen Platzhaltern wie `xxxxx`, `###` oder fehlerhaften Satzzeichenfolgen werden als ungültig verworfen.
- Beim damaligen automatischen Google-Ausweichversuch nach einer fehlerhaften MyMemory-Antwort wird die Quellsprache mit `auto` neu erkannt.

## 0.2.10
- Höhe des Anwendungsfensters reduziert.

## 0.2.9
- Fehlerhafte MyMemory-Antworten und unpassende Treffer aus dem unscharfen Übersetzungsspeicher werden nicht mehr als gültige Übersetzung angezeigt.
- Bei einer unbrauchbaren MyMemory-Antwort wurde Google Übersetzer zunächst als Online-Ausweichdienst verwendet; dieses Verhalten wurde später entfernt.
- Statusanzeige und Verlauf kennzeichnen den tatsächlich verwendeten Dienst.

## 0.2.8
- Argos Translate und sämtliche Offline-Übersetzungs- sowie Modellverwaltungsfunktionen entfernt.
- Navigationseintrag für Sprachmodelle und Argos-Auswahl entfernt; Google Übersetzer und MyMemory bleiben als Online-Dienste verfügbar.
- Vorhandene Argos-Diensteinstellungen werden beim Start auf Google Übersetzer umgestellt.
- Paketinformationen, Desktop-Beschreibung und Dokumentation auf reine Online-Übersetzung angepasst.

## 0.2.7
- Verbliebenen `speech_recognition`-Namensfehler in `SpeechInput.stop()` behoben, indem das Modul direkt in der Methode importiert wird, die das zusammengeführte `AudioData`-Objekt erstellt.
- Bestehende Aufnahme über SpeechRecognition/PyAudio und Google-Online-Transkription beibehalten.

## 0.2.6
- Namensfehler bei der Spracheingabe behoben: Der fehleranfällige Alias `sr` wurde entfernt und SpeechRecognition wird in Aufnahme- und Transkriptionsmethoden ausdrücklich importiert.
- Mikrofonkalibrierung, Zusammenführung von Sprachabschnitten und Google-Online-Erkennung beibehalten.

## 0.2.5
- Aufnahme über einen eigenen Aufnahmethread statt über den Hintergrund-Listener umgesetzt.
- Umgebungsgeräusche des Mikrofons werden vor der Aufnahme kalibriert.
- Erzwungene Abtastrate von 16 kHz entfernt, damit PortAudio eine vom ausgewählten Gerät unterstützte Rate verwenden kann.
- Alle gesprochenen Abschnitte werden zusammengeführt, statt nur den letzten Abschnitt zu transkribieren.
- Erkennung tatsächlicher PortAudio-Eingabegeräte sowie verständlichere Mikrofon- und Fehlermeldungen verbessert.

## 0.2.4 – Debian-Trixie-Paketabhängigkeit korrigiert
- Nicht auflösbare Debian-Abhängigkeit `python3-speechrecognition` aus dem DEB entfernt, damit die Installation unter Trixie nicht daran scheitert.
- `python3-pyaudio` bleibt als offizielle Trixie-Abhängigkeit für die Mikrofonaufnahme erhalten.
- Dokumentation und Fehlermeldung angepasst: SpeechRecognition ist optional und wird nicht als APT-Paket vorausgesetzt.

## 0.2.3
- Mikrofonstart korrigiert: `listen_in_background` verwaltet den Kontext der Mikrofon-Audioquelle selbst, statt dass dieser zuvor manuell geöffnet wird.
- Konfliktbehaftete manuelle Bereinigung der Audioquelle entfernt; beim Beenden des Hintergrund-Listeners wird das Mikrofon freigegeben.

## 0.2.2 – Spracheingabe ohne Whisper
- Whisper-Aufnahme- und Transkriptionspfad vollständig entfernt.
- Spracheingabe auf SpeechRecognition und PyAudio umgestellt.
- Google Speech Recognition übernimmt die Online-Transkription; die Erkennungssprache folgt der ausgewählten Quellsprache.
- Mikrofonliste zeigt tatsächliche PortAudio-/PyAudio-Geräteindizes und speichert die Auswahl.
- Debian-Paketabhängigkeiten angepasst; Whisper-Modelloption und Installationsanleitung entfernt.

## 0.2.1 – Spracheingabe mit Whisper
- Mikrofonaufnahme mit Start-/Stopp-Schaltfläche auf der Übersetzungsseite ergänzt.
- Aufnahme abhängig vom ausgewählten Audiotreiber über PipeWire, PulseAudio/PipeWire-Pulse oder ALSA.
- Whisper-Kommandozeilenprogramm zur lokalen Transkription integriert; erkannter Text wird in das Quelltextfeld übernommen.
- Whisper-Modell (tiny, base, small) in den Einstellungen auswählbar und dauerhaft gespeichert.
- Whisper bleibt optional und wird nicht in das Debian-Paket eingebettet; Installationshinweise ergänzt.

## 0.2.0
- Auswahl des Mikrofon- bzw. Eingabegeräts in den Einstellungen ergänzt; PulseAudio-/PipeWire-Quellen und ALSA-Aufnahmegeräte werden erkannt.
- Ausgewähltes Mikrofon wird unabhängig vom Audioausgabegerät gespeichert.
- Für die Mikrofonliste wird derselbe Audiounterbau verwendet; Monitor- und Rückkopplungsquellen werden ausgeschlossen.

## 0.1.9
- Nach der Wiedergabe wird das tatsächlich verwendete Sprachsynthesemodul angezeigt: das ausgewählte bzw. automatisch passende MBROLA-Modul oder die native eSpeak-NG-Ersatzstimme.
- Audioausgabe in den Einstellungen um Auswahl zwischen automatischer Auswahl, PipeWire, PulseAudio/PipeWire-Pulse und ALSA erweitert; angezeigt werden nur installierte Wiedergabeprogramme.
- Auswahl des Ausgabegeräts für den jeweiligen Audiounterbau ergänzt; PulseAudio-/PipeWire-Ausgänge und, soweit verfügbar, ALSA-Geräte werden erkannt.
- Ausgewählter Audiounterbau und Ausgabegerät werden in den Benutzereinstellungen gespeichert.

## 0.1.8
- Audiowiedergabe korrigiert: eSpeak-NG-Ausgabe wird in eine temporäre WAV-Datei geschrieben und dem ausgewählten Wiedergabeprogramm als Dateiname übergeben; dies ist für `pw-play` erforderlich.
- `paplay` und `aplay` bleiben als Ersatz-Wiedergabeprogramme verfügbar; Validierung und Fehlermeldungen für erzeugte Audiodateien verbessert.

## 0.1.7
- Absturz beim Start der Übersetzungsseite behoben: MBROLA-Stimmenauswahl und Sprachschaltflächen werden vor dem Einfügen in das Layout initialisiert.

## 0.1.6
- Feste MBROLA-Stimmenliste durch Laufzeiterkennung über `espeak-ng --voices=mb` ersetzt.
- Erkennung installierter Diphon-Daten und Einstellungs-Auswahl für jedes erkannte, installierte MBROLA-Modul ergänzt.
- Automatische Zuordnung einer Stimme zur Zielsprache ergänzt; falls kein passendes MBROLA-Modul installiert ist, wird die native eSpeak-NG-Stimme dieser Sprache verwendet.
- Aktualisierungsaktion und Übersicht erkannter MBROLA-Sprachen und -Module in den Einstellungen ergänzt.
- Manuelle MBROLA-Modulauswahl in den Benutzereinstellungen und auf der Hauptseite beibehalten.

## 0.1.5
- MBROLA-Sprachausgabe für übersetzten Text ergänzt; eSpeak NG dient als Umwandlung in Phoneme.
- Automatische Stimmauswahl anhand der Zielsprache sowie auswählbare deutsche, englische, französische, italienische, niederländische und spanische MBROLA-Stimmen ergänzt.
- Schaltfläche zum Stoppen der Sprachausgabe ergänzt.
- Ausgewählte MBROLA-Stimme wird in den Benutzereinstellungen gespeichert.
- Optionale Installation der Debian-Sprachmodule dokumentiert; Sprachmodule und Stimmen-Datenbanken sind nicht im DEB enthalten.

## 0.1.4
- Maschinelle Übersetzung über MyMemory mit `mt=1` ausdrücklich für jede Anfrage aktiviert.
- Offensichtlich unpassende Treffer aus dem unscharfen Übersetzungsspeicher werden erkannt und verworfen.
- Aufgebrauchtes anonymes Kontingent wird als verständlicher Übersetzungsfehler gemeldet.

## 0.1.3
- Verarbeitung von MyMemory-Antworten und Netzwerkfehlern verbessert, damit fehlerhafte, zeitüberschrittene oder nicht verfügbare Antworten kontrolliert gemeldet werden.
- Absatzumbrüche bleiben beim Übersetzen längerer Texte in MyMemory-Abschnitten erhalten.
- Hintergrundaufgaben bleiben bis zum Abschluss gültig und werden danach sicher freigegeben.

## 0.1.2
- Ausgewählte Quell- und Zielsprachen werden bei jeder Änderung sofort gespeichert, auch nach dem Vertauschen der Sprachen.
- Öffentlicher Apertium-Dienst nach gemeldeten HTTP-400-Fehlern aus der Auswahlliste entfernt; vorhandene Apertium-Auswahl wird auf Google Übersetzer umgestellt.
- Nicht unterstütztes MyMemory-Anfragekennzeichen entfernt und unveränderte Quelltextantworten als Übersetzungsfehler statt als Erfolg erkannt.
- Diagnose für HTTP-400-Antworten des Apertium-Dienstes in älteren Konfigurationen verbessert.

## 0.1.1
- Fehlendes Modul `ArgosEngine` ergänzt, um einen Importfehler beim Start zu beheben.

## 0.1.0 – Erstveröffentlichung
- Grundgerüst der Qt-6-/PySide6-Anwendung erstellt.
- Übersetzungsoberfläche im Graphit-Stil ergänzt.
- Dienstschnittstelle für DeepL und LibreTranslate-kompatible Endpunkte eingerichtet.
- Argos Translate als optionalen Offline-Dienst ergänzt.
- Lokalen Übersetzungsverlauf auf Basis von SQLite ergänzt.
- Erkennung sowie Installation und Entfernung von Offline-Sprachpaketen ergänzt.
- Lokale Speicherung der Einstellungen ergänzt.
- Google-Übersetzer als Online-Dienst ergänzt und als Standard festgelegt.
- Unzuverlässigen vorausgefüllten öffentlichen LibreTranslate-Endpunkt durch eine leere, konfigurierbare Serveradresse und verständlichere HTTP-400-Fehlerdiagnose ersetzt.
- Deutsche Kontextmenüs für Übersetzungsfelder sowie Eingabe- und Suchfelder in den Einstellungen ergänzt.
- Eigenes LunaTranslator-SVG-Anwendungssymbol erstellt und im Debian-Desktopstarter registriert.
- Aktualisierung des Desktop- und Symbol-Caches nach der Paketinstallation ergänzt.
- DeepL und gehostetes LibreTranslate aus der Dienstauswahl entfernt, da sie Zugangsdaten oder API-Schlüssel benötigen.
- MyMemory als Online-Dienst ohne API-Schlüssel ergänzt; optionale Kontakt-E-Mail für ein höheres Tageskontingent vorgesehen.
- Apertium als Online-Dienst ohne API-Schlüssel ergänzt, abhängig von den verfügbaren Sprachpaaren des Servers.
- Google Übersetzer und lokales Argos Translate zunächst beibehalten; alte DeepL-/LibreTranslate-Einstellungen werden auf Google umgestellt.
- Sprachausgabe und Texterkennung (OCR) waren in dieser Erstveröffentlichung noch geplant und nicht umgesetzt.
