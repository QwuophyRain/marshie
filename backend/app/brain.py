"""Marshie's thinking: decides HOW to answer, learns from feedback, runs quizzes."""
from __future__ import annotations

import hashlib
import hmac
import random
import re
from difflib import SequenceMatcher

from . import config, datasets, llm, mathengine
from .safety import has_personal_contact, looks_inappropriate
from .search import Index, normalize, tokens
from .store import Store

UNKNOWN = [
    "Hmm, I don't know that one yet! Can you teach me the answer?",
    "Oh! That's new to me. Will you teach me so I can learn it?",
    "I haven't learned that yet. Please teach me, I love learning!",
]
UNSURE_PREFIX = [
    "I'm not totally sure, but I think this might help: ",
    "Hmm, maybe this? ",
    "I found something close: ",
]
REFUSE = ["Let's keep our words kind and friendly. Ask me about school, science or Ghana instead!"]
EMPTY = ["I'm listening! Ask me anything, or say 'quiz me'."]
QUIZ_WORDS = re.compile(r"^(?:please\s+)?(?:quiz me|test me|ask me (?:a|some) questions?|let'?s play|play (?:a )?(?:game|quiz)|give me a quiz)\b", re.I)


def fill(text: str) -> str:
    return text.replace("{name}", config.BOT_NAME).replace("{school}", config.SCHOOL_NAME)


_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\b")
_DOMAIN = re.compile(r"\b(?:https?://)?(?:www\.)?((?:[A-Za-z0-9-]+\.)+(?:com|org|net|edu|gov|gh|io|info|online|shop|school|app|dev|uk|fr))\b"
                     r"(?:/[^\s,;)]*)?", re.I)
_PHONE = re.compile(r"(?<![\w.])(\+\d[\d ()-]{7,}\d|0\d[\d ()-]{7,}\d)(?![\w])")
_SAY = (re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(config.SPEECH_FIXES, key=len, reverse=True)) + r")\b",
                   re.I) if config.SPEECH_FIXES else None)


def _say_phone(m: re.Match) -> str:
    raw = m.group(1)
    groups = re.findall(r"\d+", raw)
    return ("plus " if raw.startswith("+") else "") + ", ".join(" ".join(g) for g in groups)


def _say_address(m: re.Match) -> str:
    return m.group(1).replace(".", " dot ").replace("-", " ")


def _fix_name(m: re.Match) -> str:
    word = m.group(1).lower()
    return next(v for k, v in config.SPEECH_FIXES.items() if k.lower() == word)


def speakable(text: str) -> str:
    """Make written text pleasant to say out loud: phone numbers digit by digit, e-mail and web addresses
    with 'at' and 'dot', and names the browser voice gets wrong (Ecole Ronsard) spelled the way they sound."""
    t = _PHONE.sub(_say_phone, text)
    t = _EMAIL.sub(lambda m: m.group(0).replace("@", " at ").replace(".", " dot ").replace("-", " ").replace("_", " "), t)
    t = _DOMAIN.sub(_say_address, t)
    if _SAY:
        t = _SAY.sub(_fix_name, t)
    # sums first, while the * and - are still there
    t = re.sub(r"(?<=\d)\s*\*\*\s*(?=\d)", " to the power of ", t)
    t = re.sub(r"(?<=\d)\s*[*×]\s*(?=\d)", " times ", t)
    t = re.sub(r"\b((?:1[0-9]|20)\d\d)\s*[-−–]\s*((?:1[0-9]|20)?\d\d)\b", r"\1 to \2", t)   # years: 1957-1960
    t = re.sub(r"(?<=\d)\s*[-−]\s*(?=\d)", " minus ", t)
    t = re.sub(r"[*_`#>]", "", t)
    t = re.sub(r"(?<=\d)\s*%", " percent", t)
    t = t.replace("&", " and ").replace("=", " is ")
    t = re.sub(r"(?<=\d)\s*\+\s*(?=\d)", " plus ", t)
    t = re.sub(r"(?<=\d)\s*x\s*(?=\d)", " times ", t)
    t = re.sub(r"(?<=\d)\s*/\s*(?=\d)", " divided by ", t)
    t = re.sub(r"(?<=\d),(?=\d{3})", "", t)
    return re.sub(r"\s+", " ", t).strip()


class Brain:
    def __init__(self, store: Store):
        self.store = store
        self._index: Index | None = None
        self._sig: tuple = ()

    # ------------------------------------------------------------------ index
    def greeting(self) -> dict:
        """The first thing Marshie says. Teachers can change the words in the Teacher panel."""
        text = fill(self.store.get_setting("greeting") or config.GREETING)
        return {"text": text, "spoken": speakable(text)}

    def index(self) -> Index:
        s = self.store
        pend = s.state["entries"]
        sig = (len(s.seed), len(pend), pend[-1]["id"] if pend else "", sum(1 for e in pend if e.get("status") == "pending"))
        if self._index is None or sig != self._sig:
            self._index = Index(s.all_entries())
            self._sig = sig
        self._index.weights = s.state["weights"]
        return self._index

    # ------------------------------------------------------------------ answering
    def ask(self, question: str, history: list[dict] | None = None) -> dict:
        self.store.refresh_if_stale()
        q = " ".join((question or "").split())[:400]
        if not q:
            return self._reply(random.choice(EMPTY), "empty", mood="happy")
        if looks_inappropriate(q):
            return self._reply(random.choice(REFUSE), "refused", mood="sad")
        if QUIZ_WORDS.search(q):
            quiz = self.quiz_new()
            return self._reply(f"Yay, let's play! {quiz['question']}", "quiz", mood="happy", quiz=quiz)

        m = mathengine.solve(q)
        if m:
            return self._reply(m["answer"], "math", mood="happy", spoken=speakable(m["spoken"]))

        hits = self.index().search(q, k=6)
        best = hits[0] if hits else None
        conf = best["confidence"] if best else 0.0

        # A question a student typed in word for word beats a guess from a data table.
        if conf < 0.9:
            ds = datasets.answer(q, self.store.state["datasets"])
            if ds:
                return self._reply(ds["answer"], "dataset", mood="happy", dataset=ds["dataset"])
        facts = [h["entry"]["answer"] for h in hits[:4] if h["confidence"] >= 0.15]

        if best and conf >= config.CONFIDENT:
            entry = best["entry"]
            same = [h for h in hits if h["raw"] >= best["raw"] - 0.005 and
                    normalize(h["entry"]["question"]) == normalize(entry["question"])]
            if len(same) > 1:                                  # jokes, greetings: vary the reply
                entry = random.choice(same)["entry"]
            return self._reply(fill(entry["answer"]), "knowledge", entry=entry, confidence=conf,
                               mood=entry.get("mood") or "happy", media=self.store.media_public(entry.get("media")),
                               alternatives=self._alts(hits, entry["id"]))

        ai = llm.resolve(self.store.get_setting("ai"))
        if llm.provider(ai):
            text = llm.ask(q, facts, history, ai)
            if text and not looks_inappropriate(text):             # never pass on an answer that is not child-safe
                return self._reply(text, "llm", mood="happy", confidence=conf)

        if best and conf >= config.UNSURE:
            entry = best["entry"]
            return self._reply(random.choice(UNSURE_PREFIX) + fill(entry["answer"]), "knowledge", entry=entry,
                               confidence=conf, mood="unsure", can_teach=True, media=self.store.media_public(entry.get("media")),
                               alternatives=self._alts(hits, entry["id"]))
        return self._reply(random.choice(UNKNOWN), "unknown", mood="unsure", can_teach=True, confidence=conf)

    @staticmethod
    def _alts(hits: list[dict], skip: str) -> list[dict]:
        return [{"question": h["entry"]["question"], "answer": fill(h["entry"]["answer"])}
                for h in hits if h["entry"]["id"] != skip and h["confidence"] >= 0.3][:2]

    @staticmethod
    def _reply(answer: str, source: str, *, entry: dict | None = None, confidence: float = 1.0, mood: str = "happy",
               can_teach: bool = False, spoken: str = "", **extra) -> dict:
        return {
            "answer": answer, "spoken": spoken or speakable(answer), "source": source, "mood": mood,
            "origin": entry.get("source", "") if entry else "",
            "entry_id": entry["id"] if entry else None,
            "category": entry["category"] if entry else None,
            "confidence": round(confidence, 3), "can_teach": can_teach, "media": [], **extra,
        }

    # ------------------------------------------------------------------ learning
    def teach(self, question: str, answer: str, category: str = "", keywords: str = "",
              taught_by: str = "", moderate: bool | None = None) -> dict:
        question, answer = " ".join(question.split())[:300], " ".join(answer.split())[:1000]
        if len(question) < 3 or len(answer) < 2:
            return {"ok": False, "message": "I need both a question and an answer to learn it."}
        if looks_inappropriate(question + " " + answer):
            return {"ok": False, "message": "Let's teach me kind and friendly things only."}
        if has_personal_contact(answer):
            return {"ok": False, "message": "Please don't tell me phone numbers or emails. Those are private!"}
        pending = self.store.get_setting("moderate_teaching", False) if moderate is None else moderate
        added, _ = self.store.add_entries(
            [{"question": question, "answer": answer, "category": category or "Taught by students",
              "keywords": keywords, "source": "Taught in conversation"}],
            via="teach", added_by=taught_by, status="pending" if pending else "live")
        if not added:
            return {"ok": True, "message": "I already know that one. Thank you!", "pending": False, "added": 0}
        msg = ("Thank you! My teacher will check it, then I'll remember it." if pending
               else "Yay, thank you! I learned something new!")
        return {"ok": True, "message": msg, "pending": bool(pending), "added": added}

    def feedback(self, question: str, entry_id: str | None, good: bool, correction: str = "",
                 taught_by: str = "") -> dict:
        self.store.rate(question, entry_id, good, correction)
        if good:
            return {"ok": True, "mood": "celebrate", "message": random.choice(
                ["Yay! I'm so happy I got it right!", "Hooray! Thank you for telling me!", "Woohoo! High five!"])}
        if correction.strip():
            res = self.teach(question, correction, taught_by=taught_by)
            if res["ok"]:
                res["message"] = "Oh, I see! Thank you for correcting me. " + res["message"]
                res["mood"] = "happy"
            else:
                res["mood"] = "sad"
            return res
        return {"ok": True, "mood": "sad", "ask_to_teach": True,
                "message": "Oh no, I'm sorry I got it wrong! Can you teach me the right answer?"}

    # ------------------------------------------------------------------ quiz
    def _sign(self, question: str, answer: str) -> str:
        return hmac.new(config.SECRET_KEY.encode(), f"{question}|{normalize(answer)}".encode(), hashlib.sha256).hexdigest()[:24]

    def quiz_new(self, category: str = "", level: int = 1) -> dict:
        pool = [e for e in self.store.all_entries() if e.get("short") and (not category or e["category"] == category)]
        if category.lower() in ("arithmetic", "maths", "math", "mathematics") or not pool or random.random() < 0.25:
            qa = mathengine.new_question(level)
            return {"kind": "math", "question": qa["question"], "token": self._sign(qa["question"], qa["answer"])}
        entry = random.choice(pool)
        return {"kind": "knowledge", "question": fill(entry["question"]), "entry_id": entry["id"],
                "category": entry["category"]}

    def quiz_check(self, kind: str, response: str, question: str = "", token: str = "", entry_id: str = "") -> dict:
        resp = mathengine._words_to_numbers(normalize(response))
        if kind == "math":
            digits = re.sub(r"[^\d.\-]", "", resp.replace(" ", "")) or resp
            ok = hmac.compare_digest(self._sign(question, digits), token)
            return {"correct": ok, "answer": None if ok else "Not quite", "mood": "celebrate" if ok else "sad"}
        entry = self.store.find_entry(entry_id)
        if not entry:
            return {"correct": False, "answer": "", "mood": "sad"}
        short = mathengine._words_to_numbers(normalize(entry["short"]))
        want, got = set(tokens(short, keep_stop=True)), set(tokens(resp, keep_stop=True))
        ok = bool(want) and (want <= got or SequenceMatcher(None, short, resp).ratio() >= 0.85)
        return {"correct": ok, "answer": fill(entry["answer"]), "short": entry["short"],
                "mood": "celebrate" if ok else "sad"}
