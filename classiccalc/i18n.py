"""German presentation layer; persisted identifiers and the math engine stay stable."""
from __future__ import annotations

from datetime import date, datetime
import re

TRANSLATIONS = {
    "Calculator": "Rechner", "Classic Calculator": "Klassischer Rechner",
    "Standard": "Standard", "Scientific": "Wissenschaftlich", "Programmer": "Programmierer", "Statistics": "Statistik",
    "View": "Ansicht", "Edit": "Bearbeiten", "Help": "Hilfe", "History": "Verlauf",
    "Digit grouping": "Zifferngruppierung", "Basic": "Basis", "Unit conversion": "Einheitenumrechnung",
    "Date calculation": "Datumsberechnung", "Worksheets": "Arbeitsblätter",
    "Always on top": "Immer im Vordergrund", "Interface size": "Oberflächengröße",
    "Copy": "Kopieren", "Paste": "Einfügen", "Hide history": "Verlauf ausblenden", "Show history": "Verlauf einblenden",
    "Edit history calculation": "Berechnung im Verlauf bearbeiten", "Copy history": "Verlauf kopieren",
    "Clear history": "Verlauf löschen", "Import statistics data…": "Statistikdaten importieren…",
    "Export statistics data…": "Statistikdaten exportieren…", "View Help": "Hilfe anzeigen", "About Calculator": "Info zum Rechner",
    "Double-click to copy the result": "Doppelklicken, um das Ergebnis zu kopieren",
    "Double-click: recall. Delete: remove selected sample.": "Doppelklick: Wert übernehmen. Entf: ausgewählten Wert löschen.",
    "Delete": "Löschen", "Clear": "Leeren", "Close": "Schließen",
    "Clear memory (Ctrl+L)": "Speicher löschen (Strg+L)", "Recall memory (Ctrl+R)": "Speicher abrufen (Strg+R)",
    "Store in memory (Ctrl+M)": "Im Speicher ablegen (Strg+M)", "Add to memory (Ctrl+P)": "Zum Speicher addieren (Strg+P)",
    "Subtract from memory (Ctrl+Q)": "Vom Speicher subtrahieren (Strg+Q)", "Inverse functions (I)": "Umkehrfunktionen (I)",
    "Degrees": "Grad", "Radians": "Bogenmaß", "Gradians": "Neugrad", "Grads": "Neugrad",
    "Click a bit to toggle it. Gray bits are outside the selected word size.": "Ein Bit zum Umschalten anklicken. Graue Bits liegen außerhalb der gewählten Wortbreite.",
    "Clear all statistics data": "Alle Statistikdaten löschen",
    "Add displayed value to the dataset (Enter)": "Angezeigten Wert zur Datenreihe hinzufügen (Eingabe)",
    "Mean": "Arithmetischer Mittelwert", "Mean square": "Mittelwert der Quadrate", "Sum": "Summe",
    "Sum square": "Summe der Quadrate", "Population sd": "Standardabweichung der Grundgesamtheit", "Sample sd": "Stichprobenstandardabweichung",
    "Select the type of unit you want to convert": "Wählen Sie die Art der umzurechnenden Einheit",
    "From": "Von", "To": "Nach", "Use display": "Anzeige übernehmen", "Swap": "Tauschen", "Copy result": "Ergebnis kopieren",
    "Select the date calculation you want": "Wählen Sie die gewünschte Datumsberechnung",
    "Difference": "Differenz zwischen zwei Datumsangaben", "Add / subtract": "Tage addieren oder subtrahieren",
    "From (YYYY-MM-DD)": "Von (TT.MM.JJJJ)", "To (YYYY-MM-DD)": "Bis (TT.MM.JJJJ)",
    "Add": "Addieren", "Subtract": "Subtrahieren", "Years": "Jahre", "Months": "Monate", "Days": "Tage",
    "Calculate": "Berechnen", "Result": "Ergebnis", "Select the value you want to calculate": "Wählen Sie den zu berechnenden Wert",
    "Mortgage": "Hypothek", "Vehicle lease": "Fahrzeugleasing", "Fuel economy (mpg)": "Kraftstoffverbrauch (mpg)",
    "Fuel economy (L/100 km)": "Kraftstoffverbrauch (l/100 km)", "Purchase price": "Kaufpreis",
    "Down payment": "Anzahlung", "Term (years)": "Laufzeit (Jahre)", "Interest rate (%)": "Zinssatz (%)",
    "Monthly payment": "Monatliche Rate", "Residual value": "Restwert", "Lease term (months)": "Leasingdauer (Monate)",
    "Distance (miles)": "Strecke (Meilen)", "Fuel used (gallons)": "Verbrauchte Kraftstoffmenge (Gallonen)",
    "Distance (kilometers)": "Strecke (Kilometer)", "Fuel used (liters)": "Verbrauchte Kraftstoffmenge (Liter)",
    "Edit calculation": "Berechnung bearbeiten", "Edit the expression, then press Enter.": "Bearbeiten Sie den Ausdruck und drücken Sie die Eingabetaste.",
    "Recall": "Übernehmen", "Delete selected": "Ausgewählten Wert löschen", "Clear all data": "Alle Daten löschen",
    "Import statistics data": "Statistikdaten importieren", "Export statistics data": "Statistikdaten exportieren",
    "All files": "Alle Dateien", "Text / CSV": "Text / CSV", "Import failed": "Import fehlgeschlagen", "Export failed": "Export fehlgeschlagen",
    "Calculator Help": "Rechner-Hilfe", "Choose a date": "Datum auswählen", "Today": "Heute",
    # Units: canonical English identifiers remain unchanged in state.json.
    "Angle": "Winkel", "Area": "Fläche", "Energy": "Energie", "Length": "Länge", "Power": "Leistung",
    "Pressure": "Druck", "Temperature": "Temperatur", "Time": "Zeit", "Velocity": "Geschwindigkeit",
    "Volume": "Volumen", "Weight/Mass": "Gewicht/Masse",
    "Acres": "Acre", "Hectares": "Hektar", "Square centimeters": "Quadratzentimeter", "Square feet": "Quadratfuß",
    "Square inches": "Quadratzoll", "Square kilometers": "Quadratkilometer", "Square meters": "Quadratmeter",
    "Square miles": "Quadratmeilen", "Square millimeters": "Quadratmillimeter", "Square yards": "Quadratyard",
    "British thermal units (IT)": "Britische Wärmeeinheiten (IT)", "Calories (thermochemical)": "Kalorien (thermochemisch)",
    "Electron volts": "Elektronenvolt", "Foot-pounds": "Fuß-Pfund", "Joules": "Joule",
    "Kilocalories (thermochemical)": "Kilokalorien (thermochemisch)", "Kilojoules": "Kilojoule", "Kilowatt-hours": "Kilowattstunden",
    "Angstroms": "Ångström", "Centimeters": "Zentimeter", "Chains": "Ketten (Chain)", "Fathoms": "Faden (Fathom)",
    "Feet": "Fuß", "Hands": "Handbreit (Hand)", "Inches": "Zoll", "Kilometers": "Kilometer", "Links": "Kettenglieder (Link)",
    "Meters": "Meter", "Microns": "Mikrometer", "Miles": "Meilen", "Millimeters": "Millimeter", "Nanometers": "Nanometer",
    "Nautical miles": "Seemeilen", "Picas": "Pica", "Rods": "Ruten (Rod)", "Spans": "Spannen (Span)", "Yards": "Yard",
    "BTU per minute (IT)": "BTU pro Minute (IT)", "Foot-pounds per minute": "Fuß-Pfund pro Minute",
    "Horsepower (mechanical)": "Horsepower (mechanisch)", "Kilowatts": "Kilowatt", "Watts": "Watt",
    "Atmospheres": "Atmosphären", "Bars": "Bar", "Kilopascals": "Kilopascal", "Millimeters of mercury": "Millimeter Quecksilbersäule",
    "Pascals": "Pascal", "Pounds per square inch": "Pfund pro Quadratzoll", "Degrees Celsius": "Grad Celsius",
    "Degrees Fahrenheit": "Grad Fahrenheit", "Kelvin": "Kelvin", "Hours": "Stunden", "Microseconds": "Mikrosekunden",
    "Milliseconds": "Millisekunden", "Minutes": "Minuten", "Seconds": "Sekunden", "Weeks": "Wochen",
    "Centimeters per second": "Zentimeter pro Sekunde", "Feet per second": "Fuß pro Sekunde",
    "Kilometers per hour": "Kilometer pro Stunde", "Knots": "Knoten", "Mach (340.3 m/s reference)": "Mach (Referenz: 340,3 m/s)",
    "Meters per second": "Meter pro Sekunde", "Miles per hour": "Meilen pro Stunde",
    "Cubic centimeters": "Kubikzentimeter", "Cubic feet": "Kubikfuß", "Cubic inches": "Kubikzoll", "Cubic meters": "Kubikmeter",
    "Cubic yards": "Kubikyard", "Fluid ounces (UK)": "Flüssigunzen (UK)", "Fluid ounces (US)": "Flüssigunzen (US)",
    "Gallons (UK)": "Gallonen (UK)", "Gallons (US)": "Gallonen (US)", "Liters": "Liter", "Milliliters": "Milliliter",
    "Pints (UK)": "Pint (UK)", "Pints (US)": "Pint (US)", "Quarts (UK)": "Quart (UK)", "Quarts (US)": "Quart (US)",
    "Carats": "Karat", "Centigrams": "Zentigramm", "Decigrams": "Dezigramm", "Dekagrams": "Dekagramm",
    "Grams": "Gramm", "Hectograms": "Hektogramm", "Kilograms": "Kilogramm", "Long tons": "Britische Tonnen",
    "Milligrams": "Milligramm", "Ounces": "Unzen", "Pounds": "Pfund", "Short tons": "US-Tonnen", "Stones": "Stone", "Tonnes": "Tonnen",
    # Application errors (engine internals remain language-independent).
    "Unknown mode": "Unbekannter Modus", "Unknown operation": "Unbekannte Operation", "Incomplete expression": "Unvollständiger Ausdruck",
    "Invalid number base": "Ungültige Zahlenbasis", "Invalid word size": "Ungültige Wortbreite", "No data": "Keine Daten",
    "Maximum of 10,000 samples": "Höchstens 10.000 Werte zulässig", "Too many parentheses": "Zu viele Klammern",
    "Unmatched parentheses": "Nicht zusammenpassende Klammern", "Input is too long": "Eingabe zu lang",
    "Value exceeds selected word size": "Wert überschreitet die gewählte Wortbreite", "Invalid input": "Ungültige Eingabe",
    "Unknown memory command": "Unbekannter Speicherbefehl", "Paste an integer in the selected base": "Geben Sie eine ganze Zahl in der gewählten Zahlenbasis ein",
    "Cannot divide by zero": "Division durch Null nicht möglich", "Invalid expression": "Ungültiger Ausdruck",
    "Operation not available in Programmer mode": "Operation im Programmierermodus nicht verfügbar", "Unknown statistic": "Unbekannte Statistikfunktion",
    "At least two values required": "Mindestens zwei Werte erforderlich", "Invalid shift count": "Ungültige Anzahl an Verschiebungen",
    "Result is not finite": "Ergebnis ist nicht endlich", "Overflow": "Überlauf", "Angle is too large": "Winkel zu groß",
    "Unknown function": "Unbekannte Funktion", "Number is too long": "Zahl zu lang", "Overflow or invalid input": "Überlauf oder ungültige Eingabe",
    "Empty or too long expression": "Ausdruck leer oder zu lang", "Expression is too long": "Ausdruck zu lang",
    "Expression is too deeply nested": "Ausdruck zu tief verschachtelt", "Overflow or invalid expression": "Überlauf oder ungültiger Ausdruck",
    "Invalid DMS value": "Ungültige Grad-Minuten-Sekunden-Angabe", "Missing closing parenthesis": "Schließende Klammer fehlt",
    "Use parentheses for functions": "Verwenden Sie Klammern bei Funktionen", "Unknown mortgage field": "Unbekanntes Hypothekenfeld",
    "Unknown lease field": "Unbekanntes Leasingfeld", "Loan and term must be positive; rate cannot be negative": "Kreditbetrag und Laufzeit müssen positiv sein; der Zinssatz darf nicht negativ sein",
    "Loan and payment must be positive": "Kreditbetrag und Rate müssen positiv sein", "Unknown worksheet field": "Unbekanntes Arbeitsblattfeld",
    "Fill in all input fields": "Füllen Sie alle Eingabefelder aus", "Enter non-negative numbers": "Geben Sie nichtnegative Zahlen ein",
    "Unknown unit": "Unbekannte Einheit", "Conversion overflow": "Überlauf bei der Umrechnung",
    "Enter a date as YYYY-MM-DD": "Datum als TT.MM.JJJJ oder JJJJ-MM-TT eingeben",
    "Date is outside the supported range": "Datum außerhalb des unterstützten Bereichs",
    "Invalid payment, term, or rate": "Ungültige Rate, Laufzeit oder ungültiger Zinssatz", "Rate cannot be negative": "Zinssatz darf nicht negativ sein",
    "Payment does not cover interest": "Rate deckt die Zinsen nicht", "Term must be positive": "Laufzeit muss positiv sein",
    "Payment implies a negative rate": "Die Rate ergibt einen negativen Zinssatz", "No unique solution": "Keine eindeutige Lösung",
    "Payment does not cover the financing charge": "Rate deckt die Finanzierungskosten nicht",
    "These inputs produce a negative result": "Diese Eingaben ergeben ein negatives Ergebnis", "Cannot solve with these inputs": "Mit diesen Eingaben nicht lösbar",
    "Rate is outside the supported range": "Zinssatz außerhalb des unterstützten Bereichs", "File exceeds the 2 MB limit": "Datei überschreitet die Grenze von 2 MB",
    "Use Add or Subtract; enter non-negative values": "Wählen Sie Addieren oder Subtrahieren und geben Sie nichtnegative Werte ein",
    "Years, months and days must be whole numbers": "Jahre, Monate und Tage müssen ganze Zahlen sein",
    "Unexpected error — see terminal": "Unerwarteter Fehler – siehe Terminal",
}


def tr(text: str) -> str:
    return TRANSLATIONS.get(text, text)


def display_number(text: str) -> str:
    """Convert canonical decimal/group separators, never doing binary-float math."""
    return str(text).translate(str.maketrans({".": ",", ",": "."}))


_NUMERIC = re.compile(r"(?:\d+(?:[.,]\d*)*|[.,]\d+)(?:[eE][+-]?\d+)?")


def normalize_input(text: str) -> str:
    """Decimal comma for German input; ungrouped decimal point also accepted.

    A comma makes dots thousands separators (1.234,5 -> 1234.5). A lone
    point remains a decimal point for old settings and dot-decimal imports.
    Multiple grouping dots are allowed only in correctly grouped numbers.
    The expression parser still validates all tokens; nothing is executed.
    """
    text = text.strip().replace("\u00a0", "").replace("\u202f", "")
    def convert(match: re.Match) -> str:
        token = match.group()
        if "," in token:
            return token.replace(".", "").replace(",", ".")
        if re.fullmatch(r"\d{1,3}(?:\.\d{3}){2,}", token):
            return token.replace(".", "")
        return token
    return _NUMERIC.sub(convert, text)


MONTHS = ("", "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember")
WEEKDAYS = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")


def date_text(value: date) -> str:
    return f"{value.day:02d}.{value.month:02d}.{value.year:04d}"


def date_input_text(text: str) -> str:
    try:
        return date_text(date.fromisoformat(text))
    except ValueError:
        return text


def date_description(value: date) -> str:
    return f"{WEEKDAYS[value.weekday()]}, {value.day:02d}. {MONTHS[value.month]} {value.year:04d}"


def date_duration(values: dict) -> str:
    labels = {"years": ("Jahr", "Jahre"), "months": ("Monat", "Monate"), "weeks": ("Woche", "Wochen"), "days": ("Tag", "Tage")}
    parts = [f"{values[key]} {names[0 if values[key] == 1 else 1]}" for key, names in labels.items() if values[key]]
    count = values["total_days"]
    return ", ".join(parts or ["0 Tage"]) + f"\n\n{display_number(format(count, ',d'))} {'Tag' if count == 1 else 'Tage'}"
