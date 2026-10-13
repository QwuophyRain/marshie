"""Safe arithmetic for kids' questions: "what is 12 plus 7", "15% of 200", "square root of 144".

Never uses eval(). Expressions are parsed with `ast` and only whitelisted nodes are evaluated.
"""
from __future__ import annotations

import ast
import math
import operator as op
import random
import re

from . import i18n

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


_FR = {"zero": 0, "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7, "huit": 8, "neuf": 9,
       "dix": 10, "onze": 11, "douze": 12, "treize": 13, "quatorze": 14, "quinze": 15, "seize": 16, "vingt": 20, "vingts": 20,
       "trente": 30, "quarante": 40, "cinquante": 50, "soixante": 60, "cent": 100, "cents": 100, "mille": 1000}
_ES = {"cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8,
       "nueve": 9, "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16,
       "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20, "veintiuno": 21, "veintidos": 22, "veintitres": 23,
       "veinticuatro": 24, "veinticinco": 25, "veintiseis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
       "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90,
       "cien": 100, "ciento": 100, "doscientos": 200, "trescientos": 300, "cuatrocientos": 400, "quinientos": 500,
       "seiscientos": 600, "setecientos": 700, "ochocientos": 800, "novecientos": 900, "mil": 1000}
_DE = {"null": 0, "eins": 1, "ein": 1, "eine": 1, "zwei": 2, "drei": 3, "vier": 4, "funf": 5, "sechs": 6, "sieben": 7, "acht": 8,
       "neun": 9, "zehn": 10, "elf": 11, "zwolf": 12, "dreizehn": 13, "vierzehn": 14, "funfzehn": 15, "sechzehn": 16,
       "siebzehn": 17, "achtzehn": 18, "neunzehn": 19, "zwanzig": 20, "dreissig": 30, "vierzig": 40, "funfzig": 50,
       "sechzig": 60, "siebzig": 70, "achtzig": 80, "neunzig": 90, "hundert": 100, "tausend": 1000}
WORDS = {"en": NUMBER_WORDS, "fr": _FR, "es": _ES, "de": _DE}
AND = {"en": "and", "fr": "et", "es": "y", "de": "und"}


def _de_parts(w: str) -> list[str]:
    """'siebenundzwanzig' -> sieben, und, zwanzig;  'zweihundert' -> zwei, hundert."""
    if not w or w in _DE:
        return [w] if w else []
    for sep in ("tausend", "hundert", "und"):
        i = w.find(sep)
        if i >= 0:
            parts = _de_parts(w[:i]) + [sep] + _de_parts(w[i + len(sep):])
            if all(p in _DE or p == "und" for p in parts):
                return parts
    return [w]


def _words_to_numbers(text: str, lang: str = "en") -> str:
    """'twenty five' -> '25', 'three hundred and four' -> '304', 'vingt-deux' -> '22' (small, good enough for school)."""
    lang = i18n.clean(lang)
    words, conj = WORDS[lang], AND[lang]
    tokens = text.split()
    if lang == "de":
        tokens = [p for t in tokens for p in _de_parts(t)]
    out: list[str] = []
    i = 0
    while i < len(tokens):
        if tokens[i] in words:
            total, current = 0, 0
            while i < len(tokens) and (tokens[i] in words or (tokens[i] == conj and i + 1 < len(tokens) and tokens[i + 1] in words and current)):
                w = tokens[i]
                if w == conj:
                    i += 1
                    continue
                v = words[w]
                if v == 100:
                    current = (current or 1) * 100
                elif v == 1000:
                    total += (current or 1) * 1000
                    current = 0
                elif lang == "fr" and v == 20 and current == 4:     # quatre-vingt(s) = 80
                    current = 80
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

# The same, for French, Spanish and German. The text is already folded (no accents) when these run.
_REPLACEMENTS_BY_LANG = {
    "fr": [
        (r"\ba la puissance\b|\bpuissance\b|\beleve a\b", " ** "),
        (r"\bau carre\b", " ** 2 "),
        (r"\bau cube\b", " ** 3 "),
        (r"\bmultiplie par\b|\bfois\b|\bx\b|×", " * "),
        (r"\bdivise par\b|\bsur\b|÷", " / "),
        (r"\bplus\b|\bajoute a\b|\bet\b(?=\s*\d)", " + "),
        (r"\bmoins\b|\bretire\b|\benleve\b", " - "),
        (r"\bmodulo\b|\breste de\b", " % "),
    ],
    "es": [
        (r"\belevado a\b|\ba la potencia\b", " ** "),
        (r"\bal cuadrado\b", " ** 2 "),
        (r"\bal cubo\b", " ** 3 "),
        (r"\bmultiplicado por\b|\bveces\b|\bpor\b|\bx\b|×", " * "),
        (r"\bdividido entre\b|\bdividido por\b|\bentre\b|÷", " / "),
        (r"\bmas\b|\bsumado a\b|\by\b(?=\s*\d)", " + "),
        (r"\bmenos\b|\brestado\b", " - "),
        (r"\bmodulo\b|\bresto de\b", " % "),
    ],
    "de": [
        (r"\bhoch\b", " ** "),
        (r"\bzum quadrat\b|\bim quadrat\b", " ** 2 "),
        (r"\bmultipliziert mit\b|\bmal\b|\bx\b|×", " * "),
        (r"\bgeteilt durch\b|\bdividiert durch\b|\bdurch\b|÷", " / "),
        (r"\bplus\b|\bund\b(?=\s*\d)", " + "),
        (r"\bminus\b|\bweniger\b", " - "),
        (r"\bmodulo\b|\brest von\b", " % "),
    ],
}

_LEAD = {
    "en": r"^(?:please\s+)?(?:can you\s+|could you\s+)?(?:tell me\s+|work out\s+|calculate\s+|solve\s+|compute\s+|what(?:'s| is| are)\s+|whats\s+|how much is\s+|find\s+)+",
    "fr": r"^(?:s il te plait\s+)?(?:peux tu\s+|pourrais tu\s+)?(?:me dire\s+|dis moi\s+|calcule\s+|resous\s+|combien (?:font|fait|vaut|valent|est|sont)\s+|"
          r"quel est le resultat de\s+|quel est\s+|quelle est\s+|c est quoi\s+|qu est ce que\s+|ca fait combien\s+)+",
    "es": r"^(?:por favor\s+)?(?:puedes\s+|podrias\s+)?(?:decirme\s+|dime\s+|calcula\s+|resuelve\s+|cuanto (?:es|son|da|hacen|vale|valen)\s+|"
          r"cual es el resultado de\s+|cual es\s+|que es\s+|cuanto\s+)+",
    "de": r"^(?:bitte\s+)?(?:kannst du\s+)?(?:mir sagen\s+|sag mir\s+|berechne\s+|rechne\s+|loese\s+|wie viel (?:ist|sind|macht|ergibt)\s+|"
          r"wieviel (?:ist|sind|macht|ergibt)\s+|was ist\s+|was sind\s+|was macht\s+)+",
}
_OF = {"en": "of", "fr": "de", "es": "de", "de": "von"}
_SQRT = {"en": r"square root", "fr": r"racine carree", "es": r"raiz cuadrada", "de": r"(?:quadrat)?wurzel"}
_CBRT = {"en": r"cube root", "fr": r"racine cubique", "es": r"raiz cubica", "de": r"kubikwurzel"}
_PERCENT = {"en": r"percent", "fr": r"pour cent", "es": r"por ciento", "de": r"prozent"}
_SQUARE = {"en": r"square", "fr": r"carre", "es": r"cuadrado", "de": r"quadrat"}
_FACT = {"en": r"factorial", "fr": r"factorielle", "es": r"factorial", "de": r"fakultat"}
_DE_AUS = r"(?:aus|von)"


def _format(value: float, lang: str = "en") -> str:
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError("bad")
        if abs(value - round(value)) < 1e-9:
            text = f"{int(round(value)):,}"
        else:
            text = f"{value:,.4f}".rstrip("0").rstrip(".")
    else:
        text = f"{value:,}"
    if lang == "en":
        return text
    thousands = {"fr": "\u202f", "es": ".", "de": "."}[lang]               # 1 000 / 1.000 and a decimal comma
    return text.replace(",", "\x00").replace(".", ",").replace("\x00", thousands)


def solve(text: str, lang: str = "en") -> dict | None:
    """Return {"answer": str, "spoken": str, "expression": str} or None when this isn't a maths question."""
    lang = i18n.clean(lang)
    t = text.lower().strip().rstrip("?!. ")
    if lang != "en":
        t = i18n.fold(t).replace("\u2019", " ").replace("'", " ").replace("\u00bf", "").replace("\u00a1", "").rstrip("?!. ")
        t = re.sub(r"(?<=\d),(?=\d)", ".", t)                       # 2,5 -> 2.5
        t = re.sub(r"(?<=\d)\s(?=\d{3}\b)", "", t)                    # 1 000 -> 1000
        t = re.sub(r"\s+", " ", t).strip()
    else:
        t = re.sub(r"(?<=\d),(?=\d{3}\b)", "", t)                       # 1,000 -> 1000
    t = re.sub(r"(?<=[a-z])-(?=[a-z])", " ", t)                       # vingt-deux, twenty-five
    t = re.sub(_LEAD[lang], "", t).strip()
    t = _words_to_numbers(t, lang)
    of, num = _OF[lang], r"([\d.]+)"

    m = (re.fullmatch(rf"{num}\s*%\s*{of}\s*{num}", t) or re.fullmatch(rf"{num}\s*{_PERCENT[lang]}\s*{of}\s*{num}", t)
         or re.fullmatch(rf"(?:le |el |die |der |das )?{num}\s*%\s*{of}\s*{num}", t))
    if m:
        value = float(m.group(1)) / 100 * float(m.group(2))
        return _result(f"{m.group(1)}% {of} {m.group(2)}", value, lang,
                       spoken=f"{m.group(1)} {i18n.MATH[lang]['percent']} {i18n.MATH[lang]['of']} {m.group(2)}")

    m = re.fullmatch(rf"(?:the |la |le |el |die |der )?({_SQRT[lang]}|{_CBRT[lang]})\s*(?:{of if lang != 'de' else _DE_AUS})?\s*{num}", t)
    if m:
        n = float(m.group(2))
        is_cube = bool(re.fullmatch(_CBRT[lang], m.group(1)))
        value = round(n ** (1 / 3), 10) if is_cube else math.sqrt(n)
        key = "cbrt" if is_cube else "sqrt"
        return _result(f"{'\u221b' if is_cube else '\u221a'}{m.group(2)}" if lang != "en" else f"{m.group(1)} of {m.group(2)}", value, lang,
                       spoken=f"{i18n.MATH[lang][key]} {i18n.MATH[lang]['of']} {m.group(2)}")

    m = re.fullmatch(rf"(?:the |le |el |das |der )?{_SQUARE[lang]}\s*(?:{of})?\s*{num}", t)
    if m:
        return _result(f"{m.group(1)}\u00b2", float(m.group(1)) ** 2, lang, spoken=f"{m.group(1)} {i18n.MATH[lang]['squared']}")

    m = re.fullmatch(rf"(?:the |la |)?{_FACT[lang]}\s*(?:{of})?\s*(\d+)|(\d+)\s*{_FACT[lang]}", t)
    if m:
        n = int(m.group(1) or m.group(2))
        if n > 20:
            msg = i18n.pick("too_big", lang)
            return {"answer": msg, "spoken": msg, "expression": t}
        return _result(f"{n}!", math.factorial(n), lang)

    m = re.fullmatch(r"([\d.]+)\s*/\s*([\d.]+)\s*(?:as a )?(?:decimal|fraction)", t)
    if m and float(m.group(2)):
        return _result(f"{m.group(1)}/{m.group(2)}", float(m.group(1)) / float(m.group(2)), lang)

    expr = t
    for pattern, repl in (_REPLACEMENTS if lang == "en" else _REPLACEMENTS_BY_LANG[lang] + _REPLACEMENTS[-0:0]):
        expr = re.sub(pattern, repl, expr)
    if lang != "en":                                   # symbols people type in any language
        expr = re.sub(r"\bplus\b", " + ", expr)
    expr = expr.replace("^", "**").replace("(", " ( ").replace(")", " ) ")
    expr = re.sub(r"\bsqrt\b", "sqrt", expr)
    if not re.search(r"\d", expr) or re.search(r"[a-wyz]{2,}", re.sub(r"\bsqrt\b|\bcbrt\b|\babs\b", "", expr)):
        return None
    if not re.fullmatch(r"[\d\s.+\-*/%()a-z]*", expr) or not re.search(r"[+\-*/%]|sqrt|cbrt|abs", expr):
        return None
    try:
        value = _eval(ast.parse(re.sub(r"\s+", " ", expr).strip(), mode="eval"))
    except ZeroDivisionError:
        msg = i18n.pick("divide_zero", lang)
        return {"answer": msg, "spoken": msg, "expression": t}
    except Exception:
        return None
    if lang == "en":
        return _result(t, value, lang)
    shown = re.sub(r"\s+", " ", expr).strip()
    shown = shown.replace("**", "^").replace("*", "\u00d7").replace("/", "\u00f7")
    shown = re.sub(r"(?<=\d)\s*-\s*(?=\d)", " \u2212 ", shown)
    return _result(shown, value, lang, spoken=_say_expression(re.sub(r"\s+", " ", expr).strip(), lang))


def _say_expression(expression: str, lang: str) -> str:
    """'12 * 7' -> '12 times 7' (or fois, por, mal) so a voice can read a typed sum."""
    w = i18n.MATH[lang]
    out = expression.replace("**", f" {w['pow']} ").replace("*", f" {w['*']} ").replace("\u00d7", f" {w['*']} ")
    out = re.sub(r"(?<=\d)\s*/\s*(?=\d)", f" {w['/']} ", out)
    out = re.sub(r"(?<=\d)\s*\+\s*(?=\d)", f" {w['+']} ", out)
    out = re.sub(r"(?<=\d)\s*-\s*(?=\d)", f" {w['-']} ", out)
    return re.sub(r"\s+", " ", out).strip()


def _result(expression: str, value: float, lang: str = "en", spoken: str = "") -> dict:
    pretty = _format(value, lang)
    said = spoken or _say_expression(expression, lang)
    if lang != "en":
        expression = re.sub(r"(?<=\d)\.(?=\d)", ",", expression)             # 2.5 -> 2,5
        said = re.sub(r"(?<=\d)\.(?=\d)", ",", said)
    text = f"{expression} = {pretty}"
    return {"answer": text, "spoken": f"{said} {i18n.MATH[lang]['is']} {pretty}",
            "expression": expression, "value": value}


# ------------------------------------------------------------------ quiz
def new_question(level: int = 1, lang: str = "en") -> dict:
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
    words = i18n.MATH[i18n.clean(lang)]
    return {"question": words["ask"].format(a=a, op=words[kind], b=b), "answer": str(answer)}
