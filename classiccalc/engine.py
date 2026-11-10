"""Button-driven calculator state, independent of the GUI toolkit."""
from __future__ import annotations

from decimal import Decimal
from typing import Union
from .mathlib import D, E, PI, CalcError, PRECEDENCE, binary, evaluate, format_number, number, unary

Value = Union[Decimal, int]
Token = Union[Decimal, int, str]
MODES = ("Standard", "Scientific", "Programmer", "Statistics")
OP_LABELS = {"*": "×", "/": "÷", "-": "−", "^": "^", "root": "yroot", "logbase": "logbase",
             "mod": "Mod", "and": "And", "or": "Or", "xor": "Xor", "lsh": "Lsh", "rsh": "Rsh"}
FUNCTION_LABELS = {"square": "sqr", "cube": "cube", "reciprocal": "1/", "factorial": "fact",
                   "cuberoot": "cuberoot", "pow10": "10^", "exp": "e^"}


class Calculator:
    def __init__(self, mode: str = "Standard") -> None:
        if mode not in MODES: raise CalcError("Unknown mode")
        self.mode = mode
        self.angle = "Degrees"
        self.radix = 10
        self.bits = 64
        self.scientific_notation = False
        self.grouping = False
        self.memory: Value = D(0)
        self.memory_set = False
        self.history: list[dict[str, str]] = []
        self.samples: list[Decimal] = []
        self.clear()

    @property
    def mask(self) -> int:
        return (1 << self.bits) - 1

    def normalize(self, value: int) -> int:
        value &= self.mask
        return value - (1 << self.bits) if value & (1 << (self.bits-1)) else value

    def encode(self, value: Value) -> str:
        if self.mode != "Programmer":
            return format_number(D(value), digits=60)
        v = self.normalize(int(value))
        if self.radix == 10: return str(v)
        return format(v & self.mask, {16: "X", 8: "o", 2: "b"}[self.radix])

    @property
    def value(self) -> Value:
        if self.mode == "Programmer":
            try: return self.normalize(int(self.entry or "0", self.radix))
            except ValueError as exc: raise CalcError("Invalid input") from exc
        text = self.entry
        if text.endswith(("e+", "e-", "e", "E+", "E-", "E")): text += "0"
        return number(text)

    @property
    def display(self) -> str:
        if self.error: return self.error
        if not self.new_entry: return self.entry
        if self.mode == "Programmer":
            s = self.encode(self.value)
            if self.grouping:
                if self.radix == 10: return format(int(s), ",d")
                group = 4 if self.radix in (16, 2) else 3
                pieces = []
                while s:
                    pieces.append(s[-group:]); s = s[:-group]
                return " ".join(reversed(pieces))
            return s
        return format_number(D(self.value), self.scientific_notation, self.grouping)

    @property
    def expression(self) -> str:
        if self.just_result: return self.result_expression
        text = " ".join(self.labels)
        if self.operand_ready and not self.closed_group and self.active_label:
            text += (" " if text else "") + self.active_label
        return text

    def clear(self) -> None:
        self.entry = "0"
        self.tokens: list[Token] = []
        self.labels: list[str] = []
        self.new_entry = True
        self.operand_ready = False
        self.closed_group = False
        self.just_result = False
        self.last_binary: tuple[str, Value] | None = None
        self.active_label: str | None = None
        self.result_expression = ""
        self.error = ""

    def set_error(self, message: str) -> None:
        self.error = message

    def _detach_group(self) -> None:
        if not self.closed_group: return
        depth = 0
        for i in range(len(self.tokens)-1, -1, -1):
            if self.tokens[i] == ")": depth += 1
            elif self.tokens[i] == "(":
                depth -= 1
                if depth == 0:
                    del self.tokens[i:]; del self.labels[i:]
                    break
        self.closed_group = False

    def clear_entry(self) -> None:
        if self.error:
            self.clear(); return
        self._detach_group()
        self.entry = "0"
        self.new_entry = True
        self.operand_ready = True
        self.active_label = None
        self.just_result = False

    def set_value(self, value: Value, label: str | None = None) -> None:
        self._detach_group()
        self.entry = self.encode(value)
        self.new_entry = True
        self.operand_ready = True
        self.just_result = False
        self.active_label = label
        self.error = ""

    def input_digit(self, digit: str) -> None:
        digit = digit.upper()
        allowed = "0123456789ABCDEF"[:self.radix] if self.mode == "Programmer" else "0123456789."
        if digit not in allowed: return
        if self.error or self.just_result: self.clear()
        if self.closed_group:
            self.operator("*")
        if self.new_entry:
            text = "0." if digit == "." else digit
        elif digit == ".":
            if "." in self.entry or "e" in self.entry.lower(): return
            text = self.entry + "."
        elif self.entry == "0":
            text = digit
        elif self.entry == "-0":
            text = "-" + digit
        else:
            text = self.entry + digit
        if self.mode == "Programmer":
            if abs(int(text, self.radix)) > self.mask: return
        else:
            mantissa, _, exponent = text.lower().partition("e")
            significant = mantissa.replace(".", "").lstrip("-+0")
            if len(significant) > 32 or len(exponent.lstrip("+-")) > 4: return
        self.entry = text
        self.new_entry = False
        self.operand_ready = True
        self.active_label = None

    def backspace(self) -> None:
        if self.error: self.clear(); return
        if self.new_entry: return
        self.entry = self.entry[:-1]
        if self.entry in ("", "-", "+"): self.entry = "0"
        self.active_label = None

    def sign(self) -> None:
        if self.error: return
        if not self.new_entry and "e" in self.entry.lower():
            a, b = self.entry.lower().split("e")
            self.entry = a + "e" + ("-" + b.lstrip("+-") if not b.startswith("-") else "+" + b[1:])
        elif self.mode == "Programmer":
            self.set_value(self.normalize(-int(self.value)))
        else:
            self._detach_group()
            self.entry = self.entry[1:] if self.entry.startswith("-") else "-" + self.entry
            if self.entry in ("0", "-0"): self.new_entry = False
            self.operand_ready = True
            self.just_result = False
            self.active_label = None

    def exponent(self) -> None:
        if self.mode == "Programmer" or self.error: return
        if self.just_result: self.just_result = False
        self._detach_group()
        if "e" not in self.entry.lower(): self.entry += "e+"
        self.new_entry = False
        self.operand_ready = True
        self.active_label = None

    def _append_value(self) -> None:
        self.tokens.append(self.value)
        self.labels.append(self.active_label or self.encode(self.value))

    def operator(self, op: str) -> None:
        if self.error: return
        if op not in PRECEDENCE: raise CalcError("Unknown operation")
        if self.just_result:
            self.tokens = []; self.labels = []; self.just_result = False
        if not self.closed_group:
            if not self.operand_ready and self.tokens and self.tokens[-1] in PRECEDENCE:
                self.tokens[-1] = op; self.labels[-1] = OP_LABELS.get(op, op)
                return
            self._append_value()
        if self.mode in ("Standard", "Statistics") and "(" not in self.tokens:
            value, _ = self._evaluate(self.tokens)
            self.entry = self.encode(value)
            self.tokens = [value]
            self.labels = [self.encode(value)]
        self.tokens.append(op)
        self.labels.append(OP_LABELS.get(op, op))
        self.new_entry = True
        self.operand_ready = False
        self.closed_group = False
        self.active_label = None
        self.last_binary = None

    def parenthesis(self, close: bool = False) -> None:
        if self.mode not in ("Scientific", "Programmer"): return
        if self.error: return
        if not close:
            if self.just_result: self.clear()
            if self.tokens.count("(") - self.tokens.count(")") >= 64:
                raise CalcError("Too many parentheses")
            if self.operand_ready or self.closed_group:
                self.operator("*")
            self.tokens.append("("); self.labels.append("(")
            self.entry = "0"
            self.new_entry = True
            self.operand_ready = False
            self.closed_group = False
        else:
            if self.tokens.count("(") <= self.tokens.count(")"): return
            if not self.closed_group: self._append_value()
            self.tokens.append(")"); self.labels.append(")")
            depth = 0
            for i in range(len(self.tokens)-1, -1, -1):
                if self.tokens[i] == ")": depth += 1
                elif self.tokens[i] == "(":
                    depth -= 1
                    if depth == 0:
                        value, _ = self._evaluate(self.tokens[i+1:-1])
                        self.entry = self.encode(value)
                        break
            self.closed_group = True
            self.operand_ready = True
            self.new_entry = True
        self.active_label = None

    def _binary(self, op: str, a: Value, b: Value) -> Value:
        if self.mode != "Programmer": return binary(op, D(a), D(b))
        a, b = int(a), int(b)
        if op == "+": result = a + b
        elif op == "-": result = a - b
        elif op == "*": result = a * b
        elif op in ("/", "mod"):
            if not b: raise CalcError("Cannot divide by zero")
            q = (abs(a) // abs(b)) * (-1 if (a < 0) != (b < 0) else 1)
            result = q if op == "/" else a - q * b
        elif op == "and": result = a & b
        elif op == "or": result = a | b
        elif op == "xor": result = a ^ b
        elif op in ("lsh", "rsh"):
            if b < 0: raise CalcError("Invalid shift count")
            # The logical shift count is limited to the current word width.
            if b >= self.bits: result = 0
            elif op == "lsh": result = (a & self.mask) << b
            else: result = (a & self.mask) >> b
        else: raise CalcError("Operation not available in Programmer mode")
        return self.normalize(result)

    def _evaluate(self, tokens: list[Token]) -> tuple[Value, tuple[str, Value] | None]:
        values: list[Value] = []
        ops: list[str] = []
        last: tuple[str, Value] | None = None
        def apply() -> None:
            nonlocal last
            if len(values) < 2: raise CalcError("Incomplete expression")
            op = ops.pop(); b = values.pop(); a = values.pop()
            values.append(self._binary(op, a, b)); last = (op, b)
        for token in tokens:
            if not isinstance(token, str): values.append(token)
            elif token == "(": ops.append(token)
            elif token == ")":
                while ops and ops[-1] != "(": apply()
                if not ops: raise CalcError("Unmatched parentheses")
                ops.pop()
            else:
                if token not in PRECEDENCE: raise CalcError("Invalid expression")
                p = PRECEDENCE[token]
                while ops and ops[-1] != "(" and (PRECEDENCE[ops[-1]] > p or (PRECEDENCE[ops[-1]] == p and token != "^")):
                    apply()
                ops.append(token)
        while ops:
            if ops[-1] == "(": raise CalcError("Unmatched parentheses")
            apply()
        if len(values) != 1: raise CalcError("Incomplete expression")
        return values[0], last

    def _record(self, expression: str, value: Value) -> None:
        self.history.append({"expression": expression, "result": self.encode(value),
                             "value": str(value), "mode": self.mode,
                             "radix": str(self.radix), "bits": str(self.bits)})
        del self.history[:-200]

    def equals(self) -> None:
        if self.error: return
        if self.just_result and self.last_binary:
            op, operand = self.last_binary
            expression = f"{self.encode(self.value)} {OP_LABELS.get(op, op)} {self.encode(operand)}"
            value = self._binary(op, self.value, operand)
        else:
            if not self.closed_group: self._append_value()
            difference = self.tokens.count("(") - self.tokens.count(")")
            self.tokens.extend([")"] * difference); self.labels.extend([")"] * difference)
            expression = " ".join(self.labels)
            value, self.last_binary = self._evaluate(self.tokens)
        self._record(expression, value)
        self.entry = self.encode(value)
        self.result_expression = expression + " ="
        self.tokens = []; self.labels = []
        self.new_entry = True
        self.operand_ready = True
        self.closed_group = False
        self.just_result = True
        self.active_label = None

    def function(self, name: str) -> None:
        if self.error: return
        value = self.value
        label = self.active_label or self.encode(value)
        if self.mode == "Programmer":
            raw = int(value) & self.mask
            if name == "not": result = self.normalize(~raw)
            elif name == "rol": result = self.normalize((raw << 1) | (raw >> (self.bits-1)))
            elif name == "ror": result = self.normalize((raw >> 1) | ((raw & 1) << (self.bits-1)))
            elif name == "int": result = int(value)
            else: raise CalcError("Operation not available in Programmer mode")
        else:
            result = unary(name, D(value), self.angle)
        self.set_value(result, f"{FUNCTION_LABELS.get(name, name)}({label})")

    def percent(self) -> None:
        if self.mode == "Programmer" or self.error: return
        x = D(self.value) / 100
        if self.tokens and self.tokens[-1] in ("+", "-"):
            # The accumulated left operand supplies the base for +/- percentage.
            left = self.tokens[:-1]
            unmatched = []
            for i, token in enumerate(left):
                if token == "(": unmatched.append(i)
                elif token == ")" and unmatched: unmatched.pop()
            if unmatched: left = left[unmatched[-1]+1:]
            base, _ = self._evaluate(left)
            x *= D(base)
        self.set_value(x)

    def constant(self, name: str) -> None:
        if self.mode == "Programmer": return
        self.set_value(PI if name == "pi" else E, "π" if name == "pi" else "e")

    def memory_action(self, action: str) -> None:
        if action == "MC":
            self.memory = D(0); self.memory_set = False; return
        if action == "MR": self.set_value(self.memory); return
        if self.error: return
        if action == "MS": self.memory = self.value
        elif action == "M+": self.memory = self._binary("+", self.memory, self.value)
        elif action == "M-": self.memory = self._binary("-", self.memory, self.value)
        else: raise CalcError("Unknown memory command")
        self.memory_set = True
        self.new_entry = True

    def set_mode(self, mode: str) -> None:
        if mode not in MODES: raise CalcError("Unknown mode")
        if mode == self.mode: return
        self.mode = mode
        self.clear()

    def set_radix(self, radix: int) -> None:
        if radix not in (2, 8, 10, 16): raise CalcError("Invalid number base")
        value = self.value
        self.radix = radix
        self.entry = self.encode(value)
        self.new_entry = True
        self._refresh_program_labels()

    def set_bits(self, bits: int) -> None:
        if bits not in (8, 16, 32, 64): raise CalcError("Invalid word size")
        value = self.value
        self.bits = bits
        self.entry = self.encode(value)
        self.tokens = [self.normalize(int(t)) if not isinstance(t, str) else t for t in self.tokens]
        self.new_entry = True
        self._refresh_program_labels()

    def _refresh_program_labels(self) -> None:
        if self.mode == "Programmer":
            self.labels = [OP_LABELS.get(t, t) if isinstance(t, str) else self.encode(t) for t in self.tokens]
            self.active_label = None

    def toggle_bit(self, bit: int) -> None:
        if self.mode != "Programmer" or not 0 <= bit < self.bits: return
        self.set_value(self.normalize(int(self.value) ^ (1 << bit)))

    def paste(self, text: str) -> None:
        text = text.strip().replace("\u00a0", "").replace("\u202f", "")
        if self.mode == "Programmer":
            text = text.replace(" ", "").replace(",", "")
            if len(text) > 256: raise CalcError("Input is too long")
            try:
                value = int(text, 0) if text.lower().startswith(("0x", "0o", "0b")) else int(text, self.radix)
            except ValueError as exc: raise CalcError("Paste an integer in the selected base") from exc
            if value < -(1 << (self.bits-1)) or value > self.mask:
                raise CalcError("Value exceeds selected word size")
            self.set_value(value)
        else:
            # Decimal comma is accepted when unambiguous; grouped numbers copy
            # in the calculator's own comma-thousands/point-decimal format.
            import re
            if re.fullmatch(r"[+-]?\d{1,3}(,\d{3})+(\.\d+)?", text):
                text = text.replace(",", "")
            elif "," in text and "." not in text:
                text = text.replace(",", ".")
            value = evaluate(text, self.angle, immediate=self.mode in ("Standard", "Statistics"))
            self.set_value(value, text if text != self.encode(value) else None)

    def add_sample(self) -> None:
        if self.error: return
        if len(self.samples) >= 10000: raise CalcError("Maximum of 10,000 samples")
        self.samples.append(D(self.value))
        self.new_entry = True
        self.just_result = True

    def statistic(self, name: str) -> None:
        if not self.samples: raise CalcError("No data")
        n = D(len(self.samples))
        total = sum(self.samples, D(0))
        mean = total / n
        sumsq = sum((x*x for x in self.samples), D(0))
        squared_deviations = sum(((x-mean)**2 for x in self.samples), D(0))
        if name == "mean": value = mean
        elif name == "mean_square": value = sumsq/n
        elif name == "sum": value = total
        elif name == "sum_square": value = sumsq
        elif name == "count": value = n
        elif name == "population_sd": value = (squared_deviations/n).sqrt()
        elif name == "sample_sd":
            if n < 2: raise CalcError("At least two values required")
            value = (squared_deviations/(n-1)).sqrt()
        else: raise CalcError("Unknown statistic")
        self.set_value(value, f"{name}(n={int(n)})")
