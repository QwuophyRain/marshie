"""Small, dependency-free search: BM25 shortlist, then a confidence score Marshie can trust.

Runs on a Raspberry Pi (or a Vercel function) in a few milliseconds for thousands of entries.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher

from .i18n import fold

STOPWORDS = set("""
a an the and or but if then so of to in on at by for with from into onto up down out over about
is are was were be been being am do does did done doing have has had having
i me my mine we us our you your yours he she it its they them their this that these those there here
what whats who whom whose where when why how which
can could would should will shall may might must
please tell explain describe say know give show let lets just really very also too
as than not no yes ok okay hey marshie
""".split())

# Small word lists for French, Spanish and German (written without accents: everything is folded first).
STOPWORDS_BY_LANG = {
    "en": STOPWORDS,
    "fr": set("""
        le la les l un une des du de d au aux et ou mais si donc alors que qu qui quoi quel quelle quels quelles
        ou est sont etait etaient fut sera seront ete etre suis es sommes etes ont a ai as avons avez fait faire dans sur sous avec sans pour par en y
        ce cet cette ces c cest mon ma mes ton ta tes son sa ses notre nos votre vos leur leurs
        je j tu il elle on nous vous ils elles me m te t se s moi toi lui comment pourquoi quand combien
        dis dit explique expliques parle parles montre peux peut veux veut sais sait
        stp svp merci oui non ok salut marshie tout tous plus tres aussi ne pas n
    """.split()),
    "es": set("""
        el la los las lo un una unos unas de del al y e o u pero si que qu quien quienes cual cuales cuyo
        es son era eran fue fueron sera seran ser estar esta estan este esto estos estas ese eso esa esos esas aquel
        en con sin por para sobre entre desde hasta como cuando donde cuanto cuanta cuantos cuantas porque por
        mi mis tu tus su sus nuestro nuestra nuestros nuestras me te se nos le les yo tu el ella nosotros ellos ellas
        hay ha han he has hemos puedes puede quiero dime decir explica explicame cuentame muestrame
        por favor gracias si no vale hola marshie muy mas tambien ya
    """.split()),
    "de": set("""
        der die das den dem des ein eine einen einem einer eines und oder aber wenn dass ob als wie was wer wen wem
        wessen welche welcher welches welchen wo wann warum wieso weshalb wohin woher wieviel wieviele
        ist sind war waren gewesen sein bin bist seid hat habe hast haben hatte wird werden wurde
        in im ins an am auf aus bei mit nach von vom zu zum zur fur uber unter vor hinter neben zwischen durch gegen ohne um
        ich du er sie es wir ihr mich mir dich dir ihn ihm uns euch ihnen mein meine meinen meinem meiner dein deine
        mal kann kannst konnen magst mochte sag sage sagen erklar erklare erklaren zeig zeige erzahl erzahle
        bitte danke ja nein ok hallo marshie auch sehr noch nicht nur schon dies diese dieser dieses
    """.split()),
}

_word = re.compile(r"[a-z0-9]+")


def stem(word: str, lang: str = "en") -> str:
    """Very light stemmer, then truncation so independ/independence/independent all agree."""
    w = word
    if lang == "fr":
        if len(w) > 4 and w.endswith("aux"):
            w = w[:-3] + "al"
        elif len(w) > 3 and w.endswith(("s", "x")) and not w.endswith("ss"):
            w = w[:-1]
        if len(w) > 4 and w.endswith("e"):
            w = w[:-1]
        return w[:7]
    if lang == "es":
        if len(w) > 4 and w.endswith("es"):
            w = w[:-2]
        elif len(w) > 3 and w.endswith("s"):
            w = w[:-1]
        if len(w) > 4 and w[-1] in "aoe":
            w = w[:-1]
        return w[:7]
    if lang == "de":
        for suffix in ("ern", "en", "er", "es", "e", "n", "s"):
            if len(w) > len(suffix) + 3 and w.endswith(suffix):
                w = w[: -len(suffix)]
                break
        return w[:7]
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
    """Phones and tablets type curly apostrophes; treat them like the plain one. Accents are dropped (École = Ecole)."""
    return fold(text).replace("’", "'").replace("‘", "'").replace("`", "'")


def tokens(text: str, keep_stop: bool = False, lang: str = "en") -> list[str]:
    text = _straight(text)
    if lang == "en":
        text = _possessive.sub("", text)                    # "Esi's plant" -> "esi plant"
        words = _word.findall(text.replace("'", ""))
    else:
        words = _word.findall(text.replace("'", " "))      # "l'école" -> "l ecole"
    stop = STOPWORDS_BY_LANG.get(lang, STOPWORDS)
    return [stem(w, lang) for w in words if keep_stop or w not in stop]


def without_stopwords(text: str, lang: str) -> str:
    """The question with the little words of its own language taken out ("Qui était Kwame Nkrumah ?" -> "kwame nkrumah"),
    so it can be looked up in another language's knowledge, where only names and numbers can match."""
    t = _straight(text)
    words = _word.findall(t.replace("'", " "))
    stop = STOPWORDS_BY_LANG.get(lang, STOPWORDS)
    return " ".join(w for w in words if w not in stop)


def normalize(text: str, lang: str = "en") -> str:
    t = _straight(text)
    return " ".join(_word.findall(t.replace("'", "" if lang == "en" else " ")))


class Index:
    def __init__(self, entries: list[dict], weights: dict | None = None, lang: str = "en"):
        self.lang = lang
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
            q_tokens = tokens(" ".join([e["question"], *e.get("aliases", [])]), lang=lang)
            k_tokens = tokens(" ".join(e.get("keywords", [])) + " " + e.get("category", ""), lang=lang)
            a_tokens = tokens(e["answer"], lang=lang)
            self.qk.append(set(q_tokens) | set(k_tokens))
            self.ans.append(set(a_tokens))
            self.passage.append(e.get("kind") == "passage")
            self.norm_q.append([normalize(e["question"], lang), *[normalize(a, lang) for a in e.get("aliases", [])]])
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
        q_norm = normalize(query, self.lang)
        if not self.n or not q_norm:
            return []

        # Exact wording of a stored question or alias ("how are you", "capital of ghana") always wins,
        # even when every word is a stop word.
        if q_norm in self.exact:
            raw = [(self._adjust(self.entries[i], 1.0), i) for i in self.exact[q_norm]]
            raw.sort(key=lambda r: -r[0])
            return [{"entry": self.entries[i], "confidence": round(min(r, 1.0), 4), "raw": r, "bm25": 0.0}
                    for r, i in raw[:k]]

        q_tokens = list(dict.fromkeys(tokens(query, lang=self.lang)))
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
