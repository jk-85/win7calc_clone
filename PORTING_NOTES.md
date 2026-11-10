# Portierungsnotizen – Linux und Windows, Version 1.3.0

## Gemeinsame Grundlage

Ausgangspunkt ist `classic-calc-windows-1.2.0-source.zip`; dieses enthielt bereits
die Linux-Unterstützung und die Änderungen aus der deutschen Version 1.1.0.
Der gemeinsame Anwendungscode `classiccalc/` ist in den neuen Linux- und
Windows-Quellpaketen bytegleich. Nur die Haupt-README priorisiert die jeweilige
Plattform; beide README-Varianten sind in beiden Paketen enthalten.

Geändert sind insbesondere `ui.py`, `widgets.py`, `i18n.py`, `__main__.py` und
`smoke.py`. Die Module für Rechenkern, Mathematik und Zusatzberechnungen bleiben
bytegleich zum Ausgangsprojekt:

| Datei | SHA-256 |
| :--- | :--- |
| `classiccalc/engine.py` | `1f2d95b308bacdb07cede257a5ea3801e353a296bb15f5a7a3a4f0a42944d2cb` |
| `classiccalc/mathlib.py` | `7011f8e5278ed6aba5cf26c7de2ed8d3a7ca6574aa577f9609ba5e99c69e4e02` |
| `classiccalc/tools.py` | `136dfd71beb9deba6c78331f256e7ca9790ca973280fdafcea78876387a480cc` |

Die Sprache ist ein Präsentationszustand (`de` oder `en`). Alle gespeicherten
numerischen Werte bleiben kanonisch; Hilfsbereichseingaben werden vor dem
Sprachwechsel mit der alten Sprache normalisiert. Beide Plattformen benutzen
identische Handler für Menü/Strg+H, Kontextmenüs und die hell gezeichneten
Pfeiltasten. Die gemeinsame Datei für Einstellungen bleibt Schema 2 mit einem
neuen optionalen `language`-Feld. Bestehende Profile ohne dieses Feld starten de.

## Nachweis und Abgrenzung

311 Tests und 350 numerische Prüfungen wurden unter Debian x64/Tk/Xvfb ausgeführt.
Die Windows-Buildskripte und das Manifest wurden aktualisiert und geprüft, aber
nicht auf Windows ausgeführt. Das Windows-EXE-Buildwerkzeug führt die vollständige
Suite sowie den erweiterten Paket-Selbsttest nach dem Bauen aus. Native Windows-
Popupdarstellung, reales Windows-DPI und Windows-10-Laufzeit bleiben manuell zu prüfen.

## Windows-Anbindung

`platform_support.py` kapselt AppData-Pfad, Anwendungskennung, DPI und
plattformgerechte Fehlermeldungen. Windows-Aufrufe erfolgen ausschließlich über
ctypes nach `sys.platform == 'win32'`; Linux importiert keine Windows-DLLs.
Dateipfade werden durchgehend als Unicode/Path behandelt. Einstellungen werden
weiter mit dem vorhandenen Schema 2 atomar durch eine temporäre Datei ersetzt.

Die DPI-Anpassung ist systembezogen. Die Windows-EXE erhält ein Manifest mit
`dpiAwareness=system`, Windows-10-Kompatibilitätskennung und
`requestedExecutionLevel=asInvoker`. Beim Quellenstart wird die DPI-Awareness
vor `Tk()` gesetzt. Es gibt Fallbacks für ältere APIs. Explizites `--scale`
überschreibt die automatische Startgröße. Es wird kein WM_DPICHANGED-Handler und
keine dynamische Per-Monitor-V2-Unterstützung behauptet.

`launcher.py` stellt bei `pythonw` bzw. PyInstaller `--noconsole` fehlende
Standardausgabeströme bereit. Diagnosen gehen in das lokale `error.log`; kann es
nicht geöffnet werden, bleibt der Start möglich. Bei Startfehlern erscheint
unter Windows ein nativer Fehlerdialog. Der Rechner selbst greift nicht auf das
Netzwerk zu. Nur das vom Benutzer gestartete Buildwerkzeug installiert
Entwicklungsabhängigkeiten.

`Start.cmd` verwendet eine lokale Build-Umgebung, falls vorhanden, sonst den
Python Launcher (zunächst 3.13, dann die Standardversion) oder `python` im PATH.
Die Konsole wird nur für den Start benötigt. `Start-Konsole.cmd` bleibt für
Diagnose und CLI-Ausgabe verfügbar. Alle Batch-Dateien sind ASCII mit CRLF.
Der Python-Starter verwendet `subprocess.Popen` mit einer Argumentliste, ohne
Shell-Zusammenbau der Programmpfade.

## Build und Pakete

`tools/build_windows.py` verweigert einen Windows-EXE-Build auf einem anderen
Betriebssystem sowie mit einem 32-Bit-Interpreter. Es verwendet eine separate
`.venv-build`, den in `requirements-build.txt` festgelegten PyInstaller und das
projektspezifische Icon. Die Version-Ressource wird aus `__version__` erzeugt.
Der Build prüft zuerst die Suite und anschließend die fertige EXE. Erst nach
erfolgreicher EXE-Prüfung wird ein portables ZIP mit SHA-256-Datei erzeugt.
Der Standard ist `onedir`; `--onefile` ist optional. Das gesamte `onedir`-Paket
muss gemeinsam verteilt werden. Die EXE wird nicht signiert.

Das Windows-Buildskript wurde hier syntaktisch und in einzelnen Hilfsfunktionen
geprüft, aber **nicht auf Windows ausgeführt**. Ein fertiger Windows-Build ist
nicht enthalten. Die `.pyzw` enthält den identischen Python-Anwendungscode,
jedoch keinen Python-/Tcl-/Tk-Interpreter; sie ist daher kein Ersatz für ein
selbstständiges EXE-Paket.

## Tests und ihre Grenzen

Die bestehenden GUI-Tests prüfen unter Windows nun nicht mehr auf die
Linux-Umgebungsvariable DISPLAY; auf einem Windows-Desktop werden sie ausgeführt.
UTF-8-Dateizugriffe sind explizit. Die POSIX-Dateirechte-Prüfung gilt nur auf
POSIX, nicht als unbelegte NTFS-ACL-Aussage.

Bei den Popup-Ereignistests wird nur unter Windows `Menu.tk_popup`
ersetzt: Windows verwendet eine modale native Menüschleife. Dadurch wartet ein
unbeaufsichtigter Test nicht auf einen Benutzerklick. Tk-Maus-/Tastaturereignisse,
Auswahl, Menüaufbau und Befehlsausführung bleiben echte GUI-Operationen. Unter
Linux werden die Popups tatsächlich geöffnet und ihre Sichtbarkeit geprüft.
Ein grüner Test auf Windows würde deshalb nicht allein die native Darstellung
oder Bedienung des geöffneten Windows-Popups beweisen.

Win32-API-Aufrufe und AppData-Zweige wurden auf dem vorhandenen Linux-Host mit
Testdoubles geprüft. Das ersetzt weder einen realen Windows-DPI-Test noch die
Prüfung eines physischen deutschen Tastaturlayouts. Details und tatsächlich
beobachtete Resultate stehen in `TEST_REPORT.md`.

## Vor Veröffentlichung auf Windows 10 manuell prüfen

Auf dem vorgesehenen Windows-10-x64-System einen Build ausführen und das ganze
portable Paket auf einem Rechner ohne separate Python-Installation testen.
Standard, Wissenschaftlich, Programmierer und Statistik öffnen; außerdem die
Zusatzbereiche und Hilfe. Die Startgröße bei 100/125/150/200 Prozent und einen
Wechsel zwischen Monitoren prüfen. Es ist keine automatische Monitor-DPI-
Neuberechnung implementiert.

Einige Rechnungen anlegen, den Verlauf über Ansicht und Strg+H öffnen und die
Rechtsausrichtung kurzer sowie umgebrochener Zeilen prüfen. Mit der echten Maus
rechtsklicken und Kopieren, Einfügen, Ausblenden und Löschen aufrufen; danach
Umschalt+F10 und die Menütaste prüfen. Kopieren muss den angeklickten Eintrag
nehmen, Ausblenden alle Einträge bewahren, Löschen nur den aktuellen Modus
betreffen. Die Zwischenablage zwischen dem Rechner und etwa Editor testen.

Mit einem Benutzerprofil und Entpackpfad mit Leerzeichen/Umlauten starten,
Speicher/Verlauf speichern, schließen und erneut öffnen. Die Nutzung mit einem
Standardbenutzer ohne Administratorrechte prüfen. Ein Upgrade bzw. manueller
Import der bisherigen Linux-state.json muss ohne Umdeutung der Zahlen erfolgen.
Die Original-Datei vor einem Import sichern.

## Herangezogene Primärdokumentation

- Python 3.13: Windows-Installation/Tcl-Tk: https://docs.python.org/3.13/using/windows.html
- Python/Tkinter: https://docs.python.org/3.13/library/tkinter.html
- Microsoft, DPI-Manifest und API-Verhalten: https://learn.microsoft.com/en-us/windows/win32/hidpi/setting-the-default-dpi-awareness-for-a-process
- PyInstaller 6.16, Systemanforderungen: https://pyinstaller.org/en/v6.16.0/requirements.html
- PyInstaller, getrennte Builds pro Betriebssystem: https://pyinstaller.org/en/stable/usage.html
- Tk 8.6, Windows-Menüimplementierung (TrackPopupMenu): https://github.com/tcltk/tk/blob/core-8-6-branch/win/tkWinMenu.c

Diese Dokumente wurden zur Plattformanbindung herangezogen. Sie sind kein
Nachweis, dass dieser Rechner bereits unter Windows gestartet wurde.
