"""End-to-end checks for Marshie's API. Run:  python -m pytest backend/tests   (or: python backend/tests/test_api.py)"""
from __future__ import annotations

import io
import os
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


if __name__ == "__main__":
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except Exception as exc:                          # noqa: BLE001
                failed += 1
                print("FAIL", name, "->", repr(exc)[:400])
    sys.exit(1 if failed else 0)
