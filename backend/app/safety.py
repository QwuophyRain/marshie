"""A deliberately simple guard so a children's chatbot can't be taught rude or unsafe things.

Not a replacement for teacher review (the Teacher panel lists everything Marshie has learned and
lets you delete any entry), but it catches the obvious cases from Excel uploads and the "teach me" box.
"""
from __future__ import annotations

import re

from .i18n import fold

_BLOCKED = (
    # Kept short on purpose: words with innocent school uses (weed, naked mole rat, Moby Dick,
    # sexual reproduction) are NOT listed, so science and literature entries are never rejected.
    "fuck", "shit", "bitch", "bastard", "asshole", "pussy", "cunt", "whore", "slut",
    "nigger", "nigga", "faggot", "retard", "porn", "rape", "nude", "kill yourself",
    "suicide", "cocaine", "heroin",
    # French, Spanish and German (written without accents; the text is folded before it is checked)
    "merde", "putain", "connard", "connasse", "salope", "encule", "enculer", "niquer", "ta gueule", "pute", "porno",
    "viol", "violer", "heroine", "tue toi",
    "mierda", "puta", "puto", "cabron", "pendejo", "gilipollas", "hijo de puta", "maricon", "verga", "cocaina",
    "heroina", "suicidio", "violacion", "matate",
    "scheisse", "arschloch", "fotze", "hurensohn", "wichser", "schlampe", "ficken", "nutte", "selbstmord", "kokain",
    "vergewaltigung", "bring dich um",
)
_PATTERN = re.compile(r"\b(" + "|".join(re.escape(w) for w in _BLOCKED) + r")(?:s|ed|ing)?\b", re.I)
_PHONE_OR_EMAIL = re.compile(r"(\+?\d[\d\s\-]{8,}\d)|([\w.+-]+@[\w-]+\.[\w.-]+)")


def looks_inappropriate(text: str) -> bool:
    return bool(_PATTERN.search(fold(text or "")))


def has_personal_contact(text: str) -> bool:
    """Phone numbers / emails of children shouldn't be stored or spoken aloud."""
    return bool(_PHONE_OR_EMAIL.search(text or ""))
