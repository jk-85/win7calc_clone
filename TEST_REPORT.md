# Prüfbericht – Klassischer Rechner 1.3.0

Prüfdatum: 10. November 2026. Grundlage: Windows-/Linux-Quellcode 1.2.0,
überarbeitet für rechtsbündigen Standard-Verlauf, Kontextmenü, helle
Auf-/Ab-Tasten und die sofortige deutsche/englische Sprachumschaltung.

## Tatsächlich verwendete Umgebung

Debian GNU/Linux 13 (trixie), x86-64, CPython 3.13.5, Tcl/Tk 8.6.16, Xvfb.
Keine native Windows-10- oder Linux-Mint-Desktopinstallation. Die UI-Aufnahmen
in `screenshots/` stammen aus dieser laufenden Linux/Tk-Anwendung (1.3.0).
Sie sind keine Windows-Aufnahmen und keine generierten UI-Entwürfe.

## Automatisierte Suite

```sh
xvfb-run -a python3 -m unittest discover -v
```

**311 Tests bestanden; 0 Fehler, 0 fehlgeschlagene und 0 übersprungene Tests.**
Davon **104 GUI-Tests**: 24 allgemeine, 28 deutsche, 8 Windows-Port-/Tastaturtests
und 44 zusätzliche GUI-Regressionstests für 1.3.0. Die 16 neuen sprachbezogenen
Format-/CLI-Tests ergeben mit diesen 44 GUI-Tests insgesamt 60 neue Tests.
Alle 251 bisherigen Tests bleiben Teil der Suite.

Rohprotokoll: `test-results.txt`. Neue Tests: `tests/test_update_130.py`.

Geprüft werden unter anderem:

- Die tatsächlich gerenderten rechten Kanten von Verlaufstext in Standard:
  nach Öffnung über Ansicht und über echtes Strg+H, in DE/EN, bei 75/100/125/
  150/200/300 % Skalierung, einschließlich markierter/umgebrochener Zeilen.
- Wissenschaftlicher Verlauf in beiden Sprachen; getrennte Daten beider Modi.
- Echte Rechtsklick-Ereignisse im Standard-Verlauf, auf leerem Textbereich,
  Kopfzeile, Pfeilen und Ergebnisanzeige; zusätzlich Umschalt+F10 und Menütaste.
- Exakte vier Kontextbefehle in DE/EN. Kopieren benutzt den gewählten Eintrag;
  Einfügen verändert die Rechnung, nicht den Verlauf; Ausblenden erhält Daten;
  Löschen betrifft ausschließlich den aktuellen Modus.
- Die Lage beider Pfeile oben rechts, helle Hintergründe, echte Mausbetätigung,
  Bildlauf in beide Richtungen und in langen umgebrochenen Einträgen,
  deaktivierte Grenzen und unveränderte Rechnung/Verlaufsdaten beim Scrollen.
- Sprachwechsel über echte Menükommandos ohne Neustart: Fenster-/Menütitel,
  Kontextmenüs, Dezimaltaste, Zwischenablage, Fehlermeldungen, Hilfe, Info-Dialog,
  Monats-/Wochentagsnamen, Einheitenauswahl und Statistikbezeichnungen.
- Erhalt laufender Rechenoperationen, Speicher, Verlaufsauswahl, Statistikdaten,
  Umkehrfunktionswahl und Programmierereinstellungen; Normalisierung von
  bearbeiteten Umrechnungs-, Datums- und Arbeitsblattfeldern vor Sprachwechsel.
- Bereits geöffnetes Hilfefenster wechselt die Sprache ebenfalls; wiederholter
  Menü-/GUI-Neuaufbau hinterlässt keine beobachteten Tk-Callbackfehler.
- Speichern und Neustart mit Englisch/rechtsbündigem Standard-Verlauf, alte
  Profile ohne Sprachangabe, ungültige Sprachauswahl und `--fresh` ohne Schreiben.
- CLI-Auswertung mit deutschen und englischen Gruppierungs-/Dezimalzeichen.

## Unabhängige numerische Gegenprüfung

```sh
python3 tools/verify_precision.py
```

**350 Prüfungen bestanden**, mit mpmath bei 80 Dezimalstellen und reproduzierbarer
Eingabefolge. Größter skalierter Fehler: **6.7321061e-60**; Prüfschranke 1e-45.
Rohprotokoll: `precision-results.txt`. Rechenkern, Mathematik und Zusatzberechnungen
sind gegenüber 1.2.0 unverändert. Dies prüft nicht jede mögliche numerische Eingabe
und beweist keine Identität mit Microsofts Originalprogramm.

## Pakete und Startprüfung

Der erweiterte Selbsttest wird mit `--smoke-test REPORT.json` gestartet. Er prüft
24 Bedingungen an echten Widgets, unter anderem Standard-/wissenschaftliche
Arithmetik, Strg+H, Kontextmenüaufbau, Pfeilbildlauf, englische Sprachwahl und
Rückkehr zu Deutsch. Er schreibt keine Benutzereinstellungen und manipuliert
die Zwischenablage nicht. Der Prüfbericht enthält Plattform und Version.

Die Paketprüfungen betreffen den Quellstart, `app.pyw`, Linux-`.pyz`, Windows-
`.pyzw` unter Linux, den aus dem DEB extrahierten Anwendungscode und frisch
entpackte Linux-/Windows-Quellarchive. Detaillierte Aufrufe/Ergebnisse stehen in
`packaging-results.txt` und `verification/`. Prüfungen nach dem ZIP-Erstellen
werden zusätzlich in der separat gelieferten `classic-calc-1.3.0-verification.zip`
abgelegt. Der Windows-Quellstand verwendet dieselben Module in `classiccalc/`
wie das Linux-Projekt; ein SHA-256-Abgleich ist Teil der Paketprüfung.

**Eine `.pyzw` ist kein natives Windows-Binary.** Ihre Prüfung auf Linux belegt
die Lauffähigkeit des gebündelten Python-Codes, nicht das Windows-Startverhalten.
Das DEB wurde gebaut, inspiziert und extrahiert; es wurde nicht in einer
Linux-Mint-Installation per apt installiert. Ein nativer Windows-EXE-Build wurde
hier nicht durchgeführt, und es wird keine fertige Windows-EXE geliefert.

## Vor Veröffentlichung auf Windows 10 manuell prüfen

`build-windows.cmd` auf Windows 10 x64 ausführen. Das Skript führt die gesamte
Suite und den 24-Punkte-Selbsttest an der erzeugten EXE aus. Anschließend auf
einem Zielrechner ohne separate Python-Installation starten und Standard sowie
Wissenschaftlich prüfen: Menü/Strg+H, Textausrichtung, beide Pfeile, echte
Rechtsklickmenüs, alle vier Aktionen, Sprachwechsel und Neustart.

Unter Win32 wird ausschließlich das native modale `tk_popup` in den unbeaufsichtigten
Ereignistests ersetzt, damit diese nicht auf einen Benutzerklick warten. Der
Menüaufbau, die Ereigniszuordnung und die Befehle bleiben echt. Daher muss das
tatsächliche Öffnen, Positionieren und Bedienen des nativen Windows-Kontextmenüs
mit Maus und Tastatur gesondert geprüft werden. Unter Linux wurden die Menüs
tatsächlich eingeblendet und ihre Sichtbarkeit geprüft.

Win32-API-/AppData-Prüfungen verwenden auf dem Linux-Host Testdoubles. Sie ersetzen
keine Windows-DPI-Prüfung, kein reales AltGr-Tastaturlayout, keinen SmartScreen-
Test und keinen Start mit einem Standardbenutzer. Windows-Systemrahmen und
native Menüs können anders aussehen. Kein dynamisches Per-Monitor-V2-Verhalten.

## Referenzgrenze

Zur letzten Pfeil-Anforderung war kein neuer Referenz-Screenshot vorhanden.
Die beiden hellen Pfeile sind als zeilenweise Auf-/Ab-Bildlaufsteuerung oben
rechts im eingeblendeten Verlauf umgesetzt. Eine pixelgenaue Übereinstimmung
mit einer nicht vorliegenden Referenz wird nicht behauptet.
