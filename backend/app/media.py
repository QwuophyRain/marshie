"""Pictures, sound and video that teachers add. This file keeps the bytes; what Marshie *says* about a file
lives in ordinary knowledge entries that point at it by id.

* On a normal computer the files go in data/media/ (next to data/state.json).
* On Vercel with an Upstash/KV store each file is one key. KV values are small, so such files must be small too.
"""
from __future__ import annotations

import base64
import os
import re
from pathlib import Path

from . import config

IMAGE_EXT = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
AUDIO_EXT = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg", ".oga": "audio/ogg", ".opus": "audio/ogg",
             ".m4a": "audio/mp4", ".aac": "audio/aac", ".flac": "audio/flac", ".webm": "audio/webm"}
VIDEO_EXT = {".mp4": "video/mp4", ".m4v": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm"}
DOC_EXT = {".pdf", ".docx", ".pptx", ".txt", ".md", ".html", ".htm", ".rtf"}
SHEET_EXT = {".xlsx", ".xlsm", ".csv"}
BACKUP_EXT = {".json", ".zip"}


class MediaError(ValueError):
    """A problem with a file that a teacher can understand and fix."""


def file_type(filename: str, content_type: str = "") -> str:
    """What sort of file is this? image | audio | video | document | sheet | backup | '' (unknown)."""
    ext = Path(filename or "").suffix.lower()
    ctype = (content_type or "").lower()
    if ext in SHEET_EXT:
        return "sheet"
    if ext in DOC_EXT:
        return "document"
    if ext in BACKUP_EXT:
        return "backup"
    if ext in IMAGE_EXT:
        return "image"
    if ext in (".webm", ".ogg") and ctype.startswith("video/"):
        return "video"
    if ext in AUDIO_EXT:
        return "audio"
    if ext in VIDEO_EXT:
        return "video"
    return ""


def _sniff(data: bytes) -> str:
    """The real type of the bytes, from the first few bytes. '' when it is not a type we serve."""
    h = data[:16]
    if h.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if h.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if h.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if h[:4] == b"RIFF" and h[8:12] == b"WEBP":
        return "image/webp"
    if h[:4] == b"RIFF" and h[8:12] == b"WAVE":
        return "audio/wav"
    if h.startswith(b"OggS"):
        return "audio/ogg"
    if h.startswith(b"fLaC"):
        return "audio/flac"
    if h.startswith(b"ID3") or (len(h) > 1 and h[0] == 0xFF and (h[1] & 0xE0) == 0xE0):
        return "audio/mpeg"
    if h[4:8] == b"ftyp":
        return "video/mp4"
    if h.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm"
    return ""


def check_media(filename: str, content_type: str, data: bytes) -> tuple[str, str]:
    """Return (kind, mime) for a picture, sound or video, or raise MediaError with a friendly message."""
    kind = file_type(filename, content_type)
    if kind not in ("image", "audio", "video"):
        raise MediaError("I can use pictures (png, jpg, gif, webp), sound (mp3, wav, m4a, ogg, webm) and video (mp4, webm).")
    if not data:
        raise MediaError("That file is empty.")
    limit = config.MAX_MEDIA_BYTES
    if len(data) > limit:
        raise MediaError(f"That file is too big ({len(data) / 1048576:.1f} MB). The limit here is {limit / 1048576:.0f} MB.")
    real = _sniff(data)
    ext = Path(filename).suffix.lower()
    if kind == "image":
        if not real.startswith("image/"):
            raise MediaError("That does not look like a real picture. Try saving it again as a png or jpg.")
        return kind, real
    if real.startswith("image/"):
        raise MediaError("That is a picture, not a sound or video.")
    mime = (AUDIO_EXT if kind == "audio" else VIDEO_EXT).get(ext, "")
    if kind == "audio" and ext == ".webm" and content_type.lower().startswith("video/"):
        mime = "video/webm"
    return kind, mime or ("audio/mpeg" if kind == "audio" else "video/mp4")


def new_id() -> str:
    return "m-" + os.urandom(6).hex()


SAFE_ID = re.compile(r"^[a-z0-9-]{3,40}$")


# --------------------------------------------------------------------------- where the bytes live
class FileBlobs:
    def __init__(self, folder: Path):
        self.folder = folder

    def _path(self, media_id: str) -> Path:
        if not SAFE_ID.match(media_id):
            raise MediaError("Bad file id.")
        return self.folder / media_id

    def put(self, media_id: str, data: bytes) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        path = self._path(media_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)

    def get(self, media_id: str) -> bytes | None:
        try:
            return self._path(media_id).read_bytes()
        except (FileNotFoundError, MediaError):
            return None

    def delete(self, media_id: str) -> None:
        try:
            self._path(media_id).unlink()
        except (FileNotFoundError, MediaError):
            pass

    @property
    def max_bytes(self) -> int:
        return config.MAX_MEDIA_BYTES


class KVBlobs:
    """One Upstash/KV key per file (base64). Needs a backend with get_raw/set_raw/del_raw."""

    def __init__(self, backend):
        self.backend = backend

    def put(self, media_id: str, data: bytes) -> None:
        if not SAFE_ID.match(media_id):
            raise MediaError("Bad file id.")
        self.backend.set_raw(f"marshie_media:{media_id}", base64.b64encode(data).decode())

    def get(self, media_id: str) -> bytes | None:
        if not SAFE_ID.match(media_id):
            return None
        try:
            raw = self.backend.get_raw(f"marshie_media:{media_id}")
            return base64.b64decode(raw) if raw else None
        except Exception:
            return None

    def delete(self, media_id: str) -> None:
        if SAFE_ID.match(media_id):
            try:
                self.backend.del_raw(f"marshie_media:{media_id}")
            except Exception:
                pass

    @property
    def max_bytes(self) -> int:
        return min(config.MAX_MEDIA_BYTES, config.MAX_KV_MEDIA_BYTES)


def questions_for(title: str, kind: str) -> list[str]:
    """Ways a child might ask for a picture or recording called `title`."""
    t = title.strip().rstrip("?.! ")
    if kind == "audio":
        return [f"play {t}", f"let me hear {t}", f"listen to {t}", f"play the {t} recording", f"{t} audio"]
    if kind == "video":
        return [f"show me the {t} video", f"play the {t} video", f"{t} video", f"watch {t}"]
    return [f"show me {t}", f"show me a picture of {t}", f"what does {t} look like", f"picture of {t}", f"{t} picture",
            f"let me see {t}"]
