"""Everything Marshie knows and has learned, with swappable persistence.

* Built-in ("seed") knowledge is read from JSON files shipped with the app. It is never modified.
* Anything taught, uploaded or rated is "custom" state. It is saved to
    - data/state.json            (Raspberry Pi / any normal computer), or
    - an Upstash Redis / Vercel KV store when KV_REST_API_URL + KV_REST_API_TOKEN are set (Vercel).
  Without KV on Vercel the state lives in /tmp, which survives only while the function is warm.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import threading
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from . import config, i18n
from . import media as media_mod

STATE_KEY = "marshie_state"
VERSION_KEY = "marshie_version"
MAX_FEEDBACK = 2000
KV_MAX_STATE = 950_000          # Upstash's free plan accepts about 1 MB per request
MOODS = ("hello", "love", "laugh", "wow")      # faces an entry may ask for while she speaks it


class StorageError(RuntimeError):
    """Marshie could not keep something. The message is written for a teacher."""


def _norm(text: str) -> str:
    return " ".join(str(text).lower().split())


def _now() -> int:
    return int(time.time())


def new_state() -> dict[str, Any]:
    return {
        "revision": 0,
        "entries": [],       # custom entries (taught, uploaded)
        "datasets": [],      # student-gathered tables
        "weights": {},       # entry_id -> {"good": n, "bad": n}
        "feedback": [],      # recent ratings and corrections
        "uploads": [],       # history of Excel imports
        "settings": {},      # teacher-editable options
        "unknown": {},       # questions Marshie could not answer yet -> a to-learn list for teachers
        "media": [],         # pictures, sound and video (the bytes live in the blob store)
        "documents": [],     # PDFs, Word files, pasted text: the passages are ordinary entries with group == id
    }


# --------------------------------------------------------------------------- backends
class FileBackend:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict | None:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def save(self, state: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)             # may hold a paid AI key: only this user's account should read it
        except OSError:
            pass                              # Windows and some drives have no such permissions
        os.replace(tmp, self.path)           # atomic: a power cut can't leave half a file

    def remote_revision(self) -> int | None:
        return None


class KVBackend:
    """Minimal Upstash Redis REST client (also what Vercel KV uses)."""

    def __init__(self, url: str, token: str):
        self.url, self.token = url.rstrip("/"), token

    def _cmd(self, *args: str) -> Any:
        req = urllib.request.Request(
            self.url,
            data=json.dumps(list(args)).encode(),
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode()).get("result")

    def load(self) -> dict | None:
        try:
            raw = self._cmd("GET", STATE_KEY)
            return json.loads(raw) if raw else None
        except Exception:
            return None

    def save(self, state: dict) -> None:
        payload = json.dumps(state, ensure_ascii=False)
        if len(payload.encode("utf-8")) > KV_MAX_STATE:
            raise StorageError("Marshie's memory store is full (the free Upstash plan holds about 1 MB of text). "
                               "Delete some documents or tables, or upgrade the store.")
        self._cmd("SET", STATE_KEY, payload)
        self._cmd("SET", VERSION_KEY, str(state.get("revision", 0)))

    def set_raw(self, key: str, value: str) -> None:
        self._cmd("SET", key, value)

    def get_raw(self, key: str) -> str | None:
        return self._cmd("GET", key)

    def del_raw(self, key: str) -> None:
        self._cmd("DEL", key)

    def remote_revision(self) -> int | None:
        try:
            raw = self._cmd("GET", VERSION_KEY)
            return int(raw) if raw is not None else None
        except Exception:
            return None


# --------------------------------------------------------------------------- store
class Store:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.backend = (
            KVBackend(config.KV_URL, config.KV_TOKEN)
            if config.KV_URL and config.KV_TOKEN
            else FileBackend(config.STATE_FILE)
        )
        self.persistent = isinstance(self.backend, KVBackend) or not config.IS_VERCEL
        self.blobs = (media_mod.KVBlobs(self.backend) if isinstance(self.backend, KVBackend)
                      else media_mod.FileBlobs(config.MEDIA_DIR))
        self.seed: list[dict] = []
        self.state: dict[str, Any] = new_state()
        self._last_check = 0.0
        self.load_seed()
        self.reload()

    # ----- loading
    def load_seed(self) -> None:
        entries: list[dict] = []
        seen: set[str] = set()
        files = sorted(config.SEED_DIR.glob("*.json")) + sorted(config.CUSTOM_SEED_DIR.glob("*.json"))
        for f in files:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception as exc:                      # a bad file must not stop the school event
                print(f"[marshie] skipped {f.name}: {exc}")
                continue
            file_lang = ""
            if isinstance(data, dict):                    # also accept a state/export file, or {"lang": "fr", "entries": [...]}
                file_lang = str(data.get("lang") or "")
                data = data.get("entries", [])
            for raw in data:
                if file_lang and not raw.get("lang"):
                    raw = {**raw, "lang": file_lang}
                entry = self.make_entry(raw, via="seed")
                if entry and entry["fp"] not in seen:
                    seen.add(entry["fp"])
                    entries.append(entry)
        self.seed = entries

    def reload(self) -> None:
        with self.lock:
            loaded = self.backend.load()
            if loaded:
                merged = new_state()
                merged.update(loaded)
                self.state = merged
            self._last_check = time.time()

    def refresh_if_stale(self) -> None:
        """On Vercel several instances may be alive: pick up changes made on another."""
        if not isinstance(self.backend, KVBackend) or time.time() - self._last_check < 3:
            return
        with self.lock:
            self._last_check = time.time()
            remote = self.backend.remote_revision()
            if remote is not None and remote != self.state.get("revision"):
                self.reload()

    def save(self, strict: bool = False) -> None:
        """Keep the state. A child's thumbs-up must never crash anything, so by default a failure is only logged;
        teacher actions pass strict=True and get a StorageError they can read."""
        with self.lock:
            self.state["revision"] = int(self.state.get("revision", 0)) + 1
            try:
                self.backend.save(self.state)
            except StorageError:
                if strict:
                    raise
                print("[marshie] memory store is full; not saved")
            except Exception as exc:
                print(f"[marshie] could not save state: {exc}")
                if strict:
                    raise StorageError("Marshie could not save that. Check the connection to the memory store and try again.")

    @property
    def revision(self) -> int:
        return int(self.state.get("revision", 0))

    # ----- entries
    @staticmethod
    def make_entry(raw: dict, via: str = "teach", added_by: str = "") -> dict | None:
        q = raw.get("question") or raw.get("q") or ""
        aliases: list[str] = []
        if isinstance(q, list):
            aliases, q = q[1:], (q[0] if q else "")
        aliases = [str(a).strip() for a in (aliases + list(raw.get("aliases") or [])) if str(a).strip()]
        q, a = str(q).strip(), str(raw.get("answer") or raw.get("a") or "").strip()
        if not q or not a:
            return None
        kw = raw.get("keywords") or []
        if isinstance(kw, str):
            kw = [k.strip() for k in kw.replace(";", ",").split(",") if k.strip()]
        media = [str(m) for m in (raw.get("media") or []) if media_mod.SAFE_ID.match(str(m))]
        fp = hashlib.sha1((_norm(q) + "|" + _norm(a) + ("|" + ",".join(media) if media else "")).encode()).hexdigest()[:12]
        mood = str(raw.get("mood") or "")
        prefix = "s" if via == "seed" else "c"
        return {
            "id": f"{prefix}-{fp[:10]}" if via == "seed" else f"c-{uuid.uuid4().hex[:10]}",
            "fp": fp,
            "category": str(raw.get("category") or "General").strip() or "General",
            "question": q,
            "aliases": aliases,
            "answer": a,
            "short": str(raw.get("short") or "").strip(),
            "keywords": [str(k) for k in kw],
            "source": str(raw.get("source") or "").strip(),
            "level": str(raw.get("level") or "").strip(),
            "via": via,
            "added_by": added_by or str(raw.get("added_by") or ""),
            "created": int(raw.get("created") or _now()),
            "media": media,                                   # ids of pictures / sound shown with the answer
            "group": str(raw.get("group") or ""),             # the file or document this came from
            "upload": str(raw.get("upload") or ""),           # the Excel upload that added it (so the whole upload can be undone)
            "kind": "passage" if raw.get("kind") == "passage" else "",
            "mood": mood if mood in MOODS else "",
            "lang": i18n.clean(raw.get("lang")),              # en | fr | es | de: the language the question and answer are written in
        }

    def all_entries(self) -> list[dict]:
        """Everything Marshie may use when answering (pending items wait for teacher approval)."""
        return self.seed + [e for e in self.state["entries"] if e.get("status", "live") == "live"]

    def pending_entries(self) -> list[dict]:
        return [e for e in self.state["entries"] if e.get("status") == "pending"]

    def find_entry(self, entry_id: str) -> dict | None:
        return next((e for e in self.seed + self.state["entries"] if e["id"] == entry_id), None)

    def add_entries(self, raws: list[dict], via: str, added_by: str = "", status: str = "live",
                    strict: bool = False) -> tuple[int, int]:
        """Returns (added, duplicates_skipped). strict=True raises StorageError (and changes nothing) if it cannot be kept."""
        with self.lock:
            snap = copy.deepcopy(self.state) if strict else None
            known = {e["fp"] for e in self.seed + self.state["entries"]}
            added = dup = 0
            for raw in raws:
                entry = self.make_entry(raw, via=via, added_by=added_by)
                if not entry:
                    continue
                if entry["fp"] in known:
                    dup += 1
                    continue
                entry["status"] = status
                known.add(entry["fp"])
                self.state["entries"].append(entry)
                added += 1
            if added:
                try:
                    self.save(strict=strict)
                except StorageError:
                    self.state = snap
                    raise
            return added, dup

    def approve_entry(self, entry_id: str) -> bool:
        with self.lock:
            for e in self.state["entries"]:
                if e["id"] == entry_id and e.get("status") == "pending":
                    e["status"] = "live"
                    self.save()
                    return True
            return False

    def delete_entry(self, entry_id: str) -> bool:
        with self.lock:
            before = len(self.state["entries"])
            self.state["entries"] = [e for e in self.state["entries"] if e["id"] != entry_id]
            changed = len(self.state["entries"]) != before
            if changed:
                self.save()
            return changed

    # ----- pictures, sound, video
    def media_record(self, media_id: str) -> dict | None:
        return next((m for m in self.state["media"] if m["id"] == media_id), None)

    @staticmethod
    def _media_view(m: dict) -> dict:
        return {"id": m["id"], "kind": m["kind"], "mime": m["mime"], "title": m.get("title", ""),
                "size": m.get("size", 0), "url": f"/api/media/{m['id']}"}

    def media_public(self, ids: list[str]) -> list[dict]:
        """What the screen needs to show these files. Files that were deleted are skipped."""
        out = []
        for i in ids or []:
            m = self.media_record(i)
            if m:
                out.append(self._media_view(m))
        return out

    def add_media(self, data: bytes, kind: str, mime: str, title: str, filename: str, role: str = "") -> dict:
        """Keep a file. Raises MediaError (too big for this store) or StorageError."""
        if len(data) > self.blobs.max_bytes:
            raise media_mod.MediaError(
                f"That file is too big for this store ({len(data) / 1048576:.1f} MB; the limit here is "
                f"{self.blobs.max_bytes / 1048576:.1f} MB). Make it smaller, or run Marshie on a computer for bigger files.")
        rec = {"id": media_mod.new_id(), "kind": kind, "mime": mime, "size": len(data), "title": title.strip()[:120],
               "filename": (filename or "")[:160], "role": role, "created": _now()}
        try:
            self.blobs.put(rec["id"], data)
        except media_mod.MediaError:
            raise
        except Exception as exc:
            print(f"[marshie] could not keep file: {exc}")
            raise StorageError("Marshie could not keep that file. Check the disk or the memory store and try again.")
        with self.lock:
            snap = copy.deepcopy(self.state)
            self.state["media"].append(rec)
            try:
                self.save(strict=True)
            except StorageError:
                self.state = snap
                self.blobs.delete(rec["id"])
                raise
        return rec

    def get_blob(self, media_id: str) -> tuple[bytes, str] | None:
        rec = self.media_record(media_id)
        data = self.blobs.get(media_id) if rec else None
        return (data, rec["mime"]) if rec and data is not None else None

    def delete_media(self, media_id: str) -> bool:
        with self.lock:
            rec = self.media_record(media_id)
            if not rec:
                return False
            self.state["media"] = [m for m in self.state["media"] if m["id"] != media_id]
            self.state["entries"] = [e for e in self.state["entries"] if e.get("group") != media_id]
            for e in self.state["entries"]:
                if media_id in e.get("media", []):
                    e["media"] = [m for m in e["media"] if m != media_id]
            if self.state["settings"].get("logo") == media_id:
                self.state["settings"].pop("logo", None)
            self.save()
        self.blobs.delete(media_id)
        return True

    # ----- documents
    def add_document(self, title: str, filename: str, passages: list[str], category: str, lead_fn,
                     replace_same_file: bool = True) -> dict:
        """Store a document as passages. A document with the same file name is replaced (updated)."""
        title = title.strip()[:120] or "Document"
        doc_id = "doc-" + uuid.uuid4().hex[:8]
        words = [w for w in title.replace("-", " ").split() if len(w) > 2][:6]
        raws = [{"question": f"{title}: {lead_fn(p)}", "answer": p, "category": category or "Documents",
                 "keywords": words, "source": f"From {filename or title}", "group": doc_id, "kind": "passage"}
                for p in passages]
        with self.lock:
            snap = copy.deepcopy(self.state)
            if replace_same_file and filename:
                for old in [d for d in self.state["documents"] if d.get("filename") == filename]:
                    self._drop_document(old["id"])
            added, _dup = self.add_entries(raws, via="document", added_by="Teacher", strict=False)
            rec = {"id": doc_id, "title": title, "filename": filename or "", "passages": added,
                   "chars": sum(len(p) for p in passages), "category": category or "Documents", "created": _now()}
            self.state["documents"].append(rec)
            try:
                self.save(strict=True)
            except StorageError:
                self.state = snap
                raise
        return rec

    def _drop_document(self, doc_id: str) -> bool:
        before = len(self.state["documents"])
        self.state["documents"] = [d for d in self.state["documents"] if d["id"] != doc_id]
        self.state["entries"] = [e for e in self.state["entries"] if e.get("group") != doc_id]
        return len(self.state["documents"]) != before

    def delete_document(self, doc_id: str) -> bool:
        with self.lock:
            changed = self._drop_document(doc_id)
            if changed:
                self.save()
            return changed

    def library(self) -> list[dict]:
        """Everything teachers have added that is not a single typed question, newest first."""
        counts: dict[str, int] = {}
        for e in self.state["entries"]:
            if e.get("group"):
                counts[e["group"]] = counts.get(e["group"], 0) + 1
        items = [{**self._media_view(m), "type": m["kind"], "filename": m.get("filename", ""), "created": m["created"],
                  "entries": counts.get(m["id"], 0)}
                 for m in self.state["media"] if m.get("role") != "logo"]
        items += [{"id": d["id"], "type": "document", "title": d["title"], "filename": d.get("filename", ""),
                   "size": d.get("chars", 0), "created": d["created"], "entries": counts.get(d["id"], d.get("passages", 0)),
                   "category": d.get("category", "")} for d in self.state["documents"]]
        return sorted(items, key=lambda i: -i["created"])

    def delete_library_item(self, item_id: str) -> bool:
        return self.delete_media(item_id) if item_id.startswith("m-") else self.delete_document(item_id)

    # ----- feedback
    def weight(self, entry_id: str) -> dict:
        return self.state["weights"].get(entry_id, {"good": 0, "bad": 0})

    def rate(self, question: str, entry_id: str | None, good: bool, correction: str = "") -> None:
        with self.lock:
            if entry_id:
                w = self.state["weights"].setdefault(entry_id, {"good": 0, "bad": 0})
                w["good" if good else "bad"] += 1
            self.state["feedback"].append(
                {"ts": _now(), "question": question, "entry_id": entry_id,
                 "rating": "good" if good else "bad", "correction": correction}
            )
            del self.state["feedback"][:-MAX_FEEDBACK]
            self.save()

    # ----- datasets (student-gathered tables)
    def add_dataset(self, name: str, columns: list[str], rows: list[list], source: str, upload: str = "") -> dict:
        with self.lock:
            self.state["datasets"] = [d for d in self.state["datasets"] if _norm(d["name"]) != _norm(name)]
            ds = {"id": f"d-{uuid.uuid4().hex[:8]}", "name": name, "columns": columns,
                  "rows": rows, "source": source, "created": _now()}
            if upload:
                ds["upload"] = upload
            self.state["datasets"].append(ds)
            self.save()
            return ds

    def delete_dataset(self, ds_id: str) -> bool:
        with self.lock:
            before = len(self.state["datasets"])
            self.state["datasets"] = [d for d in self.state["datasets"] if d["id"] != ds_id]
            changed = len(self.state["datasets"]) != before
            if changed:
                self.save()
            return changed

    def log_unknown(self, question: str) -> None:
        with self.lock:
            key = _norm(question)[:200]
            if not key:
                return
            u = self.state.setdefault("unknown", {})
            rec = u.setdefault(key, {"q": question[:300], "n": 0, "ts": _now()})
            rec["n"] += 1
            rec["ts"] = _now()
            if len(u) > 300:                                   # keep the most-asked
                for k, _ in sorted(u.items(), key=lambda kv: kv[1]["n"])[: len(u) - 300]:
                    u.pop(k, None)
            self.save()

    def resolve_unknown(self, question: str) -> None:
        with self.lock:
            if self.state.setdefault("unknown", {}).pop(_norm(question)[:200], None) is not None:
                self.save()

    def log_upload(self, filename: str, summary: dict, undo: dict | None = None) -> str:
        """Remember an upload. `undo` says what it added: {"batch": id} (Excel), {"media": id} or {"document": id}."""
        uid = "u-" + uuid.uuid4().hex[:8]
        with self.lock:
            rec = {"id": uid, "ts": _now(), "filename": filename, **summary}
            if undo:
                rec["undo"] = undo
            self.state["uploads"].append(rec)
            del self.state["uploads"][:-200]
            self.save()
        return uid

    def undo_upload(self, upload_id: str) -> dict | None:
        """Take back everything one upload added. Things the upload only replaced (a table or file with the same name) are
        not brought back, and facts that were already known before it are left alone. None if there is nothing to undo."""
        with self.lock:
            rec = next((u for u in self.state["uploads"] if u.get("id") == upload_id), None)
            if not rec or rec.get("undone") or not rec.get("undo"):
                return None
            what = rec["undo"]
            facts = tables = files = 0
            if what.get("batch"):
                before = len(self.state["entries"])
                self.state["entries"] = [e for e in self.state["entries"] if e.get("upload") != what["batch"]]
                facts += before - len(self.state["entries"])
                before = len(self.state["datasets"])
                self.state["datasets"] = [d for d in self.state["datasets"] if d.get("upload") != what["batch"]]
                tables += before - len(self.state["datasets"])
            if what.get("media"):
                n = sum(1 for e in self.state["entries"] if e.get("group") == what["media"])
                if self.delete_media(what["media"]):
                    files += 1
                    facts += n
            if what.get("document"):
                n = sum(1 for e in self.state["entries"] if e.get("group") == what["document"])
                if self.delete_document(what["document"]):
                    files += 1
                    facts += n
            rec["undone"] = _now()
            self.save()
            return {"facts": facts, "tables": tables, "files": files}

    # ----- settings / stats
    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.state["settings"].get(key, default)

    def set_settings(self, values: dict) -> None:
        with self.lock:
            old = dict(self.state["settings"])
            self.state["settings"].update(values)
            try:
                self.save(strict=True)
            except StorageError:
                self.state["settings"] = old
                raise

    def stats(self) -> dict:
        cats: dict[str, int] = {}
        for e in self.all_entries():
            cats[e["category"]] = cats.get(e["category"], 0) + 1
        fb = self.state["feedback"]
        return {
            "total_entries": len(self.seed) + len(self.state["entries"]),
            "built_in": len(self.seed),
            "learned": len(self.state["entries"]) - len(self.pending_entries()),
            "pending": len(self.pending_entries()),
            "datasets": len(self.state["datasets"]),
            "dataset_rows": sum(len(d["rows"]) for d in self.state["datasets"]),
            "categories": dict(sorted(cats.items())),
            "ratings_good": sum(1 for f in fb if f["rating"] == "good"),
            "ratings_bad": sum(1 for f in fb if f["rating"] == "bad"),
            "persistent": self.persistent,
            "storage": "kv" if isinstance(self.backend, KVBackend) else ("tmp" if config.IS_VERCEL else "file"),
            "media": sum(1 for m in self.state["media"] if m.get("role") != "logo"),
            "documents": len(self.state["documents"]),
            "state_kb": round(len(json.dumps(self.state, ensure_ascii=False).encode("utf-8")) / 1024),
            "state_limit_kb": round(KV_MAX_STATE / 1024) if isinstance(self.backend, KVBackend) else 0,
            "media_limit_mb": round(self.blobs.max_bytes / 1048576, 1),
        }

    def export_state(self) -> dict:
        with self.lock:
            return {"entries": list(self.state["entries"]), "datasets": list(self.state["datasets"]),
                    "media": list(self.state["media"]), "documents": list(self.state["documents"]),
                    "settings": {k: v for k, v in self.state["settings"].items() if k in ("greeting", "theme", "logo")},
                    "exported": _now()}

    def import_state(self, data: dict, blobs: dict[str, bytes] | None = None) -> tuple[int, int]:
        """Restore a backup. `blobs` maps media id -> bytes when the backup came as a .zip with its files."""
        with self.lock:
            snap = copy.deepcopy(self.state)
            kept: list[str] = []
            try:
                for rec in data.get("media", []) or []:
                    mid = str(rec.get("id", ""))
                    if not media_mod.SAFE_ID.match(mid) or not blobs or mid not in blobs or self.media_record(mid):
                        continue
                    if len(blobs[mid]) > self.blobs.max_bytes:
                        continue
                    self.blobs.put(mid, blobs[mid])
                    kept.append(mid)
                    self.state["media"].append({k: rec.get(k, "") for k in
                                                ("id", "kind", "mime", "size", "title", "filename", "role", "created")})
                for doc in data.get("documents", []) or []:
                    if not any(d["id"] == doc.get("id") for d in self.state["documents"]):
                        self.state["documents"].append({k: doc.get(k, "") for k in
                                                        ("id", "title", "filename", "passages", "chars", "category", "created")})
                added, dup = self.add_entries(data.get("entries", []), via="import", strict=True)
                for ds in data.get("datasets", []):
                    self.add_dataset(ds["name"], ds["columns"], ds["rows"], ds.get("source", "import"))
                for key, value in (data.get("settings") or {}).items():
                    if key in ("greeting", "theme") and value:
                        self.state["settings"][key] = value
                    elif key == "logo" and value and self.media_record(value):
                        self.state["settings"]["logo"] = value
                self.save(strict=True)
            except Exception:
                self.state = snap
                for mid in kept:
                    self.blobs.delete(mid)
                raise
        return added, dup
