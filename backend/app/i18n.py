"""The languages Marshie speaks: English, French, Spanish and German.

Everything a child sees or hears that is NOT school knowledge lives here: her small replies ("I don't know that one
yet"), the greeting, the words used to read sums aloud, and the words that start a quiz. School knowledge itself is
stored as entries that carry a language (see data/lang_*.json), and the optional paid AI answers in any of the four.
"""
from __future__ import annotations

import random
import re
import unicodedata

LANGS = {
    "en": {"name": "English", "native": "English", "speech": "en-US"},
    "fr": {"name": "French", "native": "Français", "speech": "fr-FR"},
    "es": {"name": "Spanish", "native": "Español", "speech": "es-ES"},
    "de": {"name": "German", "native": "Deutsch", "speech": "de-DE"},
}
DEFAULT = "en"


def fold(text: str) -> str:
    """Lower case, no accents: 'École' -> 'ecole', 'Größe' -> 'grosse'. Lets a keyboard without accents still be understood."""
    t = str(text or "").lower().replace("ß", "ss").replace("œ", "oe").replace("æ", "ae")
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))


def clean(code) -> str:
    """'fr', 'fr-FR', 'French' or 'Français' -> 'fr'. Anything unknown becomes English."""
    c = fold(str(code or "").strip())
    if c in LANGS:
        return c
    for key, info in LANGS.items():
        if c in (info["name"].lower(), fold(info["native"])):
            return key
    c2 = re.split(r"[-_]", c)[0]
    return c2 if c2 in LANGS else DEFAULT


def name(lang: str) -> str:
    return LANGS[clean(lang)]["name"]


# ---------------------------------------------------------------------------------------------- small replies
MSG: dict[str, dict[str, list[str]]] = {
    "unknown": {
        "en": ["Hmm, I don't know that one yet! Can you teach me the answer?",
               "Oh! That's new to me. Will you teach me so I can learn it?",
               "I haven't learned that yet. Please teach me, I love learning!"],
        "fr": ["Hmm, je ne connais pas encore la réponse ! Peux-tu me l'apprendre ?",
               "Oh ! C'est nouveau pour moi. Tu veux bien me l'apprendre pour que je m'en souvienne ?",
               "Je n'ai pas encore appris ça. Apprends-le-moi, j'adore apprendre !"],
        "es": ["Mmm, ¡todavía no sé la respuesta! ¿Me la puedes enseñar?",
               "¡Oh! Eso es nuevo para mí. ¿Me lo enseñas para que lo aprenda?",
               "Todavía no he aprendido eso. ¡Enséñamelo, me encanta aprender!"],
        "de": ["Hmm, das weiß ich noch nicht! Kannst du mir die Antwort beibringen?",
               "Oh! Das ist neu für mich. Bringst du es mir bei, damit ich es lerne?",
               "Das habe ich noch nicht gelernt. Bitte bring es mir bei, ich lerne so gern!"],
    },
    "unsure_prefix": {
        "en": ["I'm not totally sure, but I think this might help: ", "Hmm, maybe this? ", "I found something close: "],
        "fr": ["Je ne suis pas tout à fait sûre, mais ceci pourrait t'aider : ", "Hmm, peut-être ceci ? ", "J'ai trouvé quelque chose de proche : "],
        "es": ["No estoy del todo segura, pero creo que esto puede ayudarte: ", "Mmm, ¿quizás esto? ", "Encontré algo parecido: "],
        "de": ["Ich bin nicht ganz sicher, aber das könnte helfen: ", "Hmm, vielleicht das hier? ", "Ich habe etwas Ähnliches gefunden: "],
    },
    "refuse": {
        "en": ["Let's keep our words kind and friendly. Ask me about school, science or Ghana instead!"],
        "fr": ["Gardons des mots gentils et amicaux. Demande-moi plutôt quelque chose sur l'école, les sciences ou le Ghana !"],
        "es": ["Usemos palabras amables y simpáticas. ¡Pregúntame mejor sobre la escuela, la ciencia o Ghana!"],
        "de": ["Lass uns freundliche und nette Wörter benutzen. Frag mich lieber etwas über die Schule, Wissenschaft oder Ghana!"],
    },
    "empty": {
        "en": ["I'm listening! Ask me anything, or say 'quiz me'."],
        "fr": ["Je t'écoute ! Pose-moi une question, ou dis « quiz »."],
        "es": ["¡Te escucho! Pregúntame lo que quieras, o di « quiz »."],
        "de": ["Ich höre zu! Frag mich etwas, oder sag „Quiz“."],
    },
    "quiz_start": {
        "en": ["Yay, let's play! {question}"],
        "fr": ["Youpi, on joue ! {question}"],
        "es": ["¡Hurra, a jugar! {question}"],
        "de": ["Juhu, los geht's! {question}"],
    },
    "english_only": {
        "en": [""],
        "fr": ["Je ne connais cette réponse qu'en anglais : "],
        "es": ["Esta respuesta solo la sé en inglés: "],
        "de": ["Diese Antwort kenne ich nur auf Englisch: "],
    },
    "good": {
        "en": ["Yay! I'm so happy I got it right!", "Hooray! Thank you for telling me!", "Woohoo! High five!"],
        "fr": ["Youpi ! Je suis si contente d'avoir bien répondu !", "Hourra ! Merci de me l'avoir dit !", "Ouiii ! Tape-là !"],
        "es": ["¡Hurra! ¡Qué feliz estoy de haber acertado!", "¡Viva! ¡Gracias por decírmelo!", "¡Yupi! ¡Choca esos cinco!"],
        "de": ["Juhu! Ich freue mich so, dass ich es richtig hatte!", "Hurra! Danke, dass du es mir sagst!", "Wuhu! Gib mir fünf!"],
    },
    "bad_ask": {
        "en": ["Oh no, I'm sorry I got it wrong! Can you teach me the right answer?"],
        "fr": ["Oh non, désolée de m'être trompée ! Peux-tu m'apprendre la bonne réponse ?"],
        "es": ["¡Ay no, perdón por equivocarme! ¿Me enseñas la respuesta correcta?"],
        "de": ["Oh nein, es tut mir leid, dass ich mich geirrt habe! Kannst du mir die richtige Antwort beibringen?"],
    },
    "corrected": {
        "en": ["Oh, I see! Thank you for correcting me. "],
        "fr": ["Ah, je vois ! Merci de m'avoir corrigée. "],
        "es": ["¡Ah, ya veo! Gracias por corregirme. "],
        "de": ["Ach so! Danke, dass du mich verbessert hast. "],
    },
    "teach_need": {
        "en": ["I need both a question and an answer to learn it."],
        "fr": ["J'ai besoin d'une question et d'une réponse pour apprendre."],
        "es": ["Necesito una pregunta y una respuesta para aprender."],
        "de": ["Ich brauche eine Frage und eine Antwort, um es zu lernen."],
    },
    "teach_kind": {
        "en": ["Let's teach me kind and friendly things only."],
        "fr": ["Apprends-moi seulement des choses gentilles et amicales."],
        "es": ["Enséñame solo cosas amables y simpáticas."],
        "de": ["Bring mir bitte nur freundliche und nette Dinge bei."],
    },
    "teach_private": {
        "en": ["Please don't tell me phone numbers or emails. Those are private!"],
        "fr": ["Ne me donne pas de numéros de téléphone ni d'e-mails. C'est privé !"],
        "es": ["No me digas números de teléfono ni correos electrónicos. ¡Eso es privado!"],
        "de": ["Bitte nenne mir keine Telefonnummern oder E-Mail-Adressen. Die sind privat!"],
    },
    "teach_known": {
        "en": ["I already know that one. Thank you!"],
        "fr": ["Je connais déjà celle-là. Merci !"],
        "es": ["Eso ya lo sé. ¡Gracias!"],
        "de": ["Das weiß ich schon. Danke!"],
    },
    "teach_pending": {
        "en": ["Thank you! My teacher will check it, then I'll remember it."],
        "fr": ["Merci ! Mon professeur va la vérifier, puis je m'en souviendrai."],
        "es": ["¡Gracias! Mi profesor lo revisará y entonces lo recordaré."],
        "de": ["Danke! Meine Lehrerin oder mein Lehrer schaut es sich an, dann merke ich es mir."],
    },
    "teach_done": {
        "en": ["Yay, thank you! I learned something new!"],
        "fr": ["Youpi, merci ! J'ai appris quelque chose de nouveau !"],
        "es": ["¡Hurra, gracias! ¡Aprendí algo nuevo!"],
        "de": ["Juhu, danke! Ich habe etwas Neues gelernt!"],
    },
    "divide_zero": {
        "en": ["We can't divide by zero! It breaks maths."],
        "fr": ["On ne peut pas diviser par zéro ! Ça casse les maths."],
        "es": ["¡No se puede dividir entre cero! Rompe las matemáticas."],
        "de": ["Man kann nicht durch null teilen! Das bringt die Mathematik durcheinander."],
    },
    "too_big": {
        "en": ["That one is too big for my little head!"],
        "fr": ["Celui-là est trop gros pour ma petite tête !"],
        "es": ["¡Ese es demasiado grande para mi cabecita!"],
        "de": ["Die ist zu groß für meinen kleinen Kopf!"],
    },
}


def pick(key: str, lang: str = DEFAULT) -> str:
    options = MSG[key].get(clean(lang)) or MSG[key][DEFAULT]
    return random.choice(options)


# ---------------------------------------------------------------------------------------------- the greeting
GREETING = {
    "en": ("Hello! My name is {name}, your friendly educative chatbot for the {school} STEAM "
           "(Science, Technology, English, Agriculture & Arts, and Mathematics) Program 2026. How may I be of assistance?"),
    "fr": ("Bonjour ! Je m'appelle {name}, ton chatbot éducatif et amical pour le programme STEAM 2026 à {school} "
           "(Sciences, Technologie, Anglais, Agriculture et Arts, et Mathématiques). Comment puis-je t'aider ?"),
    "es": ("¡Hola! Me llamo {name}, tu chatbot educativo y amigable para el Programa STEAM 2026 de {school} "
           "(Ciencias, Tecnología, Inglés, Agricultura y Artes, y Matemáticas). ¿En qué puedo ayudarte?"),
    "de": ("Hallo! Ich heiße {name}, dein freundlicher Lern-Chatbot für das STEAM-Programm 2026 der {school} "
           "(Naturwissenschaften, Technologie, Englisch, Landwirtschaft und Kunst sowie Mathematik). Wie kann ich dir helfen?"),
}


# ---------------------------------------------------------------------------------------------- starting a quiz
# Written without accents; wants_quiz() folds the child's words the same way (apostrophes and hyphens become spaces).
QUIZ_WORDS = {
    "en": r"(?:please )?(?:quiz me|test me|ask me (?:a|some) questions?|let ?s play|play (?:a )?(?:game|quiz)|give me a quiz)",
    "fr": r"(?:s il te plait |stp )?(?:quiz|un quiz|fais moi un quiz|pose moi (?:des|une) questions?|teste moi|interroge moi|"
          r"jouons|on joue|jouer|je veux jouer|faisons un quiz)",
    "es": r"(?:por favor )?(?:quiz|un quiz|hazme un quiz|hazme (?:unas )?preguntas?|examiname|ponme a prueba|"
          r"juguemos|vamos a jugar|jugar|quiero jugar|hagamos un quiz)",
    "de": r"(?:bitte )?(?:quiz|ein quiz|quizze mich|frag mich|stell mir (?:fragen|eine frage)|teste mich|"
          r"lass uns spielen|spielen wir|spielen|ich will spielen|machen wir ein quiz)",
}
QUIZ_RE = {k: re.compile(r"^" + v + r"\b") for k, v in QUIZ_WORDS.items()}


def plain(text: str) -> str:
    """Folded, with apostrophes and hyphens as spaces: "Fais-moi un QUIZ !" -> "fais moi un quiz"."""
    t = re.sub(r"[\u2019'`\-]", " ", fold(text))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", t)).strip()


def wants_quiz(text: str, lang: str) -> bool:
    return bool(QUIZ_RE[clean(lang)].search(plain(text)))


# The ways a child may ask about a topic from the "Facts" sheet of the Excel file.
TOPIC_QUESTIONS = {
    "en": ["Tell me about {t}", "What is {t}", "Who is {t}", "{t}"],
    "fr": ["Parle-moi de {t}", "Qu'est-ce que {t}", "Qui est {t}", "C'est quoi {t}", "{t}"],
    "es": ["Háblame de {t}", "¿Qué es {t}?", "¿Quién es {t}?", "{t}"],
    "de": ["Erzähl mir von {t}", "Was ist {t}", "Wer ist {t}", "{t}"],
}


# ---------------------------------------------------------------------------------------------- reading sums aloud
# 'times' etc. in each language: used to say "12 times 7 is 84" and the question of a maths quiz.
MATH = {
    "en": {"+": "plus", "-": "minus", "*": "times", "/": "divided by", "pow": "to the power of", "is": "is", "of": "of",
           "sqrt": "square root", "cbrt": "cube root", "squared": "squared", "percent": "percent", "ask": "What is {a} {op} {b}?"},
    "fr": {"+": "plus", "-": "moins", "*": "fois", "/": "divisé par", "pow": "puissance", "is": "égale", "of": "de",
           "sqrt": "racine carrée", "cbrt": "racine cubique", "squared": "au carré", "percent": "pour cent", "ask": "Combien font {a} {op} {b} ?"},
    "es": {"+": "más", "-": "menos", "*": "por", "/": "dividido entre", "pow": "elevado a", "is": "es igual a", "of": "de",
           "sqrt": "raíz cuadrada", "cbrt": "raíz cúbica", "squared": "al cuadrado", "percent": "por ciento", "ask": "¿Cuánto es {a} {op} {b}?"},
    "de": {"+": "plus", "-": "minus", "*": "mal", "/": "geteilt durch", "pow": "hoch", "is": "ist", "of": "von",
           "sqrt": "Quadratwurzel", "cbrt": "Kubikwurzel", "squared": "zum Quadrat", "percent": "Prozent", "ask": "Was ist {a} {op} {b}?"},
}

# Words that stand for the symbols when text is read out loud.
SPEAK = {
    "en": {"and": "and", "is": "is", "at": "at", "dot": "dot", "plus": "plus", "minus": "minus", "times": "times",
           "over": "divided by", "power": "to the power of", "percent": "percent", "to": "to"},
    "fr": {"and": "et", "is": "égale", "at": "arobase", "dot": "point", "plus": "plus", "minus": "moins", "times": "fois",
           "over": "divisé par", "power": "puissance", "percent": "pour cent", "to": "à"},
    "es": {"and": "y", "is": "es igual a", "at": "arroba", "dot": "punto", "plus": "más", "minus": "menos", "times": "por",
           "over": "dividido entre", "power": "elevado a", "percent": "por ciento", "to": "a"},
    "de": {"and": "und", "is": "ist", "at": "at", "dot": "Punkt", "plus": "plus", "minus": "minus", "times": "mal",
           "over": "geteilt durch", "power": "hoch", "percent": "Prozent", "to": "bis"},
}


def speak_words(lang: str) -> dict:
    return SPEAK[clean(lang)]
