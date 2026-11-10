# Prüfbericht – Klassischer Rechner 1.1.0

## Umgebung und Umfang

Debian GNU/Linux 13, x86-64; Python 3.13.5; Tk 8.6.16; Xvfb/X11.
Die Screenshots wurden zusätzlich mit Python 3.11 und Pillow unter Xvfb
aufgenommen. Linux Mint selbst und die Windows-Referenzanwendung wurden in
dieser Umgebung nicht gestartet. Es wird keine pixel- oder funktionsidentische
Übereinstimmung mit Windows behauptet.

## Regressionstests

```sh
xvfb-run -a /usr/bin/python3 -m unittest discover -v
```

Ergebnis: **216 Tests bestanden; 0 Fehler, 0 Fehlschläge, 0 übersprungene Tests**.
Die vollständige Ausgabe steht in `test-results.txt`.

Die bestehende Suite enthält 178 Tests. Vier Erwartungen an englische
Zahlen-/Datumsdarstellung wurden für die deutsche Oberfläche angepasst.
Hinzu kamen 10 Sprach-/Formatprüfungen und 28 GUI-Regressionstests.
Insgesamt sind damit 52 GUI- und 164 übrige Testmethoden enthalten.

Neu geprüft wurden insbesondere die tatsächliche Textgeometrie des
rechtsbündigen Verlaufs, Menübedienung und echte Strg+H-Tastaturereignisse,
mehrzeilige lange Einträge, Schreibschutz, Auswahl mit Maus/Pfeiltasten,
Kopieren/Einfügen und Löschen über Tastatur und Kontextmenü. Der Rechtsklick
wird als Tk-Mausereignis erzeugt und die Sichtbarkeit des Menüs kontrolliert.
Ausblenden muss die Daten bewahren; Löschen darf den Verlauf eines anderen
Modus nicht entfernen. Leere Listen und deaktivierte Kommandos sind abgedeckt.

Die Sprachtests kontrollieren die Übersetzungsabdeckung aller Einheiten,
Arbeitsblattfelder und statischen Rechenkern-Fehlermeldungen. Deutsche
Dezimalzahlen, Ausdrücke, Gruppierungszeichen, Kalenderdaten, Statistikimport
und -export werden geprüft. Lokalisierte Auswahllisten müssen weiterhin die
unveränderten internen Kennungen liefern.

Alte englische Einstellungen einschließlich Speicher, Statistik, Verlauf,
Einheiten und Arbeitsblättern werden eingelesen. Ein eigener Test prüft alte
Komma-Gruppierung bei Arbeitsblättern; ein weiterer den neuen kanonischen
Speicherzyklus ohne erneute Umdeutung der Werte.

Die ursprünglichen Tests für Arithmetik, Präzision, Programmierer-Wortbreiten,
Parser, Speicher, Einheitenumrechnung, Datumsarithmetik, Arbeitsblätter,
Skalierung und Dateirechte sind weiterhin enthalten. Tk-Callback-Ausnahmen
lassen die GUI-Tests fehlschlagen.

## Unabhängiger numerischer Vergleich

```sh
python3 tools/verify_precision.py
```

**350 Prüfungen bestanden**, Referenz: mpmath mit 80 Dezimalstellen.
Maximal beobachteter skalierter Fehler: `6.7321061e-60`, geforderte Grenze:
`1e-45`. Die Tests verwenden deterministische Stichproben für 14
trigonometrische, hyperbolische, inverse und logarithmische Funktionen.
Das ist keine Genauigkeitsgarantie für jeden möglichen Grenzfall.
mpmath wird vom ausgelieferten Rechner nicht verwendet.

## Sichtprüfung

Aufnahmen der laufenden Anwendung bei 150 % Skalierung: Standard,
Wissenschaftlich, Umkehrfunktionen, Programmierer, Statistik, Verlauf,
Verlauf mit geöffnetem Kontextmenü, Einheitenumrechnung, Datumsberechnung
und Hypothekenarbeitsblatt. Die rechtsbündigen Zeilen und die vier gewünschten
Kontextmenüeinträge sind auf den Verlaufsbildern sichtbar. Unter Xvfb lief kein
Fenstermanager; daher zeigen die Bilder keine native Linux-Titelleiste.

## Paketprüfung

Die erzeugten Pakete werden mit `dpkg-deb` geprüft und in ein temporäres
Verzeichnis entpackt. Version und Kommandozeilenberechnung werden sowohl aus
dem entpackten Paket als auch aus der Python-Anwendungsdatei geprüft.
GUI-Start, Benutzerinstallation und Deinstallation werden in einer isolierten
Testumgebung geprüft. Das Protokoll steht in `packaging-results.txt`.

Diese Prüfung ersetzt keine apt-Installation auf einem tatsächlichen
Linux-Mint-Desktop. Das Debian-Paket enthält architekturunabhängigen Python-Code
und deklariert Python 3.10+ sowie Tk als Systemabhängigkeiten.
