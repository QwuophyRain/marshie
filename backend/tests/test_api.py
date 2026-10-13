"""End-to-end checks for Marshie's API. Run:  python -m pytest backend/tests   (or: python backend/tests/test_api.py)"""
from __future__ import annotations

import io
import os
import re
import sys
import tempfile
from pathlib import Path

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="marshie_test_")
os.environ["ADMIN_PIN"] = "4321"
os.environ["SECRET_KEY"] = "test-secret"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient                 # noqa: E402
from openpyxl import load_workbook                         # noqa: E402

from app.main import app                                   # noqa: E402

client = TestClient(app)


def login() -> dict:
    r = client.post("/api/admin/login", json={"pin": "4321"})
    assert r.status_code == 200, r.text
    return {"X-Admin-Token": r.json()["token"]}


def test_health_and_builtin_knowledge():
    h = client.get("/api/health").json()
    assert h["ok"] and h["entries"] > 500
    r = client.post("/api/ask", json={"question": "What is the capital of Ghana?"}).json()
    assert r["source"] == "knowledge" and "Accra" in r["answer"]
    assert client.post("/api/ask", json={"question": "what is 12 plus 7"}).json()["answer"].endswith("19")


def test_unknown_then_teach_then_remember():
    q = "What is the name of our school mascot, the purple lion?"
    r = client.post("/api/ask", json={"question": q}).json()
    assert r["source"] == "unknown" and r["can_teach"]
    t = client.post("/api/teach", json={"question": q, "answer": "Our mascot is Leo the purple lion.", "taught_by": "Ama"}).json()
    assert t["ok"] and t["added"] == 1
    again = client.post("/api/ask", json={"question": q}).json()
    assert "Leo" in again["answer"] and again["source"] == "knowledge"


def test_wrong_answer_is_corrected_and_correct_one_wins():
    q = "What is the capital of Ghana?"
    first = client.post("/api/ask", json={"question": q}).json()
    fb = client.post("/api/feedback", json={"question": q, "entry_id": first["entry_id"], "good": False,
                                            "correction": "Accra, on the Atlantic coast."}).json()
    assert fb["ok"] and fb["mood"] == "happy"
    after = client.post("/api/ask", json={"question": q}).json()
    assert "Atlantic coast" in after["answer"]


def test_thumbs_up_celebrates():
    r = client.post("/api/feedback", json={"question": "hi", "entry_id": None, "good": True}).json()
    assert r["mood"] == "celebrate"


def test_rude_input_is_refused():
    r = client.post("/api/ask", json={"question": "you are a bitch"}).json()
    assert r["source"] == "refused"
    t = client.post("/api/teach", json={"question": "what is this", "answer": "this is shit"}).json()
    assert not t["ok"]


def test_admin_requires_pin():
    assert client.get("/api/admin/overview").status_code == 401
    assert client.post("/api/admin/login", json={"pin": "0000"}).status_code == 401
    assert client.get("/api/admin/overview", headers=login()).status_code == 200


def test_template_upload_and_dataset_questions():
    h = login()
    t = client.get("/api/admin/template", params={"kind": "all", "class_name": "Class 5", "category": "Science",
                                                  "columns": "Student,Plant,Week 1 (cm),Week 2 (cm)",
                                                  "dataset_name": "Bean growth", "rows": 20}, headers=h)
    assert t.status_code == 200 and t.content[:2] == b"PK"
    wb = load_workbook(io.BytesIO(t.content))
    qa, da = wb["Q&A"], wb["Data"]
    qa["B3"], qa["C3"], qa["D3"] = "What is the school garden crop?", "The school garden grows beans and tomatoes.", "garden, crop"
    qa["B4"], qa["C4"] = "Which bean plant is the tallest in the garden?", "The tallest bean plant is the one by the gate."
    for i, row in enumerate([("Ama", "Bean", 3.5, 6.1), ("Kofi", "Bean", 4.0, 7.2), ("Esi", "Bean", 2.8, 5.0)], 3):
        for j, v in enumerate(row, 1):
            da.cell(row=i, column=j, value=v)
    buf = io.BytesIO()
    wb.save(buf)
    files = {"file": ("class5.xlsx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}

    preview = client.post("/api/admin/upload", headers=h, files=files, data={"commit": "false"}).json()
    assert preview["to_add"] == 2 and preview["datasets"][0]["rows"] == 3 and not preview["committed"]

    done = client.post("/api/admin/upload", headers=h, files=files, data={"commit": "true"}).json()
    assert done["committed"] and done["added"] == 2 and done["datasets_added"] == 1

    assert "beans" in client.post("/api/ask", json={"question": "What is the school garden crop?"}).json()["answer"]
    # a question typed word for word into the sheet wins over a guess from the data table
    exact = client.post("/api/ask", json={"question": "Which bean plant is the tallest in the garden?"}).json()
    assert exact["source"] == "knowledge" and "gate" in exact["answer"], exact
    avg = client.post("/api/ask", json={"question": "What is the average Week 2 height in the bean growth data?"}).json()
    assert avg["source"] == "dataset" and "6.1" in avg["answer"], avg
    tall = client.post("/api/ask", json={"question": "Who has the highest week 1 in the bean growth data?"}).json()
    assert "Kofi" in tall["answer"], tall
    one = client.post("/api/ask", json={"question": "What is Esi's week 2 in the bean growth data?"}).json()
    assert "5" in one["answer"], one


def test_undo_an_upload():
    h = login()
    # a fact that was already known stays when the upload that repeated it is undone
    client.post("/api/admin/entries", json={"question": "What does the pond heron eat?", "answer": "The pond heron eats small fish.",
                                            "category": "Animals"}, headers=h)
    t = client.get("/api/admin/template", params={"kind": "all", "columns": "Student,Reading", "dataset_name": "Rain gauge", "rows": 10}, headers=h)
    wb = load_workbook(io.BytesIO(t.content))
    qa, da = wb["Q&A"], wb["Data"]
    qa["B3"], qa["C3"] = "What does the pond heron eat?", "The pond heron eats small fish."
    qa["B4"], qa["C4"] = "Where does the pond heron sleep?", "The pond heron sleeps in the tall trees."
    for i, row in enumerate([("Ama", 12), ("Kofi", 7)], 3):
        for j, v in enumerate(row, 1):
            da.cell(row=i, column=j, value=v)
    buf = io.BytesIO()
    wb.save(buf)
    done = client.post("/api/admin/upload", headers=h, data={"commit": "true"},
                       files={"file": ("undo-me.xlsx", buf.getvalue(), "application/octet-stream")}).json()
    assert done["added"] == 1 and done["duplicates"] == 1 and done["datasets_added"] == 1, done

    def row(name):
        return next(u for u in client.get("/api/admin/overview", headers=h).json()["uploads"] if u["filename"] == name)
    up = row("undo-me.xlsx")
    assert up["can_undo"] and up["id"].startswith("u-") and "undo" not in up
    assert "tall trees" in client.post("/api/ask", json={"question": "Where does the pond heron sleep?"}).json()["answer"]

    assert client.post(f"/api/admin/uploads/{up['id']}/undo").status_code == 401           # teachers only
    r = client.post(f"/api/admin/uploads/{up['id']}/undo", headers=h)
    assert r.status_code == 200 and r.json() == {"ok": True, "facts": 1, "tables": 1, "files": 0}, r.text
    assert "tall trees" not in client.post("/api/ask", json={"question": "Where does the pond heron sleep?"}).json()["answer"]
    assert "small fish" in client.post("/api/ask", json={"question": "What does the pond heron eat?"}).json()["answer"]
    assert all(d["name"] != "Rain gauge" for d in client.get("/api/admin/overview", headers=h).json()["datasets"])
    assert not row("undo-me.xlsx")["can_undo"]
    assert client.post(f"/api/admin/uploads/{up['id']}/undo", headers=h).status_code == 404   # already undone
    assert client.post("/api/admin/uploads/u-nothing/undo", headers=h).status_code == 404

    # a picture: the file and what Marshie learned about it go away together
    m = client.post("/api/admin/media", headers=h, files={"file": ("zebra.png", tiny_png(), "image/png")},
                    data={"title": "Undo zebra", "say": "A zebra has black and white stripes."}).json()
    mid = m["media"]["id"]
    assert client.get(f"/api/media/{mid}").status_code == 200
    r = client.post(f"/api/admin/uploads/{row('zebra.png')['id']}/undo", headers=h)
    assert r.status_code == 200 and r.json()["files"] == 1 and r.json()["facts"] >= 1, r.text
    assert client.get(f"/api/media/{mid}").status_code == 404
    assert not client.post("/api/ask", json={"question": "show me the undo zebra"}).json()["media"]

    # a document
    d = client.post("/api/admin/document", headers=h, data={"commit": "true", "title": "Undo notes",
                    "text": "The school library opens at seven in the morning and closes at four in the afternoon every day."}).json()
    assert d["added"] >= 1
    name = next(u for u in client.get("/api/admin/overview", headers=h).json()["uploads"] if u.get("kind") == "document" and u["filename"] == "Undo notes")
    assert client.post(f"/api/admin/uploads/{name['id']}/undo", headers=h).json()["files"] == 1
    assert all(i["title"] != "Undo notes" for i in client.get("/api/admin/library", headers=h).json()["items"])


def test_vercel_rewrite_gives_the_api_the_right_address():
    """vercel.json sends /api/... to one function. Whichever address that function is handed, the API must answer."""
    from app.vercel_path import VercelPath
    web = TestClient(VercelPath(app))
    # the runtime hands over only the rewrite target (/api/index) and the real address in ?__p=
    r = web.post("/api/index?__p=admin/login", json={"pin": "4321"})
    assert r.status_code == 200 and r.json()["token"], r.text
    assert web.post("/api/index?__p=admin/login", json={"pin": "0000"}).status_code == 401      # not "Method Not Allowed"
    assert web.get("/api/index?__p=health").json()["name"] == "Marshie"
    # other query values survive, and the helper values do not leak into the app
    q = web.get("/api/index?__p=quiz&category=Science&level=1&rest=quiz")
    assert q.status_code == 200 and q.json()["question"], q.text
    h = {"X-Admin-Token": r.json()["token"]}
    assert web.get("/api/index?__p=admin/overview", headers=h).status_code == 200
    # only the captured part arrives (Vercel added it by itself)
    assert web.post("/api/index?rest=admin/login", json={"pin": "4321"}).status_code == 200
    # the runtime hands over the real address as well: still fine, with or without the helper value
    assert web.post("/api/admin/login", json={"pin": "4321"}).status_code == 200
    assert web.post("/api/admin/login?__p=admin/login", json={"pin": "4321"}).status_code == 200
    assert web.get("/api/health").status_code == 200
    # a helper value that was never filled in is ignored, and so is a strange one
    assert web.get("/api/health?__p=:rest*").status_code == 200
    assert web.get("/api/health?__p=../../etc").status_code in (200, 404)


def test_vercel_mode_switches_the_address_fix_on():
    """On Vercel (the VERCEL variable is set) the app itself puts the real address back, so the login works."""
    import subprocess
    code = (
        "from fastapi.testclient import TestClient\n"
        "from app.main import app\n"
        "c = TestClient(app)\n"
        "print(c.post('/api/index?__p=admin/login', json={'pin': '4321'}).status_code,"
        " c.post('/api/index?__p=admin/login', json={'pin': '1'}).status_code,"
        " c.get('/api/index?__p=health').status_code,"
        " c.post('/api/admin/login', json={'pin': '4321'}).status_code)\n"
    )
    env = {**os.environ, "VERCEL": "1", "DATA_DIR": tempfile.mkdtemp(prefix="marshie_vercel_"), "ADMIN_PIN": "4321"}
    out = subprocess.run([sys.executable, "-c", code], env=env, cwd=str(Path(__file__).resolve().parents[1]),
                         capture_output=True, text=True, timeout=120)
    assert out.stdout.split()[-4:] == ["200", "401", "200", "200"], out.stdout + out.stderr
    # and off Vercel the same unusual address is NOT silently accepted
    env.pop("VERCEL")
    out = subprocess.run([sys.executable, "-c", code], env=env, cwd=str(Path(__file__).resolve().parents[1]),
                         capture_output=True, text=True, timeout=120)
    assert out.stdout.split()[-4] == "405", out.stdout + out.stderr


def test_online_teacher_panel_stays_locked_until_pin_and_key_are_set():
    """On Vercel the site is public, so the starting PIN or a missing secret key must never open the Teacher panel."""
    import subprocess
    code = (
        "import hashlib, hmac, base64, json, time\n"
        "from fastapi.testclient import TestClient\n"
        "from app.main import app\n"
        "c = TestClient(app)\n"
        "r1 = c.post('/api/admin/login', json={'pin': '2468'}).status_code\n"
        "r2 = c.get('/api/admin/overview', headers={'X-Admin-Token': 'forged'}).status_code\n"
        "r3 = c.post('/api/admin/login', json={'pin': '9137'}).status_code\n"
        "print(r1, r2, r3, c.get('/api/health').status_code)\n"
    )
    here = str(Path(__file__).resolve().parents[1])

    def run(extra):
        env = {k: v for k, v in os.environ.items() if k not in ("ADMIN_PIN", "SECRET_KEY")}
        env.update({"VERCEL": "1", "DATA_DIR": tempfile.mkdtemp(prefix="marshie_lock_"), **extra})
        out = subprocess.run([sys.executable, "-c", code], env=env, cwd=here, capture_output=True, text=True, timeout=120)
        return out.stdout.split()[-4:], out.stdout + out.stderr

    assert run({})[0] == ["403", "403", "403", "200"], run({})[1]                                   # nothing set
    assert run({"ADMIN_PIN": "2468", "SECRET_KEY": "x" * 30})[0][0] == "403"                         # still the starting PIN
    assert run({"ADMIN_PIN": "9137"})[0][2] == "403"                                                 # PIN set, no secret key
    got, why = run({"ADMIN_PIN": "9137", "SECRET_KEY": "x" * 30})
    assert got == ["401", "401", "200", "200"], why                                                  # both set: opens normally


def test_export_backup_and_restore():
    h = login()
    x = client.get("/api/admin/export", params={"format": "xlsx"}, headers=h)
    assert x.status_code == 200 and x.content[:2] == b"PK"
    j = client.get("/api/admin/export", params={"format": "json"}, headers=h)
    assert j.status_code == 200 and "entries" in j.json()


def test_moderation_queue():
    h = login()
    client.post("/api/admin/settings", json={"moderate_teaching": True}, headers=h)
    q = "What colour is the school gate?"
    t = client.post("/api/teach", json={"question": q, "answer": "The school gate is bright green."}).json()
    assert t["ok"] and t["pending"]
    assert client.post("/api/ask", json={"question": q}).json()["source"] != "knowledge"
    pending = client.get("/api/admin/entries", params={"status": "pending"}, headers=h).json()["entries"]
    assert pending
    assert client.post(f"/api/admin/entries/{pending[0]['id']}/approve", headers=h).status_code == 200
    assert "green" in client.post("/api/ask", json={"question": q}).json()["answer"]
    client.post("/api/admin/settings", json={"moderate_teaching": False}, headers=h)


def test_quiz_math_and_knowledge():
    qz = client.get("/api/quiz", params={"category": "Arithmetic"}).json()
    assert qz["kind"] == "math" and qz["token"]
    bad = client.post("/api/quiz/check", json={"kind": "math", "response": "-999", "question": qz["question"], "token": qz["token"]}).json()
    assert bad["correct"] is False
    for _ in range(40):                                    # a knowledge question shows up eventually
        k = client.get("/api/quiz").json()
        if k["kind"] == "knowledge":
            break
    assert k["kind"] == "knowledge"
    # answering with the short answer is accepted
    from app.main import store
    entry = store.find_entry(k["entry_id"])
    ok = client.post("/api/quiz/check", json={"kind": "knowledge", "response": entry["short"], "entry_id": k["entry_id"]}).json()
    assert ok["correct"] is True


def test_tts_stt_gracefully_unavailable_here():
    assert client.post("/api/tts", json={"text": "hello"}).status_code in (200, 501)
    assert client.post("/api/stt", content=b"\x00\x00" * 100).status_code in (200, 501)



# ----------------------------------------------------------------------------------------- school, media, documents
import struct                                              # noqa: E402
import wave                                                # noqa: E402
import zipfile                                             # noqa: E402
import zlib                                                # noqa: E402


def tiny_png(rgb=(4, 88, 112)) -> bytes:
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"\x00" + bytes(rgb)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def tiny_wav() -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * 8000)
    return buf.getvalue()


def tiny_docx(paragraphs: list[str]) -> bytes:
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    xml = ('<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           f"<w:body>{body}</w:body></w:document>")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", xml)
    return buf.getvalue()


def test_school_greeting_and_colours():
    h = client.get("/api/health").json()
    assert h["school"] == "Ecole Ronsard" and "STEAM Program 2026" in h["event"]
    g = h["greeting"]
    assert g.startswith("Hello! My name is Marshie") and "Ecole Ronsard STEAM (Science, Technology, English, Agriculture & Arts, and Mathematics) Program 2026" in g
    assert g.endswith("How may I be of assistance?")
    assert "Ay-kol Ron-sar" in h["greeting_spoken"] and "Agriculture and Arts" in h["greeting_spoken"]
    assert h["theme"] == {"primary": "#045870", "button": "#fae240", "highlight": "#e80075", "success": "#74bd54"}
    assert h["logo"] is None


def test_school_knowledge_is_there():
    r = client.post("/api/ask", json={"question": "what is the school website"}).json()
    assert r["source"] == "knowledge" and "ecole-ronsard.com" in r["answer"]
    assert "ecole ronsard dot com" not in r["spoken"].lower() and "dot com" in r["spoken"]
    r = client.post("/api/ask", json={"question": "how can I contact the school"}).json()
    assert "+233" in r["answer"] and "plus 2 3 3" in r["spoken"] and " at " in r["spoken"]
    r = client.post("/api/ask", json={"question": "what does steam stand for"}).json()
    assert "Agriculture" in r["answer"] and "English" in r["answer"]
    r = client.post("/api/ask", json={"question": "who is the principal"}).json()
    assert "Agbenyeke" in r["answer"]


def test_expressive_moods_and_spoken_years():
    assert client.post("/api/ask", json={"question": "tell me a joke"}).json()["mood"] == "laugh"
    assert client.post("/api/ask", json={"question": "thank you"}).json()["mood"] == "love"
    assert client.post("/api/ask", json={"question": "hello"}).json()["mood"] == "hello"
    from app.brain import speakable
    assert speakable("It lasted 1957-1960. 12 - 4 = 8, 3 * 4 = 12") == "It lasted 1957 to 1960. 12 minus 4 is 8, 3 times 4 is 12"


def test_picture_upload_show_and_delete():
    h = login()
    files = {"file": ("ghana map.png", tiny_png(), "image/png")}
    r = client.post("/api/admin/media", files=files, data={"title": "Map of Ghana", "say": "This is the map of Ghana, with its ten regions.",
                                                         "questions": "where is kumasi on the map"}, headers=h)
    assert r.status_code == 200, r.text
    mid = r.json()["media"]["id"]
    a = client.post("/api/ask", json={"question": "show me the map of ghana"}).json()
    assert a["media"] and a["media"][0]["id"] == mid and a["media"][0]["kind"] == "image"
    assert "ten regions" in a["answer"]
    b = client.post("/api/ask", json={"question": "where is kumasi on the map"}).json()
    assert b["media"] and b["media"][0]["id"] == mid
    img = client.get(a["media"][0]["url"])
    assert img.status_code == 200 and img.headers["content-type"] == "image/png" and img.content[:4] == b"\x89PNG"
    assert img.headers["x-content-type-options"] == "nosniff"
    lib = client.get("/api/admin/library", headers=h).json()["items"]
    assert any(i["id"] == mid and i["type"] == "image" for i in lib)
    assert client.delete(f"/api/admin/library/{mid}", headers=h).status_code == 200
    assert client.get(f"/api/media/{mid}").status_code == 404
    assert not client.post("/api/ask", json={"question": "show me the map of ghana"}).json()["media"]


def test_media_checks():
    h = login()
    bad = client.post("/api/admin/media", files={"file": ("x.png", b"this is not a picture", "image/png")}, headers=h)
    assert bad.status_code == 400 and "real picture" in bad.json()["detail"]
    odd = client.post("/api/admin/media", files={"file": ("x.exe", b"MZ....", "application/octet-stream")}, headers=h)
    assert odd.status_code == 400
    assert client.post("/api/admin/media", files={"file": ("a.png", tiny_png(), "image/png")}).status_code == 401
    assert client.get("/api/media/m-nothere").status_code == 404
    assert client.get("/api/media/..%2f..%2fstate").status_code in (404, 422)


def test_audio_with_transcript_and_byte_ranges():
    h = login()
    transcript = ("The talking drum is played at festivals in Kumasi. The drummer squeezes the strings to change the pitch. "
                  "Long ago, drummers carried messages between villages with these drums.")
    r = client.post("/api/admin/media", files={"file": ("drum.wav", tiny_wav(), "audio/wav")}, headers=h,
                    data={"title": "Talking drum", "transcript": transcript})
    assert r.status_code == 200, r.text
    mid = r.json()["media"]["id"]
    assert r.json()["added"] >= 2
    a = client.post("/api/ask", json={"question": "play the talking drum"}).json()
    assert a["media"] and a["media"][0]["kind"] == "audio"
    b = client.post("/api/ask", json={"question": "how do drummers change the pitch of the drum"}).json()
    assert "squeezes the strings" in b["answer"] and b["media"] and b["source"] == "knowledge"
    full = client.get(f"/api/media/{mid}")
    part = client.get(f"/api/media/{mid}", headers={"Range": "bytes=0-99"})
    assert part.status_code == 206 and len(part.content) == 100
    assert part.headers["content-range"] == f"bytes 0-99/{len(full.content)}"
    tail = client.get(f"/api/media/{mid}", headers={"Range": "bytes=-10"})
    assert tail.status_code == 206 and tail.content == full.content[-10:]
    assert client.get(f"/api/media/{mid}", headers={"Range": f"bytes={len(full.content) + 5}-"}).status_code == 416
    assert client.delete(f"/api/admin/library/{mid}", headers=h).status_code == 200
    gone = client.post("/api/ask", json={"question": "how do drummers change the pitch of the drum"}).json()
    assert "squeezes the strings" not in gone["answer"]


def test_document_upload_becomes_findable_passages():
    h = login()
    text = ("The school garden was planted by Class 5 in March. They grew tomatoes, peppers and okra beside the science block. "
            "Every Friday the children water the plants and write down how tall each one has grown.\n\n"
            "Compost is made from vegetable peelings and dry leaves. The worms in the compost bin turn the waste into rich soil. "
            "Nothing from the kitchen is thrown away if it can feed the garden.")
    prev = client.post("/api/admin/document", files={"file": ("garden-notes.txt", text.encode(), "text/plain")}, headers=h).json()
    assert prev["passages"] >= 1 and not prev["committed"] and prev["title"] == "garden notes"
    done = client.post("/api/admin/document", files={"file": ("garden-notes.txt", text.encode(), "text/plain")},
                       data={"commit": "true", "category": "Science"}, headers=h).json()
    assert done["committed"] and done["added"] >= 1
    a = client.post("/api/ask", json={"question": "what do the worms in the compost bin do"}).json()
    assert "rich soil" in a["answer"] and a["source"] == "knowledge"
    b = client.post("/api/ask", json={"question": "which vegetables did class 5 grow in the garden"}).json()
    assert "okra" in b["answer"]
    # the same file again replaces it, it does not pile up
    n_before = len([e for e in client.get("/api/admin/entries?via=document&limit=200", headers=h).json()["entries"]])
    client.post("/api/admin/document", files={"file": ("garden-notes.txt", text.encode(), "text/plain")}, data={"commit": "true"}, headers=h)
    n_after = len([e for e in client.get("/api/admin/entries?via=document&limit=200", headers=h).json()["entries"]])
    assert n_after == n_before
    # an unrelated question must not be answered from the garden notes
    c = client.post("/api/ask", json={"question": "who won the world cup in 1966"}).json()
    assert "rich soil" not in c["answer"] and "okra" not in c["answer"]
    doc = next(i for i in client.get("/api/admin/library", headers=h).json()["items"] if i["type"] == "document")
    assert client.delete(f"/api/admin/library/{doc['id']}", headers=h).status_code == 200
    assert "rich soil" not in client.post("/api/ask", json={"question": "what do the worms in the compost bin do"}).json()["answer"]


def test_short_taught_fact_beats_long_document_passage_and_headings_read_well():
    h = login()
    docx = tiny_docx(["Orchard notes", "Every Monday the orchard club picks ripe guavas near the east gate and weighs them. "
                      "The orchard is watered by hand because the pipes are old."])
    client.post("/api/admin/document", files={"file": ("orchard.docx", docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
                data={"commit": "true"}, headers=h)
    r = client.post("/api/ask", json={"question": "what do you know about the orchard club"}).json()
    assert r["answer"].startswith("Orchard notes. "), r["answer"]            # a heading ends like a title, not a run-on
    client.post("/api/teach", json={"question": "Tell me about the guava", "answer": "Guavas are sweet green fruits that grow in our school orchard."}, headers=h)
    a = client.post("/api/ask", json={"question": "tell me about the guava"}).json()
    assert a["answer"].startswith("Guavas are sweet"), a["answer"]
    b = client.post("/api/ask", json={"question": "Tell me about the orchard guava"}).json()
    assert "Guavas are sweet" in b["answer"] or "orchard" in b["answer"].lower()


def test_paid_ai_settings_are_safe_and_used():
    import json as _json
    import urllib.error

    from app import llm
    h = login()
    KEY = "sk-ant-TESTKEY1234567890"
    assert client.get("/api/admin/ai").status_code == 401
    v = client.get("/api/admin/ai", headers=h).json()
    assert v["enabled"] is False and v["source"] == "none" and any(p["id"] == "anthropic" for p in v["presets"])
    # typed things are checked, with words a teacher can act on
    assert client.put("/api/admin/ai", json={"provider": "anthropic"}, headers=h).status_code == 422
    assert client.put("/api/admin/ai", json={"provider": "anthropic", "key": "bad key with spaces"}, headers=h).status_code == 422
    assert client.put("/api/admin/ai", json={"provider": "openai", "key": KEY, "base_url": "ftp://nope"}, headers=h).status_code == 422
    assert client.put("/api/admin/ai", json={"provider": "openai", "base_url": "http://localhost:11434/v1"}, headers=h).status_code == 200   # free local AI needs no key
    client.delete("/api/admin/ai", headers=h)

    calls: list = []
    reply = {"text": "Plants drink water through their roots."}

    def fake_post(url, headers, payload):
        calls.append((url, headers, payload))
        if "anthropic.com" in url:
            return {"content": [{"type": "text", "text": reply["text"]}]}
        return {"choices": [{"message": {"content": reply["text"]}}]}

    real = llm._post
    llm._post = fake_post
    try:
        # test before saving: nothing is kept, the key is used for the request only
        t = client.post("/api/admin/ai/test", json={"provider": "anthropic", "key": KEY}, headers=h).json()
        assert t["ok"] and "roots" in t["reply"] and calls[-1][1]["x-api-key"] == KEY
        assert client.get("/api/admin/ai", headers=h).json()["saved"] is False
        # save it
        v = client.put("/api/admin/ai", json={"provider": "anthropic", "key": KEY, "model": "", "daily_limit": 20}, headers=h).json()
        assert v["enabled"] and v["provider"] == "anthropic" and v["model"] == "claude-haiku-5-5" and v["source"] == "admin"
        assert v["key_hint"] == "…7890" and v["has_key"] and v["daily_limit"] == 20
        # the key never leaves the server: not in any answer, the overview, the health check or any backup
        everything = [_json.dumps(v), client.get("/api/admin/ai", headers=h).text, client.get("/api/admin/overview", headers=h).text,
                      client.get("/api/health").text, client.get("/api/admin/export?format=json", headers=h).text,
                      client.get("/api/admin/export?format=zip", headers=h).content.decode("latin-1")]
        assert all("TESTKEY" not in blob for blob in everything)
        assert client.get("/api/health").json()["capabilities"]["llm"] is True
        # she asks the AI only when her own knowledge is not enough
        local = client.post("/api/ask", json={"question": "what is the capital of ghana"}).json()
        assert local["source"] != "llm"
        n = len(calls)
        a = client.post("/api/ask", json={"question": "flibber jabber wockle zorp quibble"}).json()
        assert a["source"] == "llm" and "roots" in a["answer"] and len(calls) == n + 1
        # an answer that is not child-safe is never passed on
        reply["text"] = "That is a load of shit."
        b = client.post("/api/ask", json={"question": "flibber jabber wockle zorp quibble"}).json()
        assert b["source"] != "llm" and "shit" not in b["answer"]
        reply["text"] = "Plants drink water through their roots."
        # the daily limit stops a surprise bill
        llm._usage.update(day=llm._today(), n=20)
        c = client.post("/api/ask", json={"question": "flibber jabber wockle zorp quibble"}).json()
        assert c["source"] != "llm"
        llm._usage.update(day="", n=0)
        # a key is not carried over to a different service
        r = client.put("/api/admin/ai", json={"provider": "openai", "base_url": "https://api.openai.com/v1"}, headers=h)
        assert r.status_code == 422
        # a restored backup cannot switch the AI on or change the key
        client.post("/api/admin/restore", files={"file": ("b.json", _json.dumps({"entries": [], "settings": {"ai": {"provider": "openai", "key": "sk-evil-123456789"}}}).encode(), "application/json")}, headers=h)
        assert client.get("/api/admin/ai", headers=h).json()["provider"] == "anthropic"
        # pause: the key stays saved, she stops asking
        v = client.put("/api/admin/ai", json={"provider": "anthropic", "enabled": False, "daily_limit": 20}, headers=h).json()
        assert not v["enabled"] and v["paused"] and v["has_key"]
        assert client.post("/api/ask", json={"question": "flibber jabber wockle zorp quibble"}).json()["source"] != "llm"
        # a key the service refuses gives a clear message, and the key is not echoed back
        def refuse(url, headers, payload):
            raise urllib.error.HTTPError(url, 401, "no", {}, io.BytesIO(b'{"error":{"message":"bad key ' + KEY.encode() + b'"}}'))
        llm._post = refuse
        t = client.post("/api/admin/ai/test", json={"provider": "anthropic", "key": KEY}, headers=h).json()
        assert not t["ok"] and "did not accept" in t["message"] and "TESTKEY" not in _json.dumps(t)
        # remove it
        v = client.delete("/api/admin/ai", headers=h).json()
        assert not v["enabled"] and not v["has_key"] and not v["saved"]
    finally:
        llm._post = real
        client.delete("/api/admin/ai", headers=h)
        llm._usage.update(day="", n=0)


def test_word_and_pdf_documents():
    h = login()
    docx = tiny_docx(["Adinkra symbols are made by stamping cloth with carved calabash stamps.",
                      "Gye Nyame means except God and is one of the best known symbols."])
    r = client.post("/api/admin/document", files={"file": ("Adinkra.docx", docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
                    data={"commit": "true"}, headers=h)
    assert r.status_code == 200 and r.json()["added"] >= 1, r.text
    assert "calabash" in client.post("/api/ask", json={"question": "how are adinkra symbols made"}).json()["answer"]
    bad = client.post("/api/admin/document", files={"file": ("broken.docx", b"not a zip", "application/octet-stream")}, headers=h)
    assert bad.status_code == 400
    try:
        import pypdf  # noqa: F401
    except ImportError:
        return
    content = b"BT /F1 12 Tf 72 720 Td (The kente cloth is woven in narrow strips by the Asante and Ewe weavers.) Tj ET"
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    pdf, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(pdf))
        pdf += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(pdf)
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offs)
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, xref)
    r = client.post("/api/admin/document", files={"file": ("kente.pdf", pdf, "application/pdf")}, data={"commit": "true"}, headers=h)
    assert r.status_code == 200, r.text
    assert "Asante" in client.post("/api/ask", json={"question": "who weaves kente cloth in narrow strips"}).json()["answer"]


def test_pasted_text_and_empty_file_errors():
    h = login()
    r = client.post("/api/admin/document", data={"text": "Our school choir practises every Wednesday after lunch in the hall.", "title": "Choir",
                                                "commit": "true"}, headers=h)
    assert r.status_code == 200 and r.json()["added"] == 1
    assert "Wednesday" in client.post("/api/ask", json={"question": "when does the choir practise"}).json()["answer"]
    assert client.post("/api/admin/document", data={"text": "hi"}, headers=h).status_code == 400
    assert client.post("/api/admin/document", files={"file": ("e.txt", b"", "text/plain")}, headers=h).status_code == 400


def test_greeting_theme_and_logo_settings():
    h = login()
    r = client.post("/api/admin/settings", json={"greeting": "Hi! I am {name} from {school}.", "theme": {"primary": "#112233", "button": "red", "bogus": "#ffffff"}}, headers=h)
    assert r.status_code == 200
    hl = client.get("/api/health").json()
    assert hl["greeting"] == "Hi! I am Marshie from Ecole Ronsard." and hl["theme"]["primary"] == "#112233"
    assert hl["theme"]["button"] == "#fae240" and "bogus" not in hl["theme"]          # bad colours are ignored
    ov = client.get("/api/admin/overview", headers=h).json()
    assert ov["settings"]["theme"] == {"primary": "#112233"} and ov["defaults"]["theme"]["primary"] == "#045870"
    lg = client.post("/api/admin/logo", files={"file": ("logo.png", tiny_png((200, 0, 0)), "image/png")}, headers=h)
    assert lg.status_code == 200
    url = client.get("/api/health").json()["logo"]
    assert url == lg.json()["logo"] and client.get(url).status_code == 200
    first = url
    client.post("/api/admin/logo", files={"file": ("logo2.png", tiny_png((0, 200, 0)), "image/png")}, headers=h)
    assert client.get(first).status_code == 404                                          # the old logo is cleaned up
    assert all(i["type"] != "image" or i["title"] != "School logo" for i in client.get("/api/admin/library", headers=h).json()["items"])
    assert client.post("/api/admin/logo", files={"file": ("a.mp3", b"ID3....", "audio/mpeg")}, headers=h).status_code == 400
    client.post("/api/admin/settings", json={"greeting": "", "theme": {}}, headers=h)
    client.delete("/api/admin/logo", headers=h)
    hl = client.get("/api/health").json()
    assert hl["greeting"].startswith("Hello! My name is Marshie") and hl["theme"]["primary"] == "#045870" and hl["logo"] is None


def test_zip_backup_keeps_pictures():
    h = login()
    r = client.post("/api/admin/media", files={"file": ("tree.png", tiny_png((10, 120, 20)), "image/png")}, data={"title": "Baobab tree"}, headers=h)
    mid = r.json()["media"]["id"]
    z = client.get("/api/admin/export?format=zip", headers=h)
    assert z.status_code == 200 and z.content[:2] == b"PK"
    with zipfile.ZipFile(io.BytesIO(z.content)) as zf:
        assert "knowledge.json" in zf.namelist() and f"media/{mid}" in zf.namelist()
    client.delete(f"/api/admin/library/{mid}", headers=h)
    assert client.get(f"/api/media/{mid}").status_code == 404
    back = client.post("/api/admin/restore", files={"file": ("backup.zip", z.content, "application/zip")}, headers=h)
    assert back.status_code == 200 and back.json()["files"] >= 1, back.text
    a = client.post("/api/ask", json={"question": "show me baobab tree"}).json()
    assert a["media"] and a["media"][0]["id"] == mid
    assert client.get(f"/api/media/{mid}").content[:4] == b"\x89PNG"
    assert client.post("/api/admin/restore", files={"file": ("junk.zip", b"PK\x03\x04junk", "application/zip")}, headers=h).status_code == 400
    client.delete(f"/api/admin/library/{mid}", headers=h)


def test_old_saved_entries_without_new_fields_still_work():
    from app.main import store
    store.state["entries"].append({"id": "c-old0000001", "fp": "oldfp0000001", "category": "Taught", "question": "what colour is the old gate",
                                   "aliases": [], "answer": "The old gate is blue.", "short": "", "keywords": [], "source": "", "level": "",
                                   "via": "teach", "added_by": "", "created": 1, "status": "live"})
    r = client.post("/api/ask", json={"question": "what colour is the old gate"}).json()
    assert "blue" in r["answer"] and r["media"] == []
    assert client.get("/api/admin/entries?q=old gate", headers=login()).status_code == 200


def test_online_memory_store_keeps_files_and_says_when_full():
    """Vercel keeps things in an Upstash/KV store. Here a dictionary plays that store."""
    from app import config, media as media_mod, store as store_mod
    fake: dict = {}

    def cmd(self, *args):
        op, key, *rest = args
        if op == "GET":
            return fake.get(key)
        if op == "SET":
            fake[key] = rest[0]
            return "OK"
        if op == "DEL":
            fake.pop(key, None)
            return 1
    saved = (config.KV_URL, config.KV_TOKEN, store_mod.KVBackend._cmd)
    config.KV_URL, config.KV_TOKEN, store_mod.KVBackend._cmd = "http://kv.test", "token", cmd
    try:
        s = store_mod.Store()
        assert s.stats()["storage"] == "kv" and s.blobs.max_bytes == 600 * 1024
        rec = s.add_media(tiny_png(), "image", "image/png", "Gate", "gate.png")
        assert f"marshie_media:{rec['id']}" in fake and s.get_blob(rec["id"])[0][:4] == b"\x89PNG"
        try:
            s.add_media(b"\x89PNG\r\n\x1a\n" + b"0" * (700 * 1024), "image", "image/png", "Big", "big.png")
            raise AssertionError("a file too big for the store was accepted")
        except media_mod.MediaError as exc:
            assert "too big" in str(exc)
        before = (len(s.state["entries"]), fake[store_mod.STATE_KEY])
        lots = ["Passage number %d about the garden and its many plants, written to fill the store. " % i * 5 for i in range(2500)]
        try:
            s.add_document("Huge", "huge.txt", lots, "Science", lambda p: p[:20])
            raise AssertionError("the store should have been full")
        except store_mod.StorageError as exc:
            assert "full" in str(exc)
        assert (len(s.state["entries"]), fake[store_mod.STATE_KEY]) == before and not s.state["documents"]     # nothing half-saved
        assert s.delete_media(rec["id"]) and f"marshie_media:{rec['id']}" not in fake
    finally:
        config.KV_URL, config.KV_TOKEN, store_mod.KVBackend._cmd = saved


# ----------------------------------------------------------------------------------------- French, Spanish and German
def ask_in(lang: str, question: str) -> dict:
    from app.main import _hits
    _hits.clear()                                          # these tests ask more than the 60-a-minute guard allows
    r = client.post("/api/ask", json={"question": question, "lang": lang})
    assert r.status_code == 200, r.text
    return r.json()


def test_marshie_answers_in_french_spanish_and_german():
    fr = ask_in("fr", "Qui est la directrice de l'école ?")
    assert fr["source"] == "knowledge" and "Agbenyeke" in fr["answer"] and fr["lang"] == "fr"
    assert "Kinshasa" in ask_in("fr", "ou est notre ecole")["answer"]                 # a keyboard without accents is fine
    assert "ocho" in ask_in("es", "¿Cuántos planetas hay?")["answer"]
    assert "Naturwissenschaften" in ask_in("de", "Wofür steht STEAM?")["answer"]
    assert "Accra" in ask_in("de", "Was ist die Hauptstadt von Ghana?")["answer"]
    for lang, hello in (("fr", "Bonjour"), ("es", "Hola"), ("de", "Hallo")):            # small talk is in her own language
        r = ask_in(lang, hello)
        assert r["source"] == "knowledge" and r["lang"] == lang and "Marshie" in r["answer"] or "friend" not in r["answer"].lower()
    # English is unchanged, and a French sentence does not leak into English answers
    assert "Principal" in ask_in("en", "Who is the principal?")["answer"]
    assert ask_in("en", "Qui est la directrice de l'école ?")["source"] != "knowledge" or "Agbenyeke" not in ask_in("en", "Qui est la directrice de l'école ?")["answer"]
    # not knowing is said in the child's language, and she asks to be taught
    u = ask_in("fr", "flibber jabber wockle zorp quibble")
    assert u["source"] == "unknown" and u["can_teach"] and "don't" not in u["answer"] and u["lang"] == "fr"
    assert ask_in("es", "")["lang"] == "es"


def test_other_languages_have_a_greeting_and_a_list():
    h = client.get("/api/health").json()
    assert [x["code"] for x in h["languages"]] == ["en", "fr", "es", "de"]
    for lang, word in (("fr", "Bonjour"), ("es", "Hola"), ("de", "Hallo")):
        g = client.get("/api/greeting", params={"lang": lang}).json()
        assert word in g["text"][:9] and "Marshie" in g["text"] and g["lang"] == lang and g["spoken"]
    assert client.get("/api/greeting", params={"lang": "xx"}).json()["text"].startswith("Hello")      # unknown = English


def test_sums_are_understood_and_read_aloud_in_each_language():
    r = ask_in("fr", "Combien font 12 fois 7 ?")
    assert r["source"] == "math" and r["answer"].endswith("84") and "fois" in r["spoken"] and "égale" in r["spoken"]
    assert ask_in("fr", "quatre-vingt-dix moins sept")["answer"].endswith("83")
    assert ask_in("es", "¿Cuánto es treinta y cinco menos diez?")["answer"].endswith("25")
    assert ask_in("es", "raíz cuadrada de 81")["answer"].endswith("9")
    de = ask_in("de", "Was ist 12 mal 7?")
    assert de["source"] == "math" and de["answer"].endswith("84") and "mal" in de["spoken"] and " ist " in de["spoken"]
    assert "durch null" in ask_in("de", "Was ist 10 geteilt durch 0")["answer"]
    assert ask_in("fr", "2,5 fois 4")["answer"].startswith("2,5") and ask_in("fr", "2,5 fois 4")["answer"].endswith("10")
    from app.brain import speakable
    assert speakable("3 * 4 = 12", "fr") == "3 fois 4 égale 12"
    assert speakable("3 * 4 = 12", "es") == "3 por 4 es igual a 12"
    assert speakable("Son e-mail est a@b.com", "de") == "Son e-mail est a at b Punkt com"


def test_quiz_in_french_spanish_and_german():
    for lang, start in (("fr", "Combien font"), ("es", "¿Cuánto es"), ("de", "Was ist")):
        qz = client.get("/api/quiz", params={"category": "Arithmetic", "lang": lang}).json()
        assert qz["kind"] == "math" and qz["question"].startswith(start), qz
        a, b = [int(x) for x in re.findall(r"\d+", qz["question"])]
        op = "+" if re.search(r"plus|más", qz["question"]) else "-" if re.search(r"moins|menos|minus", qz["question"]) else "*" if re.search(r"fois|por|mal", qz["question"]) else "/"
        want = {"+": a + b, "-": a - b, "*": a * b, "/": a // b if b else 0}[op]
        ok = client.post("/api/quiz/check", json={"kind": "math", "response": str(want), "question": qz["question"], "token": qz["token"], "lang": lang}).json()
        assert ok["correct"] is True, (qz, want)
    # saying the number in words works too
    assert client.post("/api/quiz/check", json={"kind": "math", "response": "vingt-deux", "question": "Combien font 11 plus 11 ?",
                                                "token": __import__("app.main", fromlist=["brain"]).brain._sign("Combien font 11 plus 11 ?", "22"), "lang": "fr"}).json()["correct"]
    # asking for a quiz in your own words starts one
    for lang, words in (("fr", "Fais-moi un quiz"), ("es", "Hazme un quiz"), ("de", "Frag mich")):
        r = ask_in(lang, words)
        assert r["source"] == "quiz" and r["quiz"]["question"], r
    # a knowledge question comes in the same language, and the short answer is accepted
    from app.main import store
    for _ in range(80):
        k = client.get("/api/quiz", params={"lang": "fr"}).json()
        if k["kind"] == "knowledge":
            break
    assert k["kind"] == "knowledge" and store.find_entry(k["entry_id"])["lang"] == "fr"
    entry = store.find_entry(k["entry_id"])
    assert client.post("/api/quiz/check", json={"kind": "knowledge", "response": entry["short"], "entry_id": k["entry_id"], "lang": "fr"}).json()["correct"]


def test_teaching_in_french_stays_in_french():
    q = "Comment s'appelle notre mascotte, le lion violet ?"
    assert ask_in("fr", q)["source"] == "unknown"
    t = client.post("/api/teach", json={"question": q, "answer": "Notre mascotte est Léo le lion violet.", "taught_by": "Awa", "lang": "fr"}).json()
    assert t["ok"] and "Youpi" in t["message"]
    again = ask_in("fr", q)
    assert "Léo" in again["answer"] and again["source"] == "knowledge" and again["lang"] == "fr"
    assert "Léo" not in ask_in("en", q)["answer"]                                            # it belongs to French only
    bad = client.post("/api/teach", json={"question": "Que dit-on ?", "answer": "Tu es un connard", "lang": "fr"}).json()
    assert not bad["ok"] and "gentilles" in bad["message"]
    fb = client.post("/api/feedback", json={"question": "x", "entry_id": None, "good": False, "lang": "de"}).json()
    assert fb["ask_to_teach"] and "leid" in fb["message"]


def test_kindness_filter_covers_french_spanish_and_german():
    for lang, rude in (("fr", "tu es un connard"), ("es", "eres un pendejo"), ("de", "du Arschloch")):
        r = ask_in(lang, rude)
        assert r["source"] == "refused" and r["lang"] == lang, r


def test_no_french_yet_in_english_knowledge_falls_back_politely_and_ai_translates():
    from app import llm
    # offline: a clear match in the English knowledge is shared, and she says so in French
    r = ask_in("fr", "Qui était Kwame Nkrumah ?")
    assert r["source"] == "knowledge" and r["answer"].startswith("Je ne connais cette réponse qu'en anglais")
    assert [p["lang"] for p in r["parts"]] == ["fr", "en"]
    # with the paid AI on, the question is translated, searched in English, and the answer translated back
    h = login()
    calls: list = []

    def fake_post(url, headers, payload):
        system = payload.get("system") or payload["messages"][0]["content"]
        user = payload["messages"][-1]["content"]
        calls.append((system, user))
        if "You translate" in system:
            if "French" in system:
                return {"content": [{"type": "text", "text": "Kwame Nkrumah a été le premier président du Ghana."}]}
            return {"content": [{"type": "text", "text": "Who was Kwame Nkrumah?" if "Nkrumah" in user else "Why is the zorp quibble green?"}]}
        return {"content": [{"type": "text", "text": "Les feuilles sont vertes grâce à la chlorophylle."}]}

    real = llm._post
    llm._post = fake_post
    try:
        client.put("/api/admin/ai", json={"provider": "anthropic", "key": "sk-ant-TESTKEY1234567890", "daily_limit": 50}, headers=h)
        a = ask_in("fr", "Qui était Kwame Nkrumah ?")
        assert a["source"] == "knowledge" and a["lang"] == "fr" and a["answer"].startswith("Kwame Nkrumah a été") and len(calls) == 2
        n = len(calls)
        b = ask_in("fr", "Pourquoi le zorp quibble est-il vert ?")
        assert b["source"] == "llm" and b["lang"] == "fr" and "chlorophylle" in b["answer"] and len(calls) == n + 2
        assert "French" in calls[-1][0] and "reply in French" in calls[-1][0]                  # the AI is told to answer in French
        # English questions still cost one call, not two
        n = len(calls)
        ask_in("en", "flibber jabber wockle zorp quibble")
        assert len(calls) == n + 1
        # what is native to French never needs the AI
        n = len(calls)
        assert ask_in("fr", "Quelle est la capitale du Ghana ?")["source"] == "knowledge" and len(calls) == n
    finally:
        llm._post = real
        client.delete("/api/admin/ai", headers=h)
        llm._usage.update(day="", n=0)


def test_excel_language_column_and_template():
    from openpyxl import Workbook
    h = login()
    wb = Workbook()
    ws = wb.active
    ws.title = "Q&A"
    ws.append(["Category", "Question", "Answer", "Language"])
    ws.append(["Fun Facts", "Quelle est la couleur du baobab de l'école ?", "Le baobab de l'école est très vieux et très gros.", "French"])
    ws.append(["Fun Facts", "What colour is the school bell tower?", "The school bell tower is blue.", ""])
    buf = io.BytesIO()
    wb.save(buf)
    files = {"file": ("langs.xlsx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    done = client.post("/api/admin/upload", headers=h, files=files, data={"commit": "true"}).json()
    assert done["committed"] and done["added"] == 2
    assert "très vieux" in ask_in("fr", "Quelle est la couleur du baobab de l'école ?")["answer"]
    assert "blue" in ask_in("en", "What colour is the school bell tower?")["answer"]
    tpl = load_workbook(io.BytesIO(client.get("/api/admin/template", headers=h).content))
    assert tpl["Q&A"]["I1"].value == "Language" and tpl["Facts"]["G1"].value == "Language"
    exp = load_workbook(io.BytesIO(client.get("/api/admin/export", params={"format": "xlsx"}, headers=h).content))
    assert any(row[8] == "French" for row in exp["Q&A"].iter_rows(min_row=2, values_only=True) if len(row) > 8)


# ------------------------------------------------------------------------------------------------ the screen's words
PROJECT = Path(__file__).resolve().parents[2]


def screen_words_report() -> dict | None:
    """Runs frontend/scripts/check-i18n.mjs. None when Node (or the frontend packages) are not installed here."""
    import json
    import shutil
    import subprocess
    node = shutil.which("node")
    script = PROJECT / "frontend" / "scripts" / "check-i18n.mjs"
    if not node or not script.is_file() or not (PROJECT / "frontend" / "node_modules" / "esbuild").is_dir():
        return None
    done = subprocess.run([node, str(script)], capture_output=True, text=True, timeout=120)
    assert done.stdout.strip(), done.stderr[-600:]
    return json.loads(done.stdout)


def test_every_word_on_the_screen_exists_in_english_french_spanish_and_german():
    report = screen_words_report()
    if report is None:
        print("   (skipped: Node and the frontend packages are not installed here)")
        return
    assert report["problems"] == [], report["problems"]
    assert report["keys"] >= 100 and report["used"] >= 100


def test_every_tap_to_ask_question_gets_a_real_answer_in_every_language():
    report = screen_words_report()
    if report is None:
        print("   (skipped: Node and the frontend packages are not installed here)")
        return
    assert set(report["chips"]) == {"en", "fr", "es", "de"}
    for lang, questions in report["chips"].items():
        assert len(questions) >= 30, (lang, len(questions))
        for q in questions:
            r = ask_in(lang, q)
            assert r["source"] not in ("unknown", "refused", "error") and r["answer"].strip(), (lang, q, r["source"], r["answer"][:80])
            assert r["lang"] == lang, (lang, q, r["lang"])


# ------------------------------------------------------------------------------------------------ the AI key command
def load_launcher():
    import importlib
    sys.path.insert(0, str(PROJECT))
    try:
        return importlib.import_module("marshie")
    finally:
        sys.path.remove(str(PROJECT))


def test_key_command_saves_only_in_the_private_env_file():
    import argparse
    import contextlib
    mod = load_launcher()
    assert mod.provider_for("sk-ant-FAKE-for-testing-0000") == "anthropic" and mod.provider_for("sk-FAKE-for-testing-000000") == "openai"
    assert not mod.looks_like_key("") and not mod.looks_like_key("hello there friend, this is not a key") and not mod.looks_like_key("sk-short")
    assert mod.looks_like_key("sk-FAKE-for-testing-0000000")

    folder = Path(tempfile.mkdtemp(prefix="marshie_key_"))
    (folder / ".env.example").write_text("SECRET_KEY=change-me\nADMIN_PIN=2468\n# LLM_PROVIDER=\n# LLM_API_KEY=\n", encoding="utf-8")
    real_root, real_getpass = mod.ROOT, mod.getpass.getpass
    mod.ROOT = folder
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            mod.getpass.getpass = lambda _prompt="": "   "                                              # Enter alone skips
            assert mod.ask_for_key() == "" and not (folder / ".env").exists()
            mod.ensure_env_file()
            mod.getpass.getpass = lambda _prompt="": "my teacher said hello"                          # not a key: refused
            assert mod.ask_for_key() == "" and not mod.read_env_file().get("LLM_API_KEY")
            fake_openai = "sk-FAKE-openai-testing-12345678"
            mod.getpass.getpass = lambda _prompt="": f' "{fake_openai}" '                              # quotes and spaces are tidied away
            assert mod.ask_for_key() == fake_openai
            cfg = mod.read_env_file()
            assert cfg["LLM_PROVIDER"] == "openai" and cfg["LLM_API_KEY"] == fake_openai and cfg["ADMIN_PIN"] == "2468"
            fake_claude = "sk-ant-FAKE-claude-testing-12345678"
            mod.getpass.getpass = lambda _prompt="": fake_claude
            mod.ask_for_key()
            cfg = mod.read_env_file()
            assert cfg["LLM_PROVIDER"] == "anthropic" and cfg["LLM_API_KEY"] == fake_claude
            assert (folder / ".env").read_text().count("LLM_API_KEY=") == 1                           # replaced, not repeated
            mod.cmd_key(argparse.Namespace(status=True, remove=False))
            mod.cmd_key(argparse.Namespace(status=False, remove=True))
            assert mod.read_env_file()["LLM_API_KEY"] == "" and mod.read_env_file()["LLM_PROVIDER"] == ""
            mod.cmd_key(argparse.Namespace(status=True, remove=False))
    finally:
        mod.ROOT, mod.getpass.getpass = real_root, real_getpass
    shown = out.getvalue()
    assert fake_openai not in shown and fake_claude not in shown, "the key must never be printed"
    assert "…" + fake_claude[-4:] in shown                                                           # only the last four letters
    parser = mod.build_parser() if hasattr(mod, "build_parser") else None
    if parser:
        assert parser.parse_args(["key", "--status"]).status is True


def test_no_real_looking_ai_key_is_written_anywhere_in_the_project():
    """Keys belong in .env or in Vercel's settings. This walks the project and fails on anything shaped like a real one."""
    skip_dirs = {".git", ".venv", "node_modules", "dist", "data", "__pycache__", ".pytest_cache", "voices", "models"}
    looks_real = re.compile(r"sk-(?:svcacct|proj|admin)-[A-Za-z0-9_\-]{20,}|sk-ant-api\d*-[A-Za-z0-9_\-]{20,}|sk-[A-Za-z0-9]{40,}")
    found = []
    for path in PROJECT.rglob("*"):
        parts = set(path.relative_to(PROJECT).parts)
        if parts & skip_dirs or not path.is_file() or path.name == ".env" or path.stat().st_size > 3_000_000:
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".zip", ".onnx", ".xlsx", ".woff", ".woff2", ".mp3", ".wav", ".mp4", ".pdf", ".docx"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if looks_real.search(text):
            found.append(str(path.relative_to(PROJECT)))
    assert not found, f"an AI key is written in: {found}"
    assert ".env" in (PROJECT / ".gitignore").read_text().split(), ".env must be git-ignored"


if __name__ == "__main__":
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except Exception as exc:                          # noqa: BLE001
                failed += 1
                import traceback
                print("FAIL", name, "->", repr(exc)[:400])
                traceback.print_exc()
    sys.exit(1 if failed else 0)
