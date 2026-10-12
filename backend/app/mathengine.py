"""Safe arithmetic for kids' questions: "what is 12 plus 7", "15% of 200", "square root of 144".

Never uses eval(). Expressions are parsed with `ast` and only whitelisted nodes are evaluated.
"""
from __future__ import annotations

import ast
import math
import operator as op
import random
import re

_BIN = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
        ast.Pow: op.pow, ast.Mod: op.mod, ast.FloorDiv: op.floordiv}
_UN = {ast.USub: op.neg, ast.UAdd: op.pos}
_FUNCS = {"sqrt": math.sqrt, "cbrt": lambda x: round(x ** (1 / 3), 12), "abs": abs}

NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    "hundred": 100, "thousand": 1000,
}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and (abs(right) > 12 or abs(left) > 1e6):
            raise ValueError("too big")
        return _BIN[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UN:
        return _UN[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS and len(node.args) == 1:
        return _FUNCS[node.func.id](_eval(node.args[0]))
    raise ValueError("unsupported")


def _words_to_numbers(text: str) -> str:
    """'twenty five' -> '25', 'three hundred and four' -> '304' (small, good enough for school)."""
    tokens = text.split()
    out: list[str] = []
    i = 0
    while i < len(tokens):
        if tokens[i] in NUMBER_WORDS:
            total, current = 0, 0
            while i < len(tokens) and (tokens[i] in NUMBER_WORDS or (tokens[i] == "and" and i + 1 < len(tokens) and tokens[i + 1] in NUMBER_WORDS and current)):
                w = tokens[i]
                if w == "and":
                    i += 1
                    continue
                v = NUMBER_WORDS[w]
                if v == 100:
                    current = (current or 1) * 100
                elif v == 1000:
                    total += (current or 1) * 1000
                    current = 0
                else:
                    current += v
                i += 1
            out.append(str(total + current))
        else:
            out.append(tokens[i])
            i += 1
    return " ".join(out)


_REPLACEMENTS = [
    (r"\bto the power of\b|\braised to\b|\bpower\b", " ** "),
    (r"\bsquared\b", " ** 2 "),
    (r"\bcubed\b", " ** 3 "),
    (r"\bmultiplied by\b|\btimes\b|\bmultiply\b|\bx\b|×", " * "),
    (r"\bdivided by\b|\bover\b|÷|\bdivide\b", " / "),
    (r"\bplus\b|\badd(?:ed to)?\b|\band\b(?=\s*\d)", " + "),
    (r"\bminus\b|\btake away\b|\bsubtract(?:ed by)?\b|\bless\b", " - "),
    (r"\bmod(?:ulo)?\b|\bremainder of\b", " % "),
]


def _format(value: float) -> str:
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError("bad")
        if abs(value - round(value)) < 1e-9:
            return f"{int(round(value)):,}"
        return f"{value:,.4f}".rstrip("0").rstrip(".")
    return f"{value:,}"


def solve(text: str) -> dict | None:
    """Return {"answer": str, "spoken": str, "expression": str} or None when this isn't a maths question."""
    t = text.lower().strip().rstrip("?!. ")
    t = re.sub(r"(?<=\d),(?=\d{3}\b)", "", t)                       # 1,000 -> 1000
    t = re.sub(r"^(?:please\s+)?(?:can you\s+|could you\s+)?(?:tell me\s+|work out\s+|calculate\s+|solve\s+|compute\s+|what(?:'s| is| are)\s+|whats\s+|how much is\s+|find\s+)+", "", t).strip()
    t = _words_to_numbers(t)

    m = re.fullmatch(r"([\d.]+)\s*%\s*of\s*([\d.]+)", t) or re.fullmatch(r"([\d.]+)\s*percent\s*of\s*([\d.]+)", t)
    if m:
        value = float(m.group(1)) / 100 * float(m.group(2))
        return _result(f"{m.group(1)}% of {m.group(2)}", value)

    m = re.fullmatch(r"(?:the\s+)?(square root|cube root)\s*(?:of)?\s*([\d.]+)", t)
    if m:
        n = float(m.group(2))
        value = math.sqrt(n) if m.group(1) == "square root" else n ** (1 / 3)
        if m.group(1) == "cube root":
            value = round(value, 10)
        return _result(f"{m.group(1)} of {m.group(2)}", value)

    m = re.fullmatch(r"(?:the\s+)?square\s*(?:of)?\s*([\d.]+)", t)
    if m:
        return _result(f"{m.group(1)} squared", float(m.group(1)) ** 2)

    m = re.fullmatch(r"(?:the\s+)?factorial\s*(?:of)?\s*(\d+)|(\d+)\s*factorial", t)
    if m:
        n = int(m.group(1) or m.group(2))
        if n > 20:
            return {"answer": "That one is too big for my little head!", "spoken": "That one is too big for my little head!", "expression": t}
        return _result(f"{n}!", math.factorial(n))

    m = re.fullmatch(r"([\d.]+)\s*/\s*([\d.]+)\s*(?:as a )?(?:decimal|fraction)", t)
    if m and float(m.group(2)):
        return _result(f"{m.group(1)}/{m.group(2)}", float(m.group(1)) / float(m.group(2)))

    expr = t
    for pattern, repl in _REPLACEMENTS:
        expr = re.sub(pattern, repl, expr)
    expr = expr.replace("^", "**").replace("(", " ( ").replace(")", " ) ")
    expr = re.sub(r"\bsqrt\b", "sqrt", expr)
    if not re.search(r"\d", expr) or re.search(r"[a-wyz]{2,}", re.sub(r"\bsqrt\b|\bcbrt\b|\babs\b", "", expr)):
        return None
    if not re.fullmatch(r"[\d\s.+\-*/%()a-z]*", expr) or not re.search(r"[+\-*/%]|sqrt|cbrt|abs", expr):
        return None
    try:
        value = _eval(ast.parse(re.sub(r"\s+", " ", expr).strip(), mode="eval"))
    except ZeroDivisionError:
        return {"answer": "We can't divide by zero! It breaks maths.", "spoken": "We can't divide by zero! It breaks maths.", "expression": t}
    except Exception:
        return None
    return _result(t, value)


def _result(expression: str, value: float) -> dict:
    pretty = _format(value)
    text = f"{expression} = {pretty}"
    return {"answer": text, "spoken": f"{expression.replace('*', 'times').replace('**', 'to the power of')} is {pretty}", "expression": expression, "value": value}


# ------------------------------------------------------------------ quiz
def new_question(level: int = 1) -> dict:
    """A random arithmetic question. level 1 = small add/sub, 2 = tables, 3 = bigger."""
    level = max(1, min(3, level))
    if level == 1:
        a, b = random.randint(1, 20), random.randint(1, 20)
        kind = random.choice("+-")
        if kind == "-" and b > a:
            a, b = b, a
    elif level == 2:
        a, b, kind = random.randint(2, 12), random.randint(2, 12), random.choice("*+-")
        if kind == "-" and b > a:
            a, b = b, a
    else:
        kind = random.choice("*+-/")
        if kind == "/":
            b = random.randint(2, 12)
            a = b * random.randint(2, 15)
        else:
            a, b = random.randint(11, 99), random.randint(3, 20)
    answer = {"+": a + b, "-": a - b, "*": a * b, "/": a // b if b else 0}[kind]
    word = {"+": "plus", "-": "minus", "*": "times", "/": "divided by"}[kind]
    return {"question": f"What is {a} {word} {b}?", "answer": str(answer)}
