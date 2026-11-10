"""Decimal mathematics and a small, non-executing expression parser.

No Python eval/exec, binary floating-point arithmetic, or network services are used.
"""
from __future__ import annotations

import re
from decimal import Decimal, DecimalException, getcontext, localcontext
from typing import Callable

getcontext().prec = 60
getcontext().Emax = 9999
getcontext().Emin = -9999
D = Decimal
PI = D("3.141592653589793238462643383279502884197169399375105820974944592307816406286")
E = D("2.718281828459045235360287471352662497757247093699959574966967627724076630353")
EPS = D("1e-65")
MAX_INPUT = 4096


class CalcError(ValueError):
    """An error which can safely be presented in the calculator display."""


def checked(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise CalcError("Result is not finite")
    if value and abs(value.adjusted()) > 9999:
        raise CalcError("Overflow")
    return +value


def number(text: str) -> Decimal:
    try:
        if len(text) > MAX_INPUT:
            raise CalcError("Number is too long")
        return checked(D(text))
    except (DecimalException, ValueError) as exc:
        raise CalcError("Invalid input") from exc


def format_number(value: Decimal | int, scientific: bool = False,
                  grouping: bool = False, digits: int = 32) -> str:
    if isinstance(value, int):
        return format(value, ",d") if grouping else str(value)
    if not value:
        return "0"
    value = checked(value)
    with localcontext() as ctx:
        ctx.prec = digits
        rounded = +value
        use_exp = scientific or rounded.adjusted() >= digits or rounded.adjusted() < -10
        if use_exp:
            mantissa, exponent = format(rounded, f".{digits - 1}E").split("E")
            return mantissa.rstrip("0").rstrip(".") + "e" + str(int(exponent))
        result = format(rounded, "f")
        if "." in result:
            result = result.rstrip("0").rstrip(".")
        if grouping:
            integer, dot, fraction = result.partition(".")
            integer = format(int(integer), ",d") if integer not in ("-0", "+0") else integer
            return integer + dot + fraction
        return result


def power(x: Decimal, y: Decimal) -> Decimal:
    if not x and y <= 0:
        raise CalcError("Invalid input" if not y else "Cannot divide by zero")
    if x < 0 and y != y.to_integral_value():
        raise CalcError("Invalid input")
    try:
        return checked(x ** y)
    except DecimalException as exc:
        raise CalcError("Overflow or invalid input") from exc


def root(x: Decimal, degree: Decimal) -> Decimal:
    if not degree:
        raise CalcError("Cannot divide by zero")
    if x < 0:
        if degree != degree.to_integral_value() or int(degree) % 2 == 0:
            raise CalcError("Invalid input")
        return -power(-x, 1 / degree)
    if not x:
        if degree < 0:
            raise CalcError("Cannot divide by zero")
        return D(0)
    return power(x, 1 / degree)


def factorial(x: Decimal) -> Decimal:
    if x < 0 or x != x.to_integral_value():
        raise CalcError("Invalid input")
    if x > 3248:
        raise CalcError("Overflow")
    result = D(1)
    for i in range(2, int(x) + 1):
        result *= i
    return checked(result)


def angle_to_rad(x: Decimal, mode: str) -> Decimal:
    return x * PI / (D(180) if mode == "Degrees" else D(200)) if mode != "Radians" else x


def rad_to_angle(x: Decimal, mode: str) -> Decimal:
    return x * (D(180) if mode == "Degrees" else D(200)) / PI if mode != "Radians" else x


def sincos(x: Decimal) -> tuple[Decimal, Decimal]:
    if abs(x) > D("1e45"):
        raise CalcError("Angle is too large")
    with localcontext() as ctx:
        ctx.prec += 12
        x %= 2 * PI
        if x > PI:
            x -= 2 * PI
        if x < -PI:
            x += 2 * PI
        xx = x * x
        s, c, st, ct = x, D(1), x, D(1)
        for n in range(1, 400):
            st *= -xx / D((2 * n) * (2 * n + 1))
            ct *= -xx / D((2 * n - 1) * (2 * n))
            s += st
            c += ct
            if abs(st) < EPS and abs(ct) < EPS:
                break
    # Suppress tiny cancellation residue at exact quadrantal angles.
    s = D(0) if abs(s) < D("1e-57") else +s
    c = D(0) if abs(c) < D("1e-57") else +c
    return s, c


def atan(x: Decimal) -> Decimal:
    sign = -1 if x < 0 else 1
    x = abs(x)
    reciprocal = x > 1
    if reciprocal:
        x = 1 / x
    with localcontext() as ctx:
        ctx.prec += 12
        factor = 1
        while x > D("0.08"):
            x = x / (1 + (1 + x * x).sqrt())
            factor *= 2
        term, total = x, x
        for n in range(1, 2000):
            term *= -x * x
            delta = term / (2 * n + 1)
            total += delta
            if abs(delta) < EPS:
                break
        result = total * factor
        if reciprocal:
            result = PI / 2 - result
    return checked(result * sign)


def unary(name: str, x: Decimal, angle: str = "Degrees") -> Decimal:
    try:
        if name == "neg": return -x
        if name == "abs": return abs(x)
        if name == "sqrt":
            if x < 0: raise CalcError("Invalid input")
            return x.sqrt()
        if name == "square": return checked(x * x)
        if name == "cube": return checked(x * x * x)
        if name == "cuberoot": return root(x, D(3))
        if name == "reciprocal":
            if not x: raise CalcError("Cannot divide by zero")
            return 1 / x
        if name == "factorial": return factorial(x)
        if name == "int": return D(int(x))
        if name == "frac": return x - D(int(x))
        if name in ("ln", "log"):
            if x <= 0: raise CalcError("Invalid input")
            return x.ln() if name == "ln" else x.log10()
        if name == "exp": return checked(x.exp())
        if name == "pow10": return power(D(10), x)
        if name in ("sin", "cos", "tan"):
            s, c = sincos(angle_to_rad(x, angle))
            if name == "sin": return s
            if name == "cos": return c
            if not c: raise CalcError("Invalid input")
            return checked(s / c)
        if name in ("asin", "acos"):
            if abs(x) > 1: raise CalcError("Invalid input")
            a = (PI / 2 if x >= 0 else -PI / 2) if abs(x) == 1 else atan(x / (1 - x*x).sqrt())
            return rad_to_angle(a if name == "asin" else PI / 2 - a, angle)
        if name == "atan": return rad_to_angle(atan(x), angle)
        if name in ("sinh", "cosh", "tanh"):
            if name == "tanh" and abs(x) > 100: return D(-1 if x < 0 else 1)
            a, b = x.exp(), (-x).exp()
            return checked((a-b)/2 if name == "sinh" else (a+b)/2 if name == "cosh" else (a-b)/(a+b))
        if name == "asinh":
            return (1 if x >= 0 else -1) * (abs(x) + (x*x + 1).sqrt()).ln()
        if name == "acosh":
            if x < 1: raise CalcError("Invalid input")
            return (x + (x*x - 1).sqrt()).ln()
        if name == "atanh":
            if abs(x) >= 1: raise CalcError("Invalid input")
            return ((1+x)/(1-x)).ln()/2
        if name == "dms":
            sign = -1 if x < 0 else 1
            y = abs(x); degrees = D(int(y)); minutes = D(int((y-degrees)*60))
            seconds = ((y-degrees)*60-minutes)*60
            return sign * (degrees + minutes/100 + seconds/10000)
        if name == "degrees":
            sign = -1 if x < 0 else 1
            y = abs(x); degrees = D(int(y)); minutes = D(int((y-degrees)*100))
            seconds = ((y-degrees)*100-minutes)*100
            if minutes >= 60 or seconds >= 60: raise CalcError("Invalid DMS value")
            return sign * (degrees + minutes/60 + seconds/3600)
        raise CalcError("Unknown function")
    except DecimalException as exc:
        raise CalcError("Overflow or invalid input") from exc


def binary(op: str, a: Decimal, b: Decimal) -> Decimal:
    try:
        if op == "+": return checked(a+b)
        if op == "-": return checked(a-b)
        if op == "*": return checked(a*b)
        if op == "/":
            if not b: raise CalcError("Cannot divide by zero")
            return checked(a/b)
        if op == "mod":
            if not b: raise CalcError("Cannot divide by zero")
            return checked(a % b)
        if op == "^": return power(a, b)
        if op == "root": return root(a, b)
        if op == "logbase":
            if a <= 0 or b <= 0 or b == 1: raise CalcError("Invalid input")
            return a.ln()/b.ln()
        raise CalcError("Unknown operation")
    except DecimalException as exc:
        raise CalcError("Overflow or invalid input") from exc


# precedence values also used by the calculator's button-driven expression evaluator
PRECEDENCE = {"or": 1, "xor": 2, "and": 3, "lsh": 4, "rsh": 4,
              "+": 5, "-": 5, "*": 6, "/": 6, "mod": 6,
              "^": 7, "root": 7, "logbase": 7}
TOKEN = re.compile(r"\s*(?:(\d+(?:\.\d*)?|\.\d+)([eE][+-]?\d+)?|([A-Za-z_]+)|(.))")
FUNCTIONS = {"sqrt": "sqrt", "sin": "sin", "cos": "cos", "tan": "tan",
             "asin": "asin", "acos": "acos", "atan": "atan", "sinh": "sinh",
             "cosh": "cosh", "tanh": "tanh", "asinh": "asinh", "acosh": "acosh",
             "atanh": "atanh", "ln": "ln", "log": "log", "exp": "exp",
             "abs": "abs", "int": "int", "frac": "frac", "fact": "factorial",
             "cbrt": "cuberoot", "dms": "dms", "degrees": "degrees",
             "square": "square", "sqr": "square", "cube": "cube", "pow10": "pow10",
             "reciprocal": "reciprocal", "neg": "neg"}


class ExpressionParser:
    """Pratt parser. Input is data only; Python names/calls are never executed."""
    def __init__(self, text: str, angle: str = "Degrees", immediate: bool = False):
        text = text.strip().replace("×", "*").replace("÷", "/").replace("−", "-").replace("π", "pi")
        if not text or len(text) > MAX_INPUT:
            raise CalcError("Empty or too long expression")
        self.tokens: list[str] = []
        for match in TOKEN.finditer(text):
            n, exponent, word, char = match.groups()
            self.tokens.append((n + (exponent or "")) if n else (word or char).lower())
        if len(self.tokens) > 512:
            raise CalcError("Expression is too long")
        self.pos = 0
        self.depth = 0
        self.angle = angle
        self.immediate = immediate

    def peek(self) -> str:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else ""

    def pop(self) -> str:
        token = self.peek()
        if not token: raise CalcError("Incomplete expression")
        self.pos += 1
        return token

    def parse(self) -> Decimal:
        value = self.expression(0)
        if self.peek(): raise CalcError("Invalid expression")
        return checked(value)

    def expression(self, minimum: int) -> Decimal:
        self.depth += 1
        if self.depth > 80: raise CalcError("Expression is too deeply nested")
        token = self.pop()
        if token in ("+", "-"):
            value = self.expression(7)
            if token == "-": value = -value
        elif token == "(":
            value = self.expression(0)
            if self.pop() != ")": raise CalcError("Missing closing parenthesis")
        elif token in ("pi", "e"):
            value = PI if token == "pi" else E
        elif token in FUNCTIONS:
            if self.pop() != "(": raise CalcError("Use parentheses for functions")
            value = self.expression(0)
            if self.pop() != ")": raise CalcError("Missing closing parenthesis")
            value = unary(FUNCTIONS[token], value, self.angle)
        else:
            value = number(token)
        while True:
            op = self.peek()
            if op == "!":
                self.pop(); value = factorial(value); continue
            if op == "%":
                self.pop(); value /= 100; continue
            prec = (5 if self.immediate and op in PRECEDENCE else PRECEDENCE.get(op, -1))
            if prec < minimum: break
            self.pop()
            rhs = self.expression(prec if op == "^" and not self.immediate else prec+1)
            value = binary(op, value, rhs)
        self.depth -= 1
        return value


def evaluate(text: str, angle: str = "Degrees", immediate: bool = False) -> Decimal:
    try:
        return ExpressionParser(text, angle, immediate).parse()
    except (DecimalException, OverflowError, RecursionError) as exc:
        raise CalcError("Overflow or invalid expression") from exc
