"""Turn a document (PDF, Word, PowerPoint, text, web page) into short passages Marshie can find and read out.

No AI is needed: the text is split into passages of a few sentences each, and the search finds the right one.
"""
from __future__ import annotations

import html
import io
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

from .media import MediaError

MAX_CHARS = 400_000        # about 100 pages of text; more than a school project needs
MAX_ZIP_PART = 40 * 1024 * 1024
PASSAGE_CHARS = 420        # short enough to read aloud comfortably


# --------------------------------------------------------------------------- reading
def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return data.decode("utf-8", errors="replace")


class _Text(HTMLParser):
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "table"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "head"):
            self.skip += 1
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "head"):
            self.skip = max(0, self.skip - 1)
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def _html(text: str) -> str:
    p = _Text()
    p.feed(text)
    return "".join(p.out)


def _zip_xml(zf: zipfile.ZipFile, name: str) -> ET.Element:
    info = zf.getinfo(name)
    if info.file_size > MAX_ZIP_PART:
        raise MediaError("That document is too large to read.")
    return ET.fromstring(zf.read(name))


def _docx(data: bytes) -> str:
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        root = _zip_xml(zf, "word/document.xml")
    paras = []
    for p in root.iter(ns + "p"):
        bits = []
        for node in p.iter():
            if node.tag == ns + "t" and node.text:
                bits.append(node.text)
            elif node.tag in (ns + "tab", ns + "br"):
                bits.append(" ")
        paras.append("".join(bits).strip())
    return "\n\n".join(x for x in paras if x)           # each Word paragraph stands alone, so a heading ends like a title


def _pptx(data: bytes) -> str:
    ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    out = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        slides = sorted((n for n in zf.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                        key=lambda n: int(re.findall(r"\d+", n)[0]))
        for name in slides:
            root = _zip_xml(zf, name)
            for p in root.iter(ns + "p"):
                line = "".join(t.text or "" for t in p.iter(ns + "t"))
                if line.strip():
                    out.append(line.strip())
    return "\n\n".join(out)


def _pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise MediaError("Reading PDF files needs one extra package. Run:  python marshie.py setup  (or pip install pypdf).")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise MediaError("That PDF is locked with a password.")
        pages = []
        for page in reader.pages[:300]:
            pages.append(page.extract_text() or "")
    except MediaError:
        raise
    except Exception:
        raise MediaError("I could not read that PDF. Try saving it again, or paste the text instead.")
    text = "\n".join(pages)
    if len(text.strip()) < 20:
        raise MediaError("That PDF has no text I can read (it may be a scan of paper). Paste the text instead.")
    return text


def extract_text(filename: str, data: bytes) -> str:
    ext = Path(filename or "").suffix.lower()
    try:
        if ext == ".pdf":
            text = _pdf(data)
        elif ext == ".docx":
            text = _docx(data)
        elif ext == ".pptx":
            text = _pptx(data)
        elif ext in (".html", ".htm"):
            text = _html(_decode(data))
        elif ext == ".rtf":
            raw = _decode(data)
            raw = re.sub(r"\\'[0-9a-f]{2}", " ", raw)
            raw = re.sub(r"\\[a-z]+-?\d* ?|[{}]", " ", raw)
            text = raw
        else:
            text = _decode(data)
    except (zipfile.BadZipFile, KeyError, ET.ParseError):
        raise MediaError("I could not open that file. Is it really a " + (ext.lstrip(".") or "document") + " file?")
    return clean(text)[:MAX_CHARS]


def clean(text: str) -> str:
    text = html.unescape(text).replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = re.sub(r"[ \t\u00a0]+", " ", text)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)                 # words hyphenated at the end of a line
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# --------------------------------------------------------------------------- passages
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9“\"'(])")


def passages(text: str, size: int = PASSAGE_CHARS) -> list[str]:
    """Cut text into passages of about `size` characters, at sentence ends, never mid-word."""
    out: list[str] = []
    cur = ""

    def flush() -> None:
        nonlocal cur
        if len(cur.strip()) >= 25:
            out.append(cur.strip())
        cur = ""

    for block in re.split(r"\n\s*\n", text):
        block = " ".join(block.split())
        if not block:
            continue
        if len(block) <= 90 and block[-1] not in ".!?:;\"”)":     # a heading on its own line: end it so it reads as a title
            block += "."
        for sent in _SENTENCE.split(block):
            while len(sent) > size * 1.6:                         # one huge unbroken sentence
                cut = sent.rfind(" ", 0, size)
                if cut < size // 2:
                    cut = size
                piece, sent = sent[:cut], sent[cut:].lstrip()
                if cur:
                    flush()
                out.append(piece.strip())
            if cur and len(cur) + 1 + len(sent) > size:
                flush()
            cur = (cur + " " + sent).strip() if cur else sent
        if len(cur) >= size * 0.6:                               # a paragraph break is a good place to stop
            flush()
    flush()
    return out


def lead(passage: str, words: int = 9) -> str:
    bits = passage.split()
    return " ".join(bits[:words]) + ("…" if len(bits) > words else "")
