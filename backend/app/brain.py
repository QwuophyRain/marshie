"""Marshie's thinking: decides HOW to answer, learns from feedback, runs quizzes."""
from __future__ import annotations

import hashlib
import hmac
import random
import re
from difflib import SequenceMatcher

from . import config, datasets, i18n, llm, mathengine
from .safety import has_personal_contact, looks_inappropriate
from .search import Index, normalize, tokens, without_stopwords
from .store import Store


def fill(text: str) -> str:
    return text.replace("{name}", config.BOT_NAME).replace("{school}", config.SCHOOL_NAME)


_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\b")
_DOMAIN = re.compile(r"\b(?:https?://)?(?:www\.)?((?:[A-Za-z0-9-]+\.)+(?:com|org|net|edu|gov|gh|io|info|online|shop|school|app|dev|uk|fr))\b"
                     r"(?:/[^\s,;)]*)?", re.I)
_PHONE = re.compile(r"(?<![\w.])(\+\d[\d ()-]{7,}\d|0\d[\d ()-]{7,}\d)(?![\w])")
_SAY = (re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(config.SPEECH_FIXES, key=len, reverse=True)) + r")\b",
                   re.I) if config.SPEECH_FIXES else None)


def _say_phone(m: re.Match, plus: str = "plus") -> str:
    raw = m.group(1)
    groups = re.findall(r"\d+", raw)
    return (plus + " " if raw.startswith("+") else "") + ", ".join(" ".join(g) for g in groups)


def _say_address(m: re.Match, dot: str = "dot") -> str:
    return m.group(1).replace(".", f" {dot} ").replace("-", " ")


def _fix_name(m: re.Match) -> str:
    word = m.group(1).lower()
    return next(v for k, v in config.SPEECH_FIXES.items() if k.lower() == word)


def speakable(text: str, lang: str = "en") -> str:
    """Make written text pleasant to say out loud: phone numbers digit by digit, e-mail and web addresses
    with 'at' and 'dot', and names the browser voice gets wrong (Ecole Ronsard) spelled the way they sound.
    The little words ('times', 'minus', 'at'...) are said in the language of the text."""
    lang = i18n.clean(lang)
    w = i18n.speak_words(lang)
    t = _PHONE.sub(lambda m: _say_phone(m, w["plus"]), text)
    t = _EMAIL.sub(lambda m: m.group(0).replace("@", f" {w['at']} ").replace(".", f" {w['dot']} ").replace("-", " ").replace("_", " "), t)
    t = _DOMAIN.sub(lambda m: _say_address(m, w["dot"]), t)
    if _SAY and lang == "en":                       # the fixes are spellings for an English voice
        t = _SAY.sub(_fix_name, t)
    # sums first, while the * and - are still there
    t = re.sub(r"(?<=\d)\s*\*\*\s*(?=\d)", f" {w['power']} ", t)
    t = re.sub(r"(?<=\d)\s*[*×]\s*(?=\d)", f" {w['times']} ", t)
    t = re.sub(r"\b((?:1[0-9]|20)\d\d)\s*[-−–]\s*((?:1[0-9]|20)?\d\d)\b", rf"\1 {w['to']} \2", t)   # years: 1957-1960
    t = re.sub(r"(?<=\d)\s*[-−]\s*(?=\d)", f" {w['minus']} ", t)
    t = re.sub(r"[*_`#>]", "", t)
    t = re.sub(r"(?<=\d)\s*%", f" {w['percent']}", t)
    t = t.replace("&", f" {w['and']} ").replace("=", f" {w['is']} ")
    t = re.sub(r"(?<=\d)\s*\+\s*(?=\d)", f" {w['plus']} ", t)
    t = re.sub(r"(?<=\d)\s*x\s*(?=\d)", f" {w['times']} ", t)
    t = re.sub(r"(?<=\d)\s*/\s*(?=\d)", f" {w['over']} ", t)
    if lang == "en":
        t = re.sub(r"(?<=\d),(?=\d{3})", "", t)
    return re.sub(r"\s+", " ", t).strip()


class Brain:
    def __init__(self, store: Store):
        self.store = store
        self._indexes: dict[str, tuple[tuple, Index]] = {}

    # ------------------------------------------------------------------ index
    def greeting(self, lang: str = "en") -> dict:
        """The first thing Marshie says. Teachers can change the English words in the Teacher panel;
        French, Spanish and German have their own built-in greeting."""
        lang = i18n.clean(lang)
        if lang == "en":
            text = fill(self.store.get_setting("greeting") or config.GREETING)
        else:
            text = fill(i18n.GREETING[lang]).replace("{event}", config.EVENT_NAME)
        return {"text": text, "spoken": speakable(text, lang), "lang": lang}

    def index(self, lang: str = "en") -> Index:
        """One search index per language, rebuilt when the knowledge changes."""
        lang = i18n.clean(lang)
        s = self.store
        pend = s.state["entries"]
        sig = (len(s.seed), len(pend), pend[-1]["id"] if pend else "", sum(1 for e in pend if e.get("status") == "pending"))
        cached = self._indexes.get(lang)
        if cached is None or cached[0] != sig:
            entries = [e for e in s.all_entries() if (e.get("lang") or "en") == lang]
            cached = (sig, Index(entries, lang=lang))
            self._indexes[lang] = cached
        cached[1].weights = s.state["weights"]
        return cached[1]

    # ------------------------------------------------------------------ answering
    def ask(self, question: str, history: list[dict] | None = None, lang: str = "en") -> dict:
        self.store.refresh_if_stale()
        lang = i18n.clean(lang)
        q = " ".join((question or "").split())[:400]
        if not q:
            return self._reply(i18n.pick("empty", lang), "empty", lang=lang, mood="happy")
        if looks_inappropriate(q):
            return self._reply(i18n.pick("refuse", lang), "refused", lang=lang, mood="sad")
        if i18n.wants_quiz(q, lang):
            quiz = self.quiz_new(lang=lang)
            return self._reply(i18n.pick("quiz_start", lang).format(question=quiz["question"]), "quiz", lang=lang,
                               mood="happy", quiz=quiz)

        m = mathengine.solve(q, lang)
        if m:
            return self._reply(m["answer"], "math", lang=lang, mood="happy", spoken=speakable(m["spoken"], lang))

        hits = self.index(lang).search(q, k=6)
        best = hits[0] if hits else None
        conf = best["confidence"] if best else 0.0

        # A question a student typed in word for word beats a guess from a data table.
        if lang == "en" and conf < 0.9:
            ds = datasets.answer(q, self.store.state["datasets"])
            if ds:
                return self._reply(ds["answer"], "dataset", mood="happy", dataset=ds["dataset"])
        facts = [h["entry"]["answer"] for h in hits[:4] if h["confidence"] >= 0.15]

        if best and conf >= config.CONFIDENT:
            entry = best["entry"]
            same = [h for h in hits if h["raw"] >= best["raw"] - 0.005 and
                    normalize(h["entry"]["question"], lang) == normalize(entry["question"], lang)]
            if len(same) > 1:                                  # jokes, greetings: vary the reply
                entry = random.choice(same)["entry"]
            return self._reply(fill(entry["answer"]), "knowledge", entry=entry, confidence=conf, lang=lang,
                               mood=entry.get("mood") or "happy", media=self.store.media_public(entry.get("media")),
                               alternatives=self._alts(hits, entry["id"]))

        ai = llm.resolve(self.store.get_setting("ai"))
        if llm.provider(ai):
            if lang == "en":
                text = llm.ask(q, facts, history, ai)
                if text and not looks_inappropriate(text):             # never pass on an answer that is not child-safe
                    return self._reply(text, "llm", mood="happy", confidence=conf)
            else:
                got = self._ask_in(q, lang, history, ai, facts, conf)
                if got:
                    return got

        if lang != "en":
            # Offline, and nothing in her own language: a clear match in English (a name like Yaa Asantewaa, a number) is still
            # better than "I don't know". She says so in the child's language and reads the English part with an English voice.
            en = self.index("en").search(without_stopwords(q, lang), k=4)
            if en and en[0]["confidence"] >= config.CONFIDENT:
                entry = en[0]["entry"]
                intro = i18n.pick("english_only", lang)
                body = fill(entry["answer"])
                return self._reply(intro + body, "knowledge", entry=entry, confidence=en[0]["confidence"], lang=lang,
                                   mood=entry.get("mood") or "happy", media=self.store.media_public(entry.get("media")),
                                   parts=[{"text": intro.strip(), "lang": lang}, {"text": speakable(body, "en"), "lang": "en"}])

        if best and conf >= config.UNSURE:
            entry = best["entry"]
            return self._reply(i18n.pick("unsure_prefix", lang) + fill(entry["answer"]), "knowledge", entry=entry, lang=lang,
                               confidence=conf, mood="unsure", can_teach=True, media=self.store.media_public(entry.get("media")),
                               alternatives=self._alts(hits, entry["id"]))
        return self._reply(i18n.pick("unknown", lang), "unknown", lang=lang, mood="unsure", can_teach=True, confidence=conf)

    def _ask_in(self, q: str, lang: str, history, ai: dict, native_facts: list[str], conf: float) -> dict | None:
        """The paid AI helps with French, Spanish and German: it translates the child's question into English so Marshie's
        English knowledge can be searched, then translates the answer back. Two short AI calls at most."""
        q_en = llm.translate(q, "en", ai)
        if not q_en:                                              # the AI could not translate: let it answer directly
            text = llm.ask(q, native_facts, history, ai, lang=lang)
            return self._reply(text, "llm", lang=lang, mood="happy", confidence=conf) if text and not looks_inappropriate(text) else None
        q_en = q_en[:400]
        if looks_inappropriate(q_en):
            return self._reply(i18n.pick("refuse", lang), "refused", lang=lang, mood="sad")
        hits = self.index("en").search(q_en, k=6)
        best = hits[0] if hits else None
        conf_en = best["confidence"] if best else 0.0
        if conf_en < 0.9:
            ds = datasets.answer(q_en, self.store.state["datasets"])
            if ds:
                text = llm.translate(ds["answer"], lang, ai) or ds["answer"]
                return self._reply(text, "dataset", lang=lang if text != ds["answer"] else "en", mood="happy", dataset=ds["dataset"])
        if best and conf_en >= config.CONFIDENT:
            entry = best["entry"]
            text = llm.translate(fill(entry["answer"]), lang, ai)
            if text and not looks_inappropriate(text):
                return self._reply(text, "knowledge", entry=entry, confidence=conf_en, lang=lang,
                                   mood=entry.get("mood") or "happy", media=self.store.media_public(entry.get("media")))
        facts = [h["entry"]["answer"] for h in hits[:4] if h["confidence"] >= 0.15] + native_facts
        text = llm.ask(q, facts, history, ai, lang=lang)
        if text and not looks_inappropriate(text):
            return self._reply(text, "llm", lang=lang, mood="happy", confidence=max(conf, conf_en))
        return None

    @staticmethod
    def _alts(hits: list[dict], skip: str) -> list[dict]:
        return [{"question": h["entry"]["question"], "answer": fill(h["entry"]["answer"])}
                for h in hits if h["entry"]["id"] != skip and h["confidence"] >= 0.3][:2]

    @staticmethod
    def _reply(answer: str, source: str, *, entry: dict | None = None, confidence: float = 1.0, mood: str = "happy",
               can_teach: bool = False, spoken: str = "", lang: str = "en", **extra) -> dict:
        return {
            "answer": answer, "spoken": spoken or speakable(answer, lang), "source": source, "mood": mood, "lang": lang,
            "origin": entry.get("source", "") if entry else "",
            "entry_id": entry["id"] if entry else None,
            "category": entry["category"] if entry else None,
            "confidence": round(confidence, 3), "can_teach": can_teach, "media": [], **extra,
        }

    # ------------------------------------------------------------------ learning
    def teach(self, question: str, answer: str, category: str = "", keywords: str = "",
              taught_by: str = "", moderate: bool | None = None, lang: str = "en") -> dict:
        lang = i18n.clean(lang)
        question, answer = " ".join(question.split())[:300], " ".join(answer.split())[:1000]
        if len(question) < 3 or len(answer) < 2:
            return {"ok": False, "message": i18n.pick("teach_need", lang)}
        if looks_inappropriate(question + " " + answer):
            return {"ok": False, "message": i18n.pick("teach_kind", lang)}
        if has_personal_contact(answer):
            return {"ok": False, "message": i18n.pick("teach_private", lang)}
        pending = self.store.get_setting("moderate_teaching", False) if moderate is None else moderate
        added, _ = self.store.add_entries(
            [{"question": question, "answer": answer, "category": category or "Taught by students",
              "keywords": keywords, "source": "Taught in conversation", "lang": lang}],
            via="teach", added_by=taught_by, status="pending" if pending else "live")
        if not added:
            return {"ok": True, "message": i18n.pick("teach_known", lang), "pending": False, "added": 0}
        msg = i18n.pick("teach_pending", lang) if pending else i18n.pick("teach_done", lang)
        return {"ok": True, "message": msg, "pending": bool(pending), "added": added}

    def feedback(self, question: str, entry_id: str | None, good: bool, correction: str = "",
                 taught_by: str = "", lang: str = "en") -> dict:
        lang = i18n.clean(lang)
        self.store.rate(question, entry_id, good, correction)
        if good:
            return {"ok": True, "mood": "celebrate", "message": i18n.pick("good", lang)}
        if correction.strip():
            res = self.teach(question, correction, taught_by=taught_by, lang=lang)
            if res["ok"]:
                res["message"] = i18n.pick("corrected", lang) + res["message"]
                res["mood"] = "happy"
            else:
                res["mood"] = "sad"
            return res
        return {"ok": True, "mood": "sad", "ask_to_teach": True, "message": i18n.pick("bad_ask", lang)}

    # ------------------------------------------------------------------ quiz
    def _sign(self, question: str, answer: str) -> str:
        return hmac.new(config.SECRET_KEY.encode(), f"{question}|{normalize(answer)}".encode(), hashlib.sha256).hexdigest()[:24]

    def quiz_new(self, category: str = "", level: int = 1, lang: str = "en") -> dict:
        lang = i18n.clean(lang)
        pool = [e for e in self.store.all_entries()
                if e.get("short") and (e.get("lang") or "en") == lang and (not category or e["category"] == category)]
        if category.lower() in ("arithmetic", "maths", "math", "mathematics") or not pool or random.random() < 0.25:
            qa = mathengine.new_question(level, lang)
            return {"kind": "math", "question": qa["question"], "token": self._sign(qa["question"], qa["answer"])}
        entry = random.choice(pool)
        return {"kind": "knowledge", "question": fill(entry["question"]), "entry_id": entry["id"],
                "category": entry["category"]}

    def quiz_check(self, kind: str, response: str, question: str = "", token: str = "", entry_id: str = "",
                   lang: str = "en") -> dict:
        lang = i18n.clean(lang)
        if kind == "math":
            resp = mathengine._words_to_numbers(normalize(response, lang), lang)
            digits = re.sub(r"[^\d.\-]", "", resp.replace(" ", "")) or resp
            ok = hmac.compare_digest(self._sign(question, digits), token)
            return {"correct": ok, "answer": None if ok else "Not quite", "mood": "celebrate" if ok else "sad"}
        entry = self.store.find_entry(entry_id)
        if not entry:
            return {"correct": False, "answer": "", "mood": "sad"}
        el = entry.get("lang") or "en"                            # judge the answer in the language the question was in
        resp = mathengine._words_to_numbers(normalize(response, el), el)
        short = mathengine._words_to_numbers(normalize(entry["short"], el), el)
        want, got = set(tokens(short, keep_stop=True, lang=el)), set(tokens(resp, keep_stop=True, lang=el))
        ok = bool(want) and (want <= got or SequenceMatcher(None, short, resp).ratio() >= 0.85)
        return {"correct": ok, "answer": fill(entry["answer"]), "short": entry["short"],
                "mood": "celebrate" if ok else "sad"}
