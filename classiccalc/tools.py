"""Unit converters, calendar arithmetic, and classic calculation worksheets."""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta, datetime
from decimal import Decimal, DecimalException
from .mathlib import D, PI, CalcError, checked


@dataclass(frozen=True)
class Unit:
    scale: Decimal
    offset: Decimal = D(0)


def units(items: dict[str, str | Decimal]) -> dict[str, Unit]:
    return {name: Unit(D(factor)) for name, factor in items.items()}


# Affine conversion: base_value = value * scale + offset.
# Imperial length/mass and US/UK volume factors use their exact definitions.
UNITS: dict[str, dict[str, Unit]] = {
    "Angle": units({"Degrees": "1", "Gradians": ".9", "Radians": D(180)/PI}),
    "Area": units({
        "Acres": "4046.8564224", "Hectares": "10000", "Square centimeters": ".0001",
        "Square feet": ".09290304", "Square inches": ".00064516", "Square kilometers": "1000000",
        "Square meters": "1", "Square miles": "2589988.110336", "Square millimeters": ".000001",
        "Square yards": ".83612736"}),
    "Energy": units({
        "British thermal units (IT)": "1055.05585262", "Calories (thermochemical)": "4.184",
        "Electron volts": "1.602176634e-19", "Foot-pounds": "1.3558179483314004", "Joules": "1",
        "Kilocalories (thermochemical)": "4184", "Kilojoules": "1000", "Kilowatt-hours": "3600000"}),
    "Length": units({
        "Angstroms": "1e-10", "Centimeters": ".01", "Chains": "20.1168", "Fathoms": "1.8288",
        "Feet": ".3048", "Hands": ".1016", "Inches": ".0254", "Kilometers": "1000",
        "Links": ".201168", "Meters": "1", "Microns": ".000001", "Miles": "1609.344",
        "Millimeters": ".001", "Nanometers": "1e-9", "Nautical miles": "1852",
        "Picas": D(".0254")/6, "Rods": "5.0292", "Spans": ".2286", "Yards": ".9144"}),
    "Power": units({
        "BTU per minute (IT)": D("1055.05585262")/60,
        "Foot-pounds per minute": D("1.3558179483314004")/60,
        "Horsepower (mechanical)": "745.69987158227022", "Kilowatts": "1000", "Watts": "1"}),
    "Pressure": units({
        "Atmospheres": "101325", "Bars": "100000", "Kilopascals": "1000",
        "Millimeters of mercury": "133.322387415", "Pascals": "1",
        "Pounds per square inch": D(".45359237")*D("9.80665")/D(".00064516")}),
    "Temperature": {
        "Degrees Celsius": Unit(D(1), D("273.15")),
        "Degrees Fahrenheit": Unit(D(5)/9, D("273.15")-D(32)*D(5)/9),
        "Kelvin": Unit(D(1))},
    "Time": units({"Days": "86400", "Hours": "3600", "Microseconds": ".000001",
                   "Milliseconds": ".001", "Minutes": "60", "Seconds": "1", "Weeks": "604800"}),
    "Velocity": units({
        "Centimeters per second": ".01", "Feet per second": ".3048", "Kilometers per hour": D(1)/D("3.6"),
        "Knots": D(1852)/3600, "Mach (340.3 m/s reference)": "340.3", "Meters per second": "1",
        "Miles per hour": ".44704"}),
    "Volume": units({
        "Cubic centimeters": ".000001", "Cubic feet": ".028316846592", "Cubic inches": ".000016387064",
        "Cubic meters": "1", "Cubic yards": ".764554857984", "Fluid ounces (UK)": ".0000284130625",
        "Fluid ounces (US)": ".0000295735295625", "Gallons (UK)": ".00454609",
        "Gallons (US)": ".003785411784", "Liters": ".001", "Milliliters": ".000001",
        "Pints (UK)": ".00056826125", "Pints (US)": ".000473176473",
        "Quarts (UK)": ".0011365225", "Quarts (US)": ".000946352946"}),
    "Weight/Mass": units({
        "Carats": ".0002", "Centigrams": ".00001", "Decigrams": ".0001", "Dekagrams": ".01",
        "Grams": ".001", "Hectograms": ".1", "Kilograms": "1", "Long tons": "1016.0469088",
        "Milligrams": ".000001", "Ounces": ".028349523125", "Pounds": ".45359237",
        "Short tons": "907.18474", "Stones": "6.35029318", "Tonnes": "1000"}),
}


def convert(value: Decimal, category: str, source: str, target: str) -> Decimal:
    try:
        a, b = UNITS[category][source], UNITS[category][target]
        return checked((value * a.scale + a.offset - b.offset) / b.scale)
    except KeyError as exc:
        raise CalcError("Unknown unit") from exc
    except DecimalException as exc:
        raise CalcError("Conversion overflow") from exc


def parse_date(text: str) -> date:
    try:
        text = text.strip()
        if "." in text:
            return datetime.strptime(text, "%d.%m.%Y").date()
        return date.fromisoformat(text)
    except ValueError as exc:
        raise CalcError("Enter a date as YYYY-MM-DD") from exc


def add_date(start: date, years: int = 0, months: int = 0, days: int = 0) -> date:
    try:
        total = start.year*12 + start.month-1 + years*12 + months
        year, month0 = divmod(total, 12)
        if not 1 <= year <= 9999: raise ValueError("year out of range")
        day = min(start.day, calendar.monthrange(year, month0+1)[1])
        return date(year, month0+1, day) + timedelta(days=days)
    except (ValueError, OverflowError) as exc:
        raise CalcError("Date is outside the supported range") from exc


def date_difference(a: date, b: date) -> dict[str, int]:
    start, end = sorted((a, b))
    months = (end.year-start.year)*12 + end.month-start.month
    anchor = add_date(start, months=months)
    if anchor > end:
        months -= 1
        anchor = add_date(start, months=months)
    years, months = divmod(months, 12)
    weeks, days = divmod((end-anchor).days, 7)
    total = (end-start).days
    return {"years": years, "months": months, "weeks": weeks, "days": days,
            "total_days": total, "total_weeks": total//7, "remaining_days": total%7}


WORKSHEETS = {
    "Mortgage": {
        "purchase": "Purchase price", "down": "Down payment", "years": "Term (years)",
        "rate": "Interest rate (%)", "payment": "Monthly payment"},
    "Vehicle lease": {
        "purchase": "Purchase price", "residual": "Residual value", "months": "Lease term (months)",
        "rate": "Interest rate (%)", "payment": "Monthly payment"},
    "Fuel economy (mpg)": {
        "distance": "Distance (miles)", "fuel": "Fuel used (gallons)", "economy": "Fuel economy (mpg)"},
    "Fuel economy (L/100 km)": {
        "distance": "Distance (kilometers)", "fuel": "Fuel used (liters)", "economy": "Fuel economy (L/100 km)"},
}


def mortgage_payment(principal: Decimal, years: Decimal, rate: Decimal) -> Decimal:
    if principal <= 0 or years <= 0 or rate < 0:
        raise CalcError("Loan and term must be positive; rate cannot be negative")
    n, r = years*12, rate/1200
    if not r: return principal/n
    return principal*r/(1-(1+r)**(-n))


def solve_mortgage(target: str, v: dict[str, Decimal]) -> Decimal:
    if target == "payment":
        return mortgage_payment(v["purchase"]-v["down"], v["years"], v["rate"])
    if target in ("purchase", "down"):
        n, r, payment = v["years"]*12, v["rate"]/1200, v["payment"]
        if n <= 0 or payment <= 0 or r < 0: raise CalcError("Invalid payment, term, or rate")
        principal = payment*n if not r else payment*(1-(1+r)**(-n))/r
        return principal+v["down"] if target == "purchase" else v["purchase"]-principal
    principal = v["purchase"]-v["down"]
    if principal <= 0 or v["payment"] <= 0: raise CalcError("Loan and payment must be positive")
    if target == "years":
        r = v["rate"]/1200
        if r < 0: raise CalcError("Rate cannot be negative")
        if not r: return principal/v["payment"]/12
        if v["payment"] <= principal*r: raise CalcError("Payment does not cover interest")
        return -(1-principal*r/v["payment"]).ln()/(1+r).ln()/12
    if target == "rate":
        years = v["years"]
        if years <= 0: raise CalcError("Term must be positive")
        zero = principal/(years*12)
        if v["payment"] < zero: raise CalcError("Payment implies a negative rate")
        if v["payment"] == zero: return D(0)
        low, high = D(0), D(100)
        while mortgage_payment(principal, years, high) < v["payment"]:
            high *= 2
            if high > D("1e8"): raise CalcError("Rate is outside the supported range")
        for _ in range(220):
            mid = (low+high)/2
            if mortgage_payment(principal, years, mid) < v["payment"]: low = mid
            else: high = mid
        return (low+high)/2
    raise CalcError("Unknown mortgage field")


def solve_lease(target: str, v: dict[str, Decimal]) -> Decimal:
    # Same simplified amortization + money-factor model as the classic worksheet.
    # Annual percentage / 2400 is the monthly money factor, not a compound APR.
    if target == "payment":
        c, r, n, f = v["purchase"], v["residual"], v["months"], v["rate"]/2400
        if n <= 0: raise CalcError("Term must be positive")
        return (c-r)/n+(c+r)*f
    if target == "purchase":
        r, n, f, p = v["residual"], v["months"], v["rate"]/2400, v["payment"]
        if n <= 0: raise CalcError("Term must be positive")
        return (p+r/n-r*f)/(1/n+f)
    if target == "residual":
        c, n, f, p = v["purchase"], v["months"], v["rate"]/2400, v["payment"]
        if n <= 0 or f == 1/n: raise CalcError("No unique solution")
        return (p-c/n-c*f)/(f-1/n)
    if target == "months":
        c, r, f, p = v["purchase"], v["residual"], v["rate"]/2400, v["payment"]
        denominator = p-(c+r)*f
        if denominator <= 0: raise CalcError("Payment does not cover the financing charge")
        return (c-r)/denominator
    if target == "rate":
        c, r, n, p = v["purchase"], v["residual"], v["months"], v["payment"]
        if n <= 0 or c+r <= 0: raise CalcError("No unique solution")
        return (p-(c-r)/n)*2400/(c+r)
    raise CalcError("Unknown lease field")


def solve_worksheet(name: str, target: str, values: dict[str, Decimal]) -> Decimal:
    if name not in WORKSHEETS or target not in WORKSHEETS[name]:
        raise CalcError("Unknown worksheet field")
    if any(k not in values for k in WORKSHEETS[name] if k != target):
        raise CalcError("Fill in all input fields")
    if any(not v.is_finite() or v < 0 for v in values.values()):
        raise CalcError("Enter non-negative numbers")
    try:
        if name == "Mortgage": result = solve_mortgage(target, values)
        elif name == "Vehicle lease": result = solve_lease(target, values)
        elif name == "Fuel economy (mpg)":
            if target == "economy": result = values["distance"]/values["fuel"]
            elif target == "distance": result = values["economy"]*values["fuel"]
            else: result = values["distance"]/values["economy"]
        else:
            if target == "economy": result = values["fuel"]*100/values["distance"]
            elif target == "distance": result = values["fuel"]*100/values["economy"]
            else: result = values["economy"]*values["distance"]/100
        if result < 0: raise CalcError("These inputs produce a negative result")
        return checked(result)
    except DecimalException as exc:
        raise CalcError("Cannot solve with these inputs") from exc
