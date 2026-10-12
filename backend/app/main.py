"""Marshie's web API. Runs the same code on a Raspberry Pi (uvicorn) and on Vercel (api/index.py)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import importlib.util
import io
import json
import mimetypes
import re
import time
import zipfile
from collections import defaultdict, deque
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, docs, excel_io, llm, voice
from . import media as media_mod
from .brain import Brain
from .store import StorageError, Store

# Windows can report .js as text/plain (it reads the registry), which makes browsers refuse
# to run the Vue app. Pin the types so Marshie behaves the same on Windows, macOS and Linux.
for _ext, _mime in ((".js", "application/javascript"), (".mjs", "application/javascript"), (".css", "text/css"),
                    (".svg", "image/svg+xml"), (".json", "application/json"), (".wasm", "application/wasm")):
    mimetypes.add_type(_mime, _ext)

app = FastAPI(title="Marshie", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

store = Store()
brain = Brain(store)
MAX_UPLOAD = 8 * 1024 * 1024
MAX_RESTORE = 4 * 1024 * 1024 if config.IS_VERCEL else 200 * 1024 * 1024
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


@app.exception_handler(StorageError)
async def _storage_full(_request: Request, exc: StorageError):
    return JSONResponse({"detail": str(exc)}, status_code=507)


@app.exception_handler(media_mod.MediaError)
async def _bad_file(_request: Request, exc: media_mod.MediaError):
    return JSONResponse({"detail": str(exc)}, status_code=400)


# ============================================================================ small helpers
def _sign(payload: str) -> str:
    return hmac.new(config.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()


def make_token(hours: int = 8) -> str:
    body = base64.urlsafe_b64encode(json.dumps({"exp": int(time.time()) + hours * 3600}).encode()).decode()
    return f"{body}.{_sign(body)}"


def valid_token(token: str) -> bool:
    try:
        body, sig = token.split(".", 1)
        return hmac.compare_digest(sig, _sign(body)) and json.loads(base64.urlsafe_b64decode(body))["exp"] > time.time()
    except Exception:
        return False


def admin(x_admin_token: str = Header(default=""), token: str = Query(default="")) -> None:
    """Header for normal calls; ?token= for file downloads opened by a plain link."""
    if not valid_token(x_admin_token or token):
        raise HTTPException(401, "Teacher PIN needed")


_hits: dict[str, deque] = defaultdict(deque)


def limit(request: Request, bucket: str, count: int, seconds: int) -> None:
    ip = (request.headers.get("x-forwarded-for", "").split(",")[0] or (request.client.host if request.client else "?")).strip()
    q = _hits[f"{bucket}:{ip}"]
    now = time.time()
    while q and q[0] < now - seconds:
        q.popleft()
    if len(q) >= count:
        raise HTTPException(429, "Slow down a little, please!")
    q.append(now)


# ============================================================================ models
class AskIn(BaseModel):
    question: str = Field(max_length=500)
    history: list[dict] = []


class FeedbackIn(BaseModel):
    question: str = Field(max_length=500)
    entry_id: str | None = None
    good: bool
    correction: str = Field(default="", max_length=1000)
    taught_by: str = Field(default="", max_length=60)


class TeachIn(BaseModel):
    question: str = Field(max_length=300)
    answer: str = Field(max_length=1000)
    category: str = Field(default="", max_length=60)
    keywords: str = Field(default="", max_length=200)
    taught_by: str = Field(default="", max_length=60)


class QuizCheckIn(BaseModel):
    kind: str
    response: str = Field(max_length=200)
    question: str = ""
    token: str = ""
    entry_id: str = ""


class TtsIn(BaseModel):
    text: str = Field(max_length=800)
    length_scale: float = 1.25


class LoginIn(BaseModel):
    pin: str


class SettingsIn(BaseModel):
    moderate_teaching: bool | None = None
    greeting: str | None = Field(default=None, max_length=700)      # "" = go back to the standard greeting
    theme: dict[str, str] | None = None                            # {} = go back to the school colours


class AIIn(BaseModel):
    provider: str = Field(default="anthropic", pattern="^(anthropic|openai)$")
    key: str = Field(default="", max_length=400)                     # blank = keep the key already saved
    model: str = Field(default="", max_length=100)
    base_url: str = Field(default="", max_length=300)
    enabled: bool = True
    daily_limit: int = Field(default=llm.DEFAULT_LIMIT, ge=10, le=5000)


# ============================================================================ public API
def current_theme() -> dict:
    theme = dict(config.THEME)
    saved = store.get_setting("theme")
    if isinstance(saved, dict):
        theme.update({k: v for k, v in saved.items() if k in theme and isinstance(v, str) and HEX.match(v)})
    return theme


def logo_url() -> str | None:
    mid = store.get_setting("logo")
    return f"/api/media/{mid}" if mid and store.media_record(mid) else None


@app.get("/api/health")
def health():
    store.refresh_if_stale()
    caps = {**voice.capabilities(), "llm": llm.describe(llm.resolve(store.get_setting("ai")))["enabled"]}
    hello = brain.greeting()
    return {"ok": True, "name": config.BOT_NAME, "school": config.SCHOOL_NAME, "event": config.EVENT_NAME,
            "greeting": hello["text"], "greeting_spoken": hello["spoken"],
            "theme": current_theme(), "logo": logo_url(), "school_url": config.SCHOOL_URL,
            "capabilities": caps, "entries": len(store.all_entries()), "persistent": store.persistent,
            "on_vercel": config.IS_VERCEL}


@app.get("/api/media/{media_id}")
def get_media(media_id: str, request: Request):
    """A picture, recording or video. Supports byte ranges, which Safari needs before it will play sound or video."""
    store.refresh_if_stale()
    got = store.get_blob(media_id)
    if not got:
        raise HTTPException(404, "I can't find that file.")
    data, mime = got
    headers = {"Accept-Ranges": "bytes", "Cache-Control": "public, max-age=31536000, immutable",
               "X-Content-Type-Options": "nosniff"}
    m = re.match(r"^bytes=(\d*)-(\d*)$", request.headers.get("range", ""))
    if m and (m.group(1) or m.group(2)):
        size = len(data)
        if m.group(1):
            start, end = int(m.group(1)), (int(m.group(2)) if m.group(2) else size - 1)
        else:
            start, end = max(0, size - int(m.group(2))), size - 1
        end = min(end, size - 1)
        if start >= size or start > end:
            return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})
        return Response(data[start:end + 1], status_code=206, media_type=mime,
                        headers={**headers, "Content-Range": f"bytes {start}-{end}/{size}"})
    return Response(data, media_type=mime, headers=headers)


@app.post("/api/ask")
def ask(body: AskIn, request: Request):
    limit(request, "ask", 60, 60)
    result = brain.ask(body.question, body.history)
    if result["source"] == "unknown":
        store.log_unknown(body.question)
    return result


@app.post("/api/feedback")
def feedback(body: FeedbackIn, request: Request):
    limit(request, "feedback", 40, 60)
    res = brain.feedback(body.question, body.entry_id, body.good, body.correction, body.taught_by)
    if res.get("ok") and body.correction.strip() and not res.get("ask_to_teach"):
        store.resolve_unknown(body.question)
    return res


@app.post("/api/teach")
def teach(body: TeachIn, request: Request):
    limit(request, "teach", 20, 60)
    res = brain.teach(body.question, body.answer, body.category, body.keywords, body.taught_by)
    if res.get("ok"):
        store.resolve_unknown(body.question)
    return res


@app.get("/api/categories")
def categories():
    return {"categories": sorted(store.stats()["categories"])}


@app.get("/api/quiz")
def quiz(category: str = "", level: int = 1):
    return brain.quiz_new(category, level)


@app.post("/api/quiz/check")
def quiz_check(body: QuizCheckIn):
    return brain.quiz_check(body.kind, body.response, body.question, body.token, body.entry_id)


@app.post("/api/tts")
def tts(body: TtsIn):
    wav = voice.synthesize(body.text, max(0.8, min(body.length_scale, 1.8)))
    if wav is None:
        raise HTTPException(501, "Server voice is not installed; the browser voice will be used.")
    return Response(wav, media_type="audio/wav", headers={"Cache-Control": "no-store"})


@app.post("/api/stt")
async def stt(request: Request):
    """Body: raw 16-bit mono PCM @ 16 kHz (the browser records and downsamples it)."""
    if not voice.stt_available():
        raise HTTPException(501, "Server listening is not installed; the browser microphone recogniser will be used.")
    pcm = await request.body()
    if len(pcm) > 16000 * 2 * 30:
        raise HTTPException(413, "That recording is too long (30 seconds max).")
    return {"text": voice.transcribe(pcm)}


# ============================================================================ teacher API
_fails: dict[str, list[float]] = defaultdict(list)


@app.post("/api/admin/login")
def login(body: LoginIn, request: Request):
    ip = (request.headers.get("x-forwarded-for", "").split(",")[0] or (request.client.host if request.client else "?")).strip()
    now = time.time()
    _fails[ip] = [t for t in _fails[ip] if t > now - 60]
    if len(_fails[ip]) >= 5:
        raise HTTPException(429, "Too many tries. Wait a minute and try again.")
    if not hmac.compare_digest(body.pin.encode(), config.ADMIN_PIN.encode()):
        _fails[ip].append(now)
        raise HTTPException(401, "That PIN is not right.")
    return {"token": make_token(), "default_pin": config.PIN_IS_DEFAULT}


@app.get("/api/admin/overview", dependencies=[Depends(admin)])
def overview():
    store.refresh_if_stale()
    s = store.state
    unknown = sorted(s.get("unknown", {}).values(), key=lambda r: (-r["n"], -r["ts"]))[:25]
    return {
        "stats": store.stats(), "llm": llm.describe(llm.resolve(store.get_setting("ai"))), "voice": voice.capabilities(),
        "settings": {"moderate_teaching": store.get_setting("moderate_teaching", False),
                     "greeting": store.get_setting("greeting", ""), "theme": store.get_setting("theme", {}) or {}},
        "defaults": {"greeting": config.GREETING, "theme": config.THEME},
        "features": {"pdf": importlib.util.find_spec("pypdf") is not None,
                     "transcribe": voice.stt_available(), "media_mb": round(store.blobs.max_bytes / 1048576, 1)},
        "uploads": list(reversed(s["uploads"]))[:10], "unknown": unknown,
        "datasets": [{"id": d["id"], "name": d["name"], "columns": d["columns"], "rows": len(d["rows"]),
                      "source": d.get("source", ""), "preview": d["rows"][:5]} for d in s["datasets"]],
        "default_pin": config.PIN_IS_DEFAULT, "on_vercel": config.IS_VERCEL,
    }


@app.post("/api/admin/settings", dependencies=[Depends(admin)])
def set_settings(body: SettingsIn):
    values: dict = {}
    if body.moderate_teaching is not None:
        values["moderate_teaching"] = body.moderate_teaching
    if body.greeting is not None:
        values["greeting"] = " ".join(body.greeting.split())
    if body.theme is not None:
        values["theme"] = {k: v.lower() for k, v in body.theme.items() if k in config.DEFAULT_THEME and HEX.match(v)}
    store.set_settings(values)
    return {"ok": True, "theme": current_theme(), "greeting": brain.greeting()["text"]}


# ---------------------------------------------------------------------------- the paid AI (optional)
def _ai_view() -> dict:
    """What the Teacher panel may see. The key itself is never sent back: only its last four letters."""
    saved = store.get_setting("ai") or {}
    cfg = llm.resolve(saved)
    return {
        **llm.describe(cfg), "base_url": cfg["base_url"], "has_key": bool(cfg["key"]), "key_hint": llm.key_hint(cfg["key"]),
        "saved": bool(saved.get("provider")), "needs_key": llm.needs_key(cfg["provider"], cfg["base_url"]),
        "model_default": llm.DEFAULT_MODEL.get(cfg["provider"], ""), "model_saved": str(saved.get("model") or ""),
        "presets": llm.PRESETS, "on_vercel": config.IS_VERCEL,
    }


def _ai_from(body: AIIn) -> dict:
    """Check what a teacher typed and turn it into settings. Raises a 422 with words they can act on."""
    saved = store.get_setting("ai") or {}
    base = body.base_url.strip().rstrip("/")
    if base and not re.fullmatch(r"https?://[^\s]+", base):
        raise HTTPException(422, "The web address must start with http:// or https://")
    key = body.key.strip().strip("\"'")
    if key and not llm.KEY_OK.fullmatch(key):
        raise HTTPException(422, "That key does not look right. It should be one line of letters and numbers with no spaces.")
    if not key and saved.get("key") and saved.get("provider") == body.provider and (saved.get("base_url") or "") == base:
        key = saved["key"]                       # unchanged service: keep the saved key, so it never has to be typed again
    if not key and llm.needs_key(body.provider, base):
        raise HTTPException(422, "Paste the API key first. You get it from the service's website.")
    return {"provider": body.provider, "key": key, "model": body.model.strip(), "base_url": base,
            "enabled": body.enabled, "daily_limit": body.daily_limit}


@app.get("/api/admin/ai", dependencies=[Depends(admin)])
def get_ai():
    store.refresh_if_stale()
    return _ai_view()


@app.put("/api/admin/ai", dependencies=[Depends(admin)])
def save_ai(body: AIIn):
    store.set_settings({"ai": _ai_from(body)})
    return _ai_view()


@app.delete("/api/admin/ai", dependencies=[Depends(admin)])
def remove_ai():
    store.set_settings({"ai": {}})
    return _ai_view()


@app.post("/api/admin/ai/test", dependencies=[Depends(admin)])
def test_ai(body: AIIn):
    """Try the settings on the form (saved or not) with one small question."""
    return llm.test(llm.resolve({**_ai_from(body), "enabled": True}))


@app.get("/api/admin/entries", dependencies=[Depends(admin)])
def list_entries(q: str = "", via: str = "", status: str = "", category: str = "", limit: int = 50, offset: int = 0,
                 group: str = ""):
    rows = store.seed + store.state["entries"]
    if group:
        rows = [e for e in rows if e.get("group") == group]
    if via:
        rows = [e for e in rows if e["via"] == via]
    if status == "pending":
        rows = [e for e in rows if e.get("status") == "pending"]
    if category:
        rows = [e for e in rows if e["category"] == category]
    if q:
        ql = q.lower()
        rows = [e for e in rows if ql in e["question"].lower() or ql in e["answer"].lower()]
    limit = max(1, min(limit, 200))
    slim = [{k: e.get(k, "") for k in ("id", "category", "question", "answer", "via", "added_by", "source", "created")}
            | {"status": e.get("status", "live"), "has_media": bool(e.get("media"))} for e in rows[offset:offset + limit]]
    return {"total": len(rows), "entries": slim}


@app.delete("/api/admin/entries/{entry_id}", dependencies=[Depends(admin)])
def delete_entry(entry_id: str):
    if not store.delete_entry(entry_id):
        raise HTTPException(404, "Only learned entries can be deleted (built-in knowledge is read-only).")
    return {"ok": True}


@app.post("/api/admin/entries/{entry_id}/approve", dependencies=[Depends(admin)])
def approve(entry_id: str):
    if not store.approve_entry(entry_id):
        raise HTTPException(404, "Nothing waiting with that id.")
    return {"ok": True}


class ManualEntry(BaseModel):
    question: str
    answer: str
    category: str = "General"
    keywords: str = ""
    short: str = ""


@app.post("/api/admin/entries", dependencies=[Depends(admin)])
def add_entry(body: ManualEntry):
    res = brain.teach(body.question, body.answer, body.category, body.keywords, "Teacher", moderate=False)
    if res.get("ok") and body.short:
        last = store.state["entries"][-1]
        if last["question"] == body.question.strip():
            last["short"] = body.short.strip()
            store.save()
    return res


@app.get("/api/admin/template", dependencies=[Depends(admin)])
def template(kind: str = "all", school: str = "", class_name: str = "", category: str = "",
             columns: str = "", dataset_name: str = "", rows: int = 50):
    cols = [c.strip() for c in columns.replace("|", ",").split(",") if c.strip()]
    data = excel_io.build_template(kind, school or config.SCHOOL_NAME, class_name, category, cols, dataset_name, rows)
    name = f"marshie-template-{kind}{('-' + class_name.replace(' ', '')) if class_name else ''}.xlsx"
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@app.post("/api/admin/upload", dependencies=[Depends(admin)])
async def upload(file: UploadFile = File(...), commit: bool = Form(False), category_override: str = Form("")):
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "That file is too big (8 MB max). Split it into smaller files.")
    parsed = excel_io.parse_workbook(data, file.filename or "upload.xlsx")
    summary = {
        "filename": file.filename, "sheets": parsed["sheets"], "errors": parsed["errors"][:100],
        "error_count": len(parsed["errors"]), "warnings": parsed["warnings"][:50],
        "skipped_examples": parsed["skipped_examples"],
        "to_add": len(parsed["entries"]), "datasets": [{"name": d["name"], "columns": d["columns"], "rows": len(d["rows"]),
                                                       "preview": d["rows"][:3]} for d in parsed["datasets"]],
        "sample": [{"question": (e["question"][0] if isinstance(e["question"], list) else e["question"]),
                    "answer": e["answer"]} for e in parsed["entries"][:5]],
        "committed": False,
    }
    if commit:
        for e in parsed["entries"]:
            if category_override:
                e["category"] = category_override
        added, dup = store.add_entries(parsed["entries"], via="excel", added_by="Excel upload")
        for ds in parsed["datasets"]:
            store.add_dataset(ds["name"], ds["columns"], ds["rows"], file.filename or "upload")
        summary.update({"committed": True, "added": added, "duplicates": dup,
                        "datasets_added": len(parsed["datasets"])})
        store.log_upload(file.filename or "upload", {"added": added, "duplicates": dup, "errors": len(parsed["errors"]),
                                                     "datasets": len(parsed["datasets"])})
    return summary


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[A-Za-z0-9']+", text) if len(w) > 2][:8]


DEFAULT_SAY = {"image": "Here it is: {t}!", "audio": "Listen! Press play to hear {t}.",
               "video": "Here is the video: {t}. Press play to watch it."}
DEFAULT_CATEGORY = {"image": "Pictures", "audio": "Sound", "video": "Video"}


@app.post("/api/admin/media", dependencies=[Depends(admin)])
async def add_media(file: UploadFile = File(...), title: str = Form(""), say: str = Form(""), questions: str = Form(""),
                    category: str = Form(""), transcript: str = Form("")):
    """A picture, recording or video. Marshie shows or plays it when a child asks for it (or about what is in it)."""
    data = await file.read(config.MAX_MEDIA_BYTES + 1)
    kind, mime = media_mod.check_media(file.filename or "", file.content_type or "", data)
    stem = Path(file.filename or "file").stem.replace("_", " ").replace("-", " ")
    title = " ".join(title.split())[:100] or " ".join(stem.split())[:100] or "My file"
    say = " ".join(say.split())[:600] or DEFAULT_SAY[kind].format(t=title)
    category = category.strip()[:60] or DEFAULT_CATEGORY[kind]
    extra_qs = [" ".join(q.split())[:200] for q in questions.splitlines() if q.strip()][:20]
    rec = store.add_media(data, kind, mime, title, file.filename or "", role="")
    try:
        entries = [{"question": [title, *media_mod.questions_for(title, kind), *extra_qs], "answer": say,
                    "category": category, "keywords": _words(title), "media": [rec["id"]], "group": rec["id"],
                    "source": f"File: {file.filename}" if file.filename else ""}]
        transcript = docs.clean(transcript)[:20000]
        if len(transcript) >= 30:
            for p in docs.passages(transcript):
                entries.append({"question": f"{title}: {docs.lead(p)}", "answer": p, "category": category,
                                "keywords": _words(title), "media": [rec["id"]], "group": rec["id"], "kind": "passage",
                                "source": f"From the recording: {title}"})
        added, _ = store.add_entries(entries, via="media", added_by="Teacher", strict=True)
    except Exception:
        store.delete_media(rec["id"])
        raise
    store.log_upload(file.filename or title, {"added": added, "duplicates": 0, "errors": 0, "datasets": 0, "kind": kind})
    return {"ok": True, "kind": kind, "title": title, "added": added, "media": store._media_view(rec)}


@app.post("/api/admin/document", dependencies=[Depends(admin)])
async def add_document(file: UploadFile | None = File(default=None), text: str = Form(""), title: str = Form(""),
                       category: str = Form(""), commit: bool = Form(False)):
    """A PDF, Word, PowerPoint, text or web page file, or pasted text. Cut into passages Marshie can find and read."""
    filename = ""
    if file is not None and file.filename:
        data = await file.read(MAX_UPLOAD + 1)
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, "That file is too big (8 MB max). Split it into smaller files.")
        filename = file.filename
        body = docs.extract_text(filename, data)
    else:
        body = docs.clean(text)[:docs.MAX_CHARS]
    if len(body) < 25:
        raise HTTPException(400, "I could not find any text to learn. Choose a file with words in it, or paste some text.")
    title = " ".join(title.split())[:120] or " ".join(Path(filename).stem.replace("_", " ").replace("-", " ").split()) \
        or " ".join(body.split()[:6])
    parts = docs.passages(body)[:2000]
    if not parts:
        raise HTTPException(400, "I could not find any text to learn in that.")
    replaces = bool(filename) and any(d.get("filename") == filename for d in store.state["documents"])
    summary = {"title": title, "filename": filename, "characters": len(body), "passages": len(parts),
               "sample": parts[:3], "replaces": replaces, "committed": False}
    if commit:
        rec = store.add_document(title, filename, parts, category.strip()[:60], docs.lead)
        store.log_upload(filename or title, {"added": rec["passages"], "duplicates": 0, "errors": 0, "datasets": 0,
                                             "kind": "document"})
        summary.update({"committed": True, "added": rec["passages"]})
    return summary


@app.get("/api/admin/library", dependencies=[Depends(admin)])
def library():
    return {"items": store.library()}


@app.delete("/api/admin/library/{item_id}", dependencies=[Depends(admin)])
def delete_library_item(item_id: str):
    if not store.delete_library_item(item_id):
        raise HTTPException(404, "I can't find that.")
    return {"ok": True}


@app.post("/api/admin/logo", dependencies=[Depends(admin)])
async def set_logo(file: UploadFile = File(...)):
    data = await file.read(config.MAX_MEDIA_BYTES + 1)
    kind, mime = media_mod.check_media(file.filename or "", file.content_type or "", data)
    if kind != "image":
        raise HTTPException(400, "The logo must be a picture (png, jpg, gif or webp).")
    old = store.get_setting("logo")
    rec = store.add_media(data, kind, mime, "School logo", file.filename or "logo", role="logo")
    store.set_settings({"logo": rec["id"]})
    if old and old != rec["id"]:
        store.delete_media(old)
    return {"ok": True, "logo": f"/api/media/{rec['id']}"}


@app.delete("/api/admin/logo", dependencies=[Depends(admin)])
def remove_logo():
    old = store.get_setting("logo")
    if old:
        store.delete_media(old)
    return {"ok": True}


@app.delete("/api/admin/datasets/{ds_id}", dependencies=[Depends(admin)])
def delete_dataset(ds_id: str):
    if not store.delete_dataset(ds_id):
        raise HTTPException(404, "No such data table.")
    return {"ok": True}


@app.get("/api/admin/export", dependencies=[Depends(admin)])
def export(format: str = "xlsx"):
    if format == "json":
        return Response(json.dumps(store.export_state(), ensure_ascii=False, indent=1), media_type="application/json",
                        headers={"Content-Disposition": 'attachment; filename="marshie-knowledge-backup.json"'})
    if format == "zip":                       # everything, including pictures and recordings
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("knowledge.json", json.dumps(store.export_state(), ensure_ascii=False, indent=1))
            for rec in store.state["media"]:
                blob = store.blobs.get(rec["id"])
                if blob is not None:
                    zf.writestr(f"media/{rec['id']}", blob)
        return Response(buf.getvalue(), media_type="application/zip",
                        headers={"Content-Disposition": 'attachment; filename="marshie-backup-with-files.zip"'})
    data = excel_io.export_workbook(store.state["entries"], store.state["datasets"])
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="marshie-learned.xlsx"'})


@app.post("/api/admin/restore", dependencies=[Depends(admin)])
async def restore(file: UploadFile = File(...)):
    raw = await file.read(MAX_RESTORE + 1)
    if len(raw) > MAX_RESTORE:
        raise HTTPException(413, f"That backup is too big ({MAX_RESTORE // 1048576} MB max here).")
    blobs: dict[str, bytes] = {}
    try:
        if raw[:2] == b"PK":                  # a .zip backup with its files
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                if sum(i.file_size for i in zf.infolist()) > 2 * MAX_RESTORE:
                    raise ValueError("too large")
                data = json.loads(zf.read("knowledge.json").decode("utf-8"))
                for name in zf.namelist():
                    mid = name[6:] if name.startswith("media/") else ""
                    if media_mod.SAFE_ID.match(mid):
                        blobs[mid] = zf.read(name)
        else:
            data = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError("not a backup")
    except (ValueError, KeyError, zipfile.BadZipFile):
        raise HTTPException(400, "That doesn't look like a Marshie backup (.json or .zip) file.")
    added, dup = store.import_state(data, blobs)
    return {"ok": True, "added": added, "duplicates": dup, "files": len(blobs)}


# ============================================================================ serve the Vue app (Raspberry Pi)
if config.FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=config.FRONTEND_DIST, html=True), name="web")
else:
    @app.get("/")
    def no_frontend():
        return JSONResponse({"message": "Marshie's API is running. Build the face first: cd frontend && npm install && npm run build"})
