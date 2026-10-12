"""Answer simple questions about tables the students collected (averages, biggest, how many, one row...)."""
from __future__ import annotations

from .search import normalize, tokens

_AVG = {"average", "mean", "typical"}
_SUM = {"total", "sum", "altogether", "combined"}
_MAX = {"highest", "largest", "tallest", "biggest", "most", "maximum", "max", "longest", "heaviest",
        "oldest", "greatest", "fastest", "best", "top", "hottest", "warmest"}
_MIN = {"lowest", "smallest", "shortest", "least", "minimum", "min", "youngest", "lightest", "slowest",
        "worst", "coldest", "fewest", "coolest"}
_COUNT_PHRASES = ("how many", "number of", "count")
_GENERIC = {"data", "dataset", "table", "row", "sheet", "list", "survey", "result", "record", "count", "number", "many"}


def _num(value: str) -> float | None:
    try:
        return float(str(value).replace(",", "").replace("%", "").strip())
    except ValueError:
        return None


def _fmt(x: float) -> str:
    return str(int(round(x))) if abs(x - round(x)) < 1e-9 else f"{x:.2f}".rstrip("0").rstrip(".")


def _numeric_columns(ds: dict) -> list[int]:
    cols = []
    for i in range(len(ds["columns"])):
        vals = [r[i] for r in ds["rows"] if i < len(r) and r[i] != ""]
        if vals and sum(_num(v) is not None for v in vals) / len(vals) >= 0.7:
            cols.append(i)
    return cols


def _label_column(ds: dict, numeric: list[int]) -> int:
    return next((i for i in range(len(ds["columns"])) if i not in numeric), 0)


def _pick_dataset(q_tokens: set[str], datasets: list[dict]) -> tuple[dict | None, float]:
    best, best_score = None, 0.0
    for ds in datasets:
        head = set(tokens(ds["name"])) | set(tokens(" ".join(ds["columns"])))
        values = set()
        for row in ds["rows"][:300]:
            for cell in row:
                values.update(tokens(str(cell)))
        score = 3.0 * len(q_tokens & set(tokens(ds["name"]))) + 1.5 * len(q_tokens & head) + 1.0 * len(q_tokens & values)
        if score > best_score:
            best, best_score = ds, score
    return best, best_score


def _pick_column(q_tokens: set[str], ds: dict, candidates: list[int]) -> int | None:
    scored = [(len(q_tokens & set(tokens(ds["columns"][i]))), i) for i in candidates]
    scored.sort(reverse=True)
    if scored and scored[0][0] > 0:
        return scored[0][1]
    return candidates[0] if len(candidates) == 1 else None


def answer(question: str, datasets: list[dict]) -> dict | None:
    if not datasets:
        return None
    words = set(normalize(question).split())
    q_tokens = set(tokens(question))
    ds, score = _pick_dataset(q_tokens, datasets)
    if not ds or score < 2:
        return None

    numeric = _numeric_columns(ds)
    label_i = _label_column(ds, numeric)
    name = ds["name"]
    rows = ds["rows"]
    wants_avg, wants_sum = bool(words & _AVG), bool(words & _SUM)
    wants_max, wants_min = bool(words & _MAX), bool(words & _MIN)
    wants_count = any(p in normalize(question) for p in _COUNT_PHRASES)

    if wants_count:
        # "how many Ama" / "how many beans": count rows containing every non-generic query token
        filt = q_tokens - set(tokens(name)) - set(tokens(" ".join(ds["columns"]))) - _GENERIC
        matches = [r for r in rows if not filt or filt <= {t for c in r for t in tokens(str(c))}]
        return {"answer": f"I counted {len(matches)} {'rows' if len(matches) != 1 else 'row'} in the {name} data.", "dataset": name}

    if wants_avg or wants_sum or wants_max or wants_min:
        col = _pick_column(q_tokens, ds, numeric)
        if col is None:
            if not numeric:
                return None
            options = ", ".join(ds["columns"][i] for i in numeric)
            return {"answer": f"I have numbers about {options} in the {name} data. Which one do you mean?", "dataset": name}
        pairs = [(_num(r[col]), r[label_i] if label_i < len(r) else "") for r in rows if col < len(r) and _num(r[col]) is not None]
        if not pairs:
            return None
        values = [p[0] for p in pairs]
        cname = ds["columns"][col]
        if wants_avg:
            return {"answer": f"The average {cname} in the {name} data is {_fmt(sum(values) / len(values))}.", "dataset": name}
        if wants_sum:
            return {"answer": f"The total {cname} in the {name} data is {_fmt(sum(values))}.", "dataset": name}
        pick = max(pairs, key=lambda p: p[0]) if wants_max else min(pairs, key=lambda p: p[0])
        word = "highest" if wants_max else "lowest"
        who = f" That was {pick[1]}." if pick[1] else ""
        return {"answer": f"The {word} {cname} is {_fmt(pick[0])}.{who}", "dataset": name}

    # otherwise: look for matching rows ("How tall is Ama?", "tell me about Kofi's plant")
    filt = q_tokens - set(tokens(name)) - set(tokens(" ".join(ds["columns"]))) - _GENERIC
    scored = []
    for r in rows:
        cell_tokens = {t for c in r for t in tokens(str(c))}
        hit = len(filt & cell_tokens)
        if hit:
            scored.append((hit, r))
    if not scored:
        return None
    scored.sort(key=lambda s: -s[0])
    top = [r for h, r in scored if h == scored[0][0]][:3]
    col = _pick_column(q_tokens, ds, list(range(len(ds["columns"]))))
    parts = []
    for r in top:
        if col is not None and col < len(r) and col != label_i:
            parts.append(f"{r[label_i]}'s {ds['columns'][col]} is {r[col]}")
        else:
            parts.append(", ".join(f"{c} {v}" for c, v in zip(ds["columns"], r) if v != ""))
    return {"answer": f"In the {name} data: " + "; ".join(parts) + ".", "dataset": name}
