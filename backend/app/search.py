"""Small, dependency-free search: BM25 shortlist, then a confidence score Marshie can trust.

Runs on a Raspberry Pi (or a Vercel function) in a few milliseconds for thousands of entries.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher

STOPWORDS = set("""
a an the and or but if then so of to in on at by for with from into onto up down out over about
is are was were be been being am do does did done doing have has had having
i me my mine we us our you your yours he she it its they them their this that these those there here
what whats who whom whose where when why how which
can could would should will shall may might must
please tell explain describe say know give show let lets just really very also too
as than not no yes ok okay hey marshie
""".split())

_word = re.compile(r"[a-z0-9]+")


def stem(word: str) -> str:
    """Very light stemmer, then truncation so independ/independence/independent all agree."""
    w = word
    if len(w) > 4 and w.endswith("ies"):
        w = w[:-3] + "y"
    elif len(w) > 4 and w.endswith(("sses", "xes", "zes", "ches", "shes")):
        w = w[:-2]
    elif len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us", "is")):
        w = w[:-1]
    for suffix in ("ing", "ed", "ly"):
        if len(w) > len(suffix) + 3 and w.endswith(suffix):
            w = w[: -len(suffix)]
            break
    return w[:7]


_possessive = re.compile(r"'s\b")


def _straight(text: str) -> str:
    """Phones and tablets type curly apostrophes; treat them like the plain one."""
    return text.lower().replace("’", "'").replace("‘", "'").replace("`", "'")


def tokens(text: str, keep_stop: bool = False) -> list[str]:
    text = _possessive.sub("", _straight(text))          # "Esi's plant" -> "esi plant"
    words = _word.findall(text.replace("'", ""))
    return [stem(w) for w in words if keep_stop or w not in STOPWORDS]


def normalize(text: str) -> str:
    return " ".join(_word.findall(_straight(text).replace("'", "")))


class Index:
    def __init__(self, entries: list[dict], weights: dict | None = None):
        self.entries = entries
        self.weights = weights or {}
        self.n = len(entries)
        self.qk: list[set[str]] = []        # question + keyword tokens
        self.ans: list[set[str]] = []       # answer tokens
        self.norm_q: list[list[str]] = []   # normalized question + aliases (for exact/fuzzy match)
        self.length: list[int] = []
        self.passage: list[bool] = []       # text lifted from a document: the answer words are the point
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        self.exact: dict[str, list[int]] = defaultdict(list)   # normalized question -> entry numbers

        for i, e in enumerate(entries):
            q_tokens = tokens(" ".join([e["question"], *e.get("aliases", [])]))
            k_tokens = tokens(" ".join(e.get("keywords", [])) + " " + e.get("category", ""))
            a_tokens = tokens(e["answer"])
            self.qk.append(set(q_tokens) | set(k_tokens))
            self.ans.append(set(a_tokens))
            self.passage.append(e.get("kind") == "passage")
            self.norm_q.append([normalize(e["question"]), *[normalize(a) for a in e.get("aliases", [])]])
            for nq in set(self.norm_q[-1]):
                if nq:
                    self.exact[nq].append(i)
            bag = Counter()
            for t in q_tokens:
                bag[t] += 3
            for t in k_tokens:
                bag[t] += 3
            for t in a_tokens:
                bag[t] += 1
            self.length.append(sum(bag.values()))
            for t, tf in bag.items():
                self.postings[t].append((i, tf))
        self.avg_len = (sum(self.length) / self.n) if self.n else 1.0

    # ------------------------------------------------------------------ helpers
    def idf(self, term: str) -> float:
        df = len(self.postings.get(term, ()))
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def _adjust(self, entry: dict, conf: float) -> float:
        """Learning: thumbs-down lowers an entry, thumbs-up raises it, taught knowledge wins ties."""
        w = self.weights.get(entry["id"], {})
        conf *= 0.8 ** min(w.get("bad", 0), 4)
        conf *= 1 + 0.05 * min(w.get("good", 0), 4)
        if entry.get("via") not in ("seed", None):
            conf += 0.02
        return conf

    def search(self, query: str, k: int = 5) -> list[dict]:
        """Return up to k hits: {entry, confidence, bm25}. Best first."""
        q_norm = normalize(query)
        if not self.n or not q_norm:
            return []

        # Exact wording of a stored question or alias ("how are you", "capital of ghana") always wins,
        # even when every word is a stop word.
        if q_norm in self.exact:
            raw = [(self._adjust(self.entries[i], 1.0), i) for i in self.exact[q_norm]]
            raw.sort(key=lambda r: -r[0])
            return [{"entry": self.entries[i], "confidence": round(min(r, 1.0), 4), "raw": r, "bm25": 0.0}
                    for r, i in raw[:k]]

        q_tokens = list(dict.fromkeys(tokens(query)))
        if not q_tokens:
            return []

        scores: dict[int, float] = defaultdict(float)
        k1, b = 1.5, 0.75
        for t in q_tokens:
            idf = self.idf(t)
            for i, tf in self.postings.get(t, ()):
                denom = tf + k1 * (1 - b + b * self.length[i] / self.avg_len)
                scores[i] += idf * (tf * (k1 + 1)) / denom
        if not scores:
            return []

        shortlist = sorted(scores, key=scores.get, reverse=True)[:25]
        total_idf = sum(self.idf(t) for t in q_tokens) or 1.0
        hits = []
        for i in shortlist:
            e = self.entries[i]
            if self.passage[i]:
                # A passage has no real question, so words found anywhere in it count in full. A single common word is
                # not enough: the matched words must carry some weight (about two ordinary words, or one rare one).
                hit_weight = sum(self.idf(t) for t in q_tokens if t in self.ans[i] or t in self.qk[i])
                conf = self._adjust(e, 0.82 * (hit_weight / total_idf) * min(1.0, hit_weight / 4.0))
                hits.append({"entry": e, "confidence": round(min(conf, 1.0), 4), "raw": conf, "bm25": round(scores[i], 3)})
                continue
            # how much of the question is covered (question/keywords count fully, answer half)
            covered = sum(
                self.idf(t) * (1.0 if t in self.qk[i] else 0.5 if t in self.ans[i] else 0.0)
                for t in q_tokens
            )
            coverage = covered / total_idf
            # how much of the stored question the asker actually mentioned
            e_tokens = self.qk[i]
            rev = (
                sum(self.idf(t) for t in e_tokens if t in q_tokens)
                / (sum(self.idf(t) for t in e_tokens) or 1.0)
            )
            fuzzy = max(SequenceMatcher(None, q_norm, nq).ratio() for nq in self.norm_q[i])
            conf = 0.62 * coverage * (0.55 + 0.45 * rev) + 0.38 * fuzzy * min(1.0, coverage + 0.3)
            conf = self._adjust(e, conf)
            hits.append({"entry": e, "confidence": round(min(conf, 1.0), 4), "raw": conf, "bm25": round(scores[i], 3)})

        hits.sort(key=lambda h: (h["raw"], h["bm25"]), reverse=True)
        return hits[:k]
