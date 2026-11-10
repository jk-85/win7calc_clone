# Änderungen

## 1.3.0 – Verlauf in Standard, helle Navigation, Deutsch/English

Gemeinsames Update für Linux Mint x64 und das Windows-10-x64-Projekt, auf Basis
von 1.2.0 unter Erhalt sämtlicher bisherigen Funktionen und Windows-Starter.

- Standard und Wissenschaftlich verwenden dasselbe rechtsbündige Verlaufswidget;
  Ausrichtung gilt für jede Zeile einschließlich Umbrüchen und Markierungen.
- Kontextmenü mit Kopieren, Einfügen, Verlauf ausblenden und Verlauf löschen,
  auch auf leeren Bereichen und der Kopfzeile; zusätzlich Tastaturzugriff.
- Helle ▲-/▼-Tasten oben rechts im Verlauf; Bildlauf um eine sichtbare Zeile,
  deaktivierte Tasten an den Grenzen, keine Änderung der Berechnung.
- Ansicht → Sprache → Deutsch / English, sofortiger Wechsel ohne Datenverlust;
  persistierte Sprache, lokalisierte Zahlen/Datumsfelder/Hilfe/Kalender/Dialoge.
- Neue CLI-Option --language de|en; ältere Profile starten weiterhin deutsch.
- 60 neue Regressionstests; insgesamt 311 Tests, darunter 104 GUI-Tests.
- Erweiterte Paket-Selbsttests, 14 aktuelle Screenshots direkt unter der
  README-Hauptüberschrift und aktualisierte Linux-/Windows-Dokumentation.

Rechenkern, mathematische Routinen und Zusatzberechnungen bleiben bytegleich zu
1.2.0. Kein unter Windows gebautes EXE-Paket in dieser Lieferung. Pfeilposition
und Funktion mangels neuer Referenzaufnahme als Auf-/Ab-Bildlauf umgesetzt.

# Änderungen

## 1.2.0 – Windows-Port, 10. November 2026

- Windows-10-x64-Zielplattform, Start.cmd und konsolenfreier app.pyw-Einstieg.
- Vollständiger vorhandener deutscher Rechenkern und klassische Tastenlayouts beibehalten.
- Rechtsbündiger Verlauf über Menü und Strg+H; die vier deutschen Kontextmenüaktionen bleiben erhalten.
- Einstellungen unter %APPDATA%/ClassicCalc; kompatibles Schema 2, alte Daten weiterhin lesbar.
- Eigene Windows-Anwendungskennung, System-DPI beim Start, Manifest und Projekt-ICO.
- AltGr-Mathematikzeichen auf deutschen Windows-Tastaturen berücksichtigt.
- Lokale Diagnoseausgabe auch ohne Konsole.
- Windows-x64-Buildwerkzeug mit isolierter Umgebung, Tests, EXE-Selbstprüfung und portablem ZIP.
- README auf Windows umgestellt; die zehn vorhandenen PNGs weiterhin direkt unter der Hauptüberschrift.
- Linux bleibt unterstützt; Windows-spezifische APIs sind isoliert.
- Keine Behauptung eines durchgeführten nativen Windows-Tests oder eines mitgelieferten EXE-Builds.

## 1.1.0 – 10. November 2026

- Deutsche Oberfläche, Hilfe, Fehlermeldungen, Einheiten, Kalender und Starter.
- Dezimalkomma in Anzeige, Statistik und Zwischenablage; deutsche Datumseingabe.
- Wirklich rechtsbündiger, schreibgeschützter Verlauf mit Umbruch und Scrollbar.
- Einheitliches Verhalten bei Ansicht > Verlauf und Strg+H, auch nach Skalierung.
- Rechtsklickmenü mit Kopieren, Einfügen, Verlauf ausblenden und Verlauf löschen.
- Kontextmenü auch per Menütaste oder Umschalt+F10; Tastenkürzel funktionieren
  auch bei fokussiertem Verlauf.
- Kopieren im Verlauf bezieht sich auf den ausgewählten Eintrag; Einfügen wirkt
  auf den Rechner. Ausblenden bewahrt Daten, Löschen betrifft nur den aktuellen Modus.
- Kompatible Migration alter Einstellungen; Zahlenwerte werden kanonisch gespeichert.
- 38 neue Regressionstests. Vier bestehende GUI-Erwartungen an die gewollten
  deutschen Text-/Zahlenformate angepasst. Rechenkern unverändert; Datumsparser
  zusätzlich um deutsche Datumsangaben erweitert.

## 1.0.0

Erste eigenständige Linux-Rekonstruktion mit englischer Oberfläche.
