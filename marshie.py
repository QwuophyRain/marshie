#!/usr/bin/env python3
"""Marshie launcher. One script that behaves the same on Raspberry Pi, macOS, Windows and Linux.

    python marshie.py              set everything up the first time, then start Marshie
    python marshie.py setup        first-time setup only (you can pick a teacher PIN)
    python marshie.py start        start Marshie and open her in the browser
    python marshie.py kiosk        start Marshie and open her full screen (for the school screen)
    python marshie.py voice        add Marshie's offline voice and ears (downloads about 120 MB)
    python marshie.py build        rebuild the screen (only needed after editing frontend/src)
    python marshie.py autostart    start Marshie by herself when this computer turns on
    python marshie.py doctor       check what works and what is missing
    python marshie.py test         run the self-tests

Uses the Python standard library only, so it runs before anything else is installed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import secrets
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import webbrowser
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"
VENV = ROOT / ".venv"
MIN_PYTHON = (3, 10)

DEFAULT_PIPER_VOICE = "en_US-amy-low"
VOSK_MODEL_NAME = "vosk-model-small-en-us-0.15"
VOSK_URL = f"https://alphacephei.com/vosk/models/{VOSK_MODEL_NAME}.zip"
PIPER_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"

for _stream in (sys.stdout, sys.stderr):                       # Windows consoles can be cp1252; never crash on a character
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ------------------------------------------------------------------------------------------------ small helpers
def say(msg: str = "") -> None:
    print(msg, flush=True)


def ok(msg: str) -> None:
    say(f"  [ok]  {msg}")


def bad(msg: str) -> None:
    say(f"  [!!]  {msg}")


def fail(msg: str, code: int = 1):
    say("")
    say(f"Marshie could not continue: {msg}")
    sys.exit(code)


def run(cmd: list[str], **kw) -> int:
    return subprocess.run(cmd, **kw).returncode


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if IS_WIN else "bin/python")


def child_env() -> dict:
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def read_env_file() -> dict:
    out: dict = {}
    path = ROOT / ".env"
    if path.is_file():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def set_env_value(key: str, value: str) -> None:
    path = ROOT / ".env"
    text = path.read_text(encoding="utf-8-sig") if path.is_file() else ""
    line = f"{key}={value}"
    if re.search(rf"(?m)^#?\s*{re.escape(key)}=", text):
        text = re.sub(rf"(?m)^#?\s*{re.escape(key)}=.*$", lambda _m: line, text, count=1)
    else:
        text = text.rstrip("\n") + f"\n{line}\n"
    path.write_text(text, encoding="utf-8")


# ------------------------------------------------------------------------------------------------ setup steps
def check_python() -> None:
    if sys.version_info < MIN_PYTHON:
        fail(f"Marshie needs Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer, and this is Python "
             f"{sys.version_info.major}.{sys.version_info.minor}. Get a newer one from https://www.python.org/downloads/ "
             "(on Windows, tick 'Add python.exe to PATH').")


def ensure_venv() -> Path:
    py = venv_python()
    if py.exists():
        return py
    say("Making Marshie's own Python space (.venv). This happens once.")
    code = run([sys.executable, "-m", "venv", str(VENV)])
    if code != 0 or not py.exists():
        shutil.rmtree(VENV, ignore_errors=True)
        hint = ""
        if sys.platform.startswith("linux"):
            hint = " On Raspberry Pi OS, Ubuntu or Debian run:  sudo apt install python3-venv python3-pip"
        fail("could not create the .venv folder." + hint)
    return py


def sync_packages(files: tuple[str, ...] = ("requirements.txt",)) -> None:
    py = ensure_venv()
    stamp = VENV / ".marshie-installed.json"
    try:
        have = json.loads(stamp.read_text())
    except Exception:
        have = {}
    key = "+".join(files)
    want = hashlib.sha256(b"".join((ROOT / f).read_bytes() for f in files)).hexdigest()
    if have.get(key) == want:
        return
    say("Installing Marshie's packages. The first time needs the internet and can take a few minutes.")
    cmd = [str(py), "-m", "pip", "install", "--disable-pip-version-check"]
    for f in files:
        cmd += ["-r", str(ROOT / f)]
    if run(cmd, env=child_env()) != 0:
        fail("the packages did not install. Check the internet connection, then run the same command again.")
    have[key] = want
    stamp.write_text(json.dumps(have))


def ensure_env_file(ask: bool = False) -> None:
    path = ROOT / ".env"
    if path.exists():
        return
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    text = re.sub(r"(?m)^SECRET_KEY=.*$", lambda _m: f"SECRET_KEY={secrets.token_hex(24)}", text)
    if ask and sys.stdin.isatty():
        say("")
        pin = input("Choose a teacher PIN, 4 to 8 digits (press Enter to keep 2468): ").strip()
        if pin.isdigit() and 4 <= len(pin) <= 8:
            text = re.sub(r"(?m)^ADMIN_PIN=.*$", lambda _m: f"ADMIN_PIN={pin}", text)
        elif pin:
            say("  That was not 4 to 8 digits, so I kept 2468. You can change ADMIN_PIN in the .env file later.")
        school = input("Your school's name (press Enter to skip): ").strip().replace("\n", " ")
        if school:
            text = re.sub(r"(?m)^SCHOOL_NAME=.*$", lambda _m: f"SCHOOL_NAME={school}", text)
    path.write_text(text, encoding="utf-8")
    say("  Made the settings file (.env).")


def frontend_ready() -> bool:
    return (ROOT / "frontend" / "dist" / "index.html").is_file()


def build_frontend(force: bool = False) -> bool:
    if frontend_ready() and not force:
        return True
    npm = shutil.which("npm")
    if not npm:
        bad("Marshie's screen is not built yet, and Node.js (npm) is not installed.")
        say("        Install Node.js 18 or newer from https://nodejs.org (Raspberry Pi OS: sudo apt install nodejs npm),")
        say("        then run:  python marshie.py build")
        say("        Or build it on any computer and copy the frontend/dist folder here.")
        return False
    say("Building Marshie's screen. This takes a minute the first time.")
    fe = ROOT / "frontend"
    if run([npm, "install", "--no-audit", "--no-fund"], cwd=fe) != 0 or run([npm, "run", "build"], cwd=fe) != 0:
        bad("The screen did not build. Scroll up to see why, or run:  python marshie.py doctor")
        return False
    return True


def prepare(ask: bool = False, frontend: bool = True) -> None:
    check_python()
    sync_packages()
    ensure_env_file(ask)
    if frontend:
        build_frontend()


# ------------------------------------------------------------------------------------------------ networking
def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) != 0


def pick_port(want: int) -> int:
    for port in range(want, want + 20):
        if port_free(port):
            return port
    fail(f"ports {want} to {want + 19} are all busy. Close the other program or use  --port 9000")


def lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))               # no packet is sent; this only picks the right network card
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def wait_until_up(port: int, proc: subprocess.Popen, seconds: int = 60) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1.5):
                return True
        except Exception:
            time.sleep(0.4)
    return False


# ------------------------------------------------------------------------------------------------ browsers
def find_browser() -> str | None:
    if IS_WIN:
        roots = [os.environ.get(k, "") for k in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
        rel = [r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe",
               r"BraveSoftware\Brave-Browser\Application\brave.exe"]
        for r in roots:
            for p in rel:
                if r and (Path(r) / p).is_file():
                    return str(Path(r) / p)
        return None
    if IS_MAC:
        apps = ["Google Chrome.app/Contents/MacOS/Google Chrome", "Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "Chromium.app/Contents/MacOS/Chromium", "Brave Browser.app/Contents/MacOS/Brave Browser"]
        for a in apps:
            for base in (Path("/Applications"), Path.home() / "Applications"):
                if (base / a).is_file():
                    return str(base / a)
        return None
    for name in ("chromium-browser", "chromium", "google-chrome", "google-chrome-stable", "microsoft-edge", "brave-browser"):
        found = shutil.which(name)
        if found:
            return found
    return None


def open_kiosk(url: str) -> bool:
    browser = find_browser()
    if not browser:
        return False
    profile = ROOT / "data" / "browser-profile"
    profile.mkdir(parents=True, exist_ok=True)
    flags = [
        "--kiosk", f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check",
        "--autoplay-policy=no-user-gesture-required",          # lets Marshie speak without an extra tap
        "--use-fake-ui-for-media-stream",                      # allows the microphone without asking each morning
        "--disable-session-crashed-bubble", "--disable-infobars", "--noerrdialogs",
        "--overscroll-history-navigation=0", "--password-store=basic", url,
    ]
    try:
        subprocess.Popen([browser, *flags], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError:
        return False


# ------------------------------------------------------------------------------------------------ commands
def cmd_setup(args) -> None:
    prepare(ask=True)
    say("")
    say("All set. Start Marshie with:  python marshie.py start")
    say("For the school screen:       python marshie.py kiosk")
    say("To give her a voice:         python marshie.py voice")


def serve(args, kiosk: bool = False) -> None:
    prepare()
    cfg = read_env_file()
    port = pick_port(args.port)
    if port != args.port:
        say(f"Port {args.port} is busy, so I am using {port} instead.")
    host = "0.0.0.0" if args.share else "127.0.0.1"
    cmd = [str(venv_python()), "-m", "uvicorn", "backend.app.main:app", "--host", host, "--port", str(port),
           "--log-level", "warning"]
    say("Starting Marshie...")
    proc = subprocess.Popen(cmd, cwd=ROOT, env=child_env())
    if not wait_until_up(port, proc):
        if proc.poll() is None:
            proc.terminate()
        fail("Marshie did not start. Scroll up for the reason, or run:  python marshie.py doctor")

    url = f"http://localhost:{port}"
    say("")
    say("  Marshie is awake!")
    say(f"  On this computer:  {url}")
    if args.share:
        say(f"  On the school network:  http://{lan_ip()}:{port}")
        say("  (Phones and tablets can chat and teachers can open the Teacher panel there.")
        say("   The microphone only works on this computer, or when the site uses HTTPS.)")
    if cfg.get("ADMIN_PIN", "2468") == "2468":
        say("  Reminder: the teacher PIN is still 2468. Change ADMIN_PIN in the .env file.")
    say("  Press Ctrl+C in this window to stop her.")
    say("")

    if kiosk:
        if not open_kiosk(url):
            say("  I could not find Chrome, Edge or Chromium for full screen, so I opened your normal browser.")
            webbrowser.open(url)
    elif not args.no_browser:
        webbrowser.open(url)

    try:
        proc.wait()
    except KeyboardInterrupt:
        say("\nGoodnight from Marshie!")
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()


def cmd_start(args) -> None:
    serve(args, kiosk=False)


def cmd_kiosk(args) -> None:
    serve(args, kiosk=True)


def cmd_build(args) -> None:
    check_python()
    if not build_frontend(force=True):
        sys.exit(1)
    say("The screen is built.")


# ---- voice
def ssl_contexts():
    """The normal certificates first; pip's own bundle as a backup (python.org builds on a Mac often lack certificates)."""
    yield ssl.create_default_context()
    py = venv_python()
    if py.exists():
        try:
            path = subprocess.run([str(py), "-c", "import pip._vendor.certifi as c; print(c.where())"],
                                  capture_output=True, text=True, timeout=20).stdout.strip()
            if path and Path(path).is_file():
                yield ssl.create_default_context(cafile=path)
        except Exception:
            pass


def download(url: str, dest: Path) -> None:
    if dest.is_file() and dest.stat().st_size > 0:
        say(f"  already have {dest.name}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    last_error: Exception | None = None
    for context in ssl_contexts():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "marshie-setup"})
            with urllib.request.urlopen(req, timeout=60, context=context) as resp, open(part, "wb") as out:
                total = int(resp.headers.get("Content-Length") or 0)
                done = 0
                while True:
                    chunk = resp.read(1 << 16)
                    if not chunk:
                        break
                    out.write(chunk)
                    done += len(chunk)
                    if total:
                        print(f"\r  downloading {dest.name}: {done * 100 // total}% ", end="", flush=True)
            part.replace(dest)
            say(f"\r  downloaded {dest.name} ({dest.stat().st_size // 1024} KB)          ")
            return
        except urllib.error.URLError as exc:
            last_error = exc
            if not isinstance(getattr(exc, "reason", None), ssl.SSLError):
                break
        except OSError as exc:
            last_error = exc
            break
    part.unlink(missing_ok=True)
    fail(f"could not download {url}\n  ({last_error})\n  Check the internet connection. A school network may block this "
         "address; you can also download the file on another computer and copy it into the 'voices' folder.")


def safe_extract(archive: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    base = target.resolve()
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            dest = (target / member.filename).resolve()
            if dest != base and base not in dest.parents:
                fail("the downloaded listening model has an unsafe file path inside it, so I stopped.")
        z.extractall(target)


def piper_urls(voice: str) -> list[str]:
    try:
        locale, name, quality = voice.split("-", 2)
        lang = locale.split("_")[0]
    except ValueError:
        fail(f"'{voice}' is not a Piper voice name. It looks like en_US-amy-low (language_REGION-name-quality).")
    stem = f"{PIPER_BASE}/{lang}/{locale}/{name}/{quality}/{voice}"
    return [stem + ".onnx", stem + ".onnx.json"]


def try_voice(voice: str) -> bool:
    model = ROOT / "voices" / f"{voice}.onnx"
    out = Path(tempfile.gettempdir()) / "marshie-voice-test.wav"
    out.unlink(missing_ok=True)
    cmd = [str(venv_python()), "-m", "piper", "--model", str(model), "--output_file", str(out), "--length-scale", "1.0"]
    try:
        subprocess.run(cmd, input=b"Hello! I am Marshie.", capture_output=True, timeout=120, check=True)
    except Exception as exc:
        detail = getattr(exc, "stderr", b"") or b""
        bad(f"The voice did not speak: {exc}\n{detail.decode('utf-8', 'replace')[-400:]}")
        return False
    return out.is_file() and out.stat().st_size > 2000


def cmd_voice(args) -> None:
    prepare(frontend=False)
    sync_packages(("requirements.txt", "requirements-voice.txt"))
    voices = ROOT / "voices"
    voices.mkdir(exist_ok=True)
    if args.only in ("both", "talk"):
        say(f"Marshie's voice ({args.piper_voice}):")
        for url in piper_urls(args.piper_voice):
            download(url, voices / url.rsplit("/", 1)[1])
        if args.piper_voice != DEFAULT_PIPER_VOICE:
            set_env_value("PIPER_MODEL", f"voices/{args.piper_voice}.onnx")
    if args.only in ("both", "listen"):
        say("Marshie's ears (Vosk):")
        if (voices / VOSK_MODEL_NAME).is_dir():
            say(f"  already have {VOSK_MODEL_NAME}")
        else:
            zip_path = voices / f"{VOSK_MODEL_NAME}.zip"
            download(VOSK_URL, zip_path)
            say("  unpacking...")
            safe_extract(zip_path, voices)
            zip_path.unlink(missing_ok=True)
    say("")
    if args.only in ("both", "talk"):
        say("Trying her voice...")
        if try_voice(args.piper_voice):
            ok("Marshie can speak with the offline voice.")
        else:
            bad("The voice files are in place but the test did not work. Marshie will use the browser's voice instead.")
    say("")
    say("Done. Restart Marshie to use them. The Teacher panel > Voice and screen page shows what she is using.")


# ---- autostart
def autostart_command(kiosk: bool = True) -> list[str]:
    py = str(venv_python() if venv_python().exists() else Path(sys.executable))
    return [py, str(ROOT / "marshie.py"), "kiosk"] if kiosk else [py, str(ROOT / "marshie.py"), "start", "--no-browser"]


def cmd_autostart(args) -> None:
    check_python()
    cmd = autostart_command(kiosk=not args.no_kiosk)
    if IS_WIN:
        startup = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs/Startup"
        target = startup / "Marshie.bat"
        if args.remove:
            target.unlink(missing_ok=True)
            say("Marshie will no longer start by herself.")
            return
        startup.mkdir(parents=True, exist_ok=True)
        quoted = " ".join(f'"{c}"' for c in cmd)
        target.write_text(f'@echo off\r\ncd /d "{ROOT}"\r\nstart "Marshie" /min {quoted}\r\n', encoding="utf-8")
        say(f"Done. Marshie will start when you sign in to Windows.\n  ({target})")
    elif IS_MAC:
        plist = Path.home() / "Library/LaunchAgents/com.marshie.plist"
        if args.remove:
            run(["launchctl", "unload", str(plist)], stderr=subprocess.DEVNULL)
            plist.unlink(missing_ok=True)
            say("Marshie will no longer start by herself.")
            return
        plist.parent.mkdir(parents=True, exist_ok=True)
        items = "".join(f"<string>{c}</string>" for c in cmd)
        plist.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0"><dict>'
            f"<key>Label</key><string>com.marshie</string><key>ProgramArguments</key><array>{items}</array>"
            f"<key>WorkingDirectory</key><string>{ROOT}</string><key>RunAtLoad</key><true/>"
            f"<key>StandardErrorPath</key><string>{ROOT}/data/marshie.log</string></dict></plist>\n", encoding="utf-8")
        (ROOT / "data").mkdir(exist_ok=True)
        run(["launchctl", "unload", str(plist)], stderr=subprocess.DEVNULL)
        run(["launchctl", "load", "-w", str(plist)])
        say(f"Done. Marshie will start when you log in to this Mac.\n  ({plist})")
    else:
        desktop = Path.home() / ".config/autostart/marshie.desktop"
        labwc = Path.home() / ".config/labwc/autostart"
        line = " ".join(f'"{c}"' if " " in c else c for c in cmd)
        if args.remove:
            desktop.unlink(missing_ok=True)
            if labwc.is_file():
                labwc.write_text("".join(l for l in labwc.read_text().splitlines(True) if "marshie.py" not in l))
            say("Marshie will no longer start by herself.")
            return
        desktop.parent.mkdir(parents=True, exist_ok=True)
        desktop.write_text(f"[Desktop Entry]\nType=Application\nName=Marshie\nExec={line}\nPath={ROOT}\n"
                           "X-GNOME-Autostart-enabled=true\nTerminal=false\n", encoding="utf-8")
        if labwc.parent.is_dir():                                # newer Raspberry Pi OS desktops read this file instead
            existing = labwc.read_text() if labwc.is_file() else ""
            if "marshie.py" not in existing:
                labwc.write_text(existing.rstrip("\n") + f"\n{line} &\n")
        say(f"Done. Marshie will start when the desktop starts after you sign in.\n  ({desktop})")
        say("  For a school screen, set the Pi to sign in automatically: sudo raspi-config > System Options > Boot / Auto Login.")


# ---- doctor
def cmd_doctor(args) -> None:
    say(f"Marshie health check ({platform.system()} {platform.machine()}, Python {platform.python_version()})")
    say("")
    (ok if sys.version_info >= MIN_PYTHON else bad)(f"Python {platform.python_version()} (needs {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+)")
    py = venv_python()
    if py.exists():
        ok("Private Python space (.venv) exists")
        code = run([str(py), "-c", "import fastapi, uvicorn, openpyxl, multipart"], stderr=subprocess.DEVNULL)
        (ok if code == 0 else bad)("Packages installed" if code == 0 else "Packages missing: run  python marshie.py setup")
        if code == 0:
            pdf = run([str(py), "-c", "import pypdf"], stderr=subprocess.DEVNULL) == 0
            (ok if pdf else bad)("Can read PDF files (pypdf)" if pdf else "PDF reading is missing: run  python marshie.py setup")
        voice_ok = run([str(py), "-c", "import piper"], stderr=subprocess.DEVNULL) == 0
        ears_ok = run([str(py), "-c", "import vosk"], stderr=subprocess.DEVNULL) == 0
    else:
        bad("No .venv yet: run  python marshie.py setup")
        voice_ok = ears_ok = False
    (ok if frontend_ready() else bad)("Screen is built (frontend/dist)" if frontend_ready()
                                      else "Screen is not built: run  python marshie.py build  (needs Node.js)")
    node, npm = shutil.which("node"), shutil.which("npm")
    say(f"        Node.js: {'found' if node and npm else 'not found (only needed to rebuild the screen)'}")
    cfg = read_env_file()
    if (ROOT / ".env").is_file():
        ok("Settings file (.env) exists")
        if cfg.get("ADMIN_PIN", "2468") == "2468":
            bad("Teacher PIN is still 2468: change ADMIN_PIN in .env")
        if cfg.get("LLM_PROVIDER"):
            ok(f"AI helper is set up in .env ({cfg['LLM_PROVIDER']})")
        else:
            say("        Paid AI: not set in .env (optional; you can add it in the Teacher panel, Paid AI tab)")
    else:
        bad("No .env yet: run  python marshie.py setup")
    model = ROOT / "voices" / Path(cfg.get("PIPER_MODEL") or f"{DEFAULT_PIPER_VOICE}.onnx").name
    talk = voice_ok and model.is_file()
    listen = ears_ok and (ROOT / "voices" / VOSK_MODEL_NAME).is_dir()
    say(f"        Offline voice: {'ready' if talk else 'not installed (the browser voice will be used)'}")
    say(f"        Offline listening: {'ready' if listen else 'not installed (Chrome or Edge listening will be used)'}")
    browser = find_browser()
    say(f"        Browser for full screen: {Path(browser).name if browser else 'none of Chrome, Edge or Chromium found'}")
    say("")
    say("Fix anything marked [!!], then run:  python marshie.py start")


def cmd_test(args) -> None:
    check_python()
    sync_packages(("requirements.txt", "requirements-dev.txt"))
    sys.exit(run([str(venv_python()), str(ROOT / "backend/tests/test_api.py")], cwd=ROOT, env=child_env()))


# ------------------------------------------------------------------------------------------------ entry point
def main() -> None:
    parser = argparse.ArgumentParser(prog="marshie", description="Marshie the marshmallow helper.")
    sub = parser.add_subparsers(dest="command")

    def serving(p: argparse.ArgumentParser) -> None:
        p.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")), help="default 8000")
        p.add_argument("--share", action="store_true", help="let other devices on the school network open Marshie")
        p.add_argument("--no-browser", action="store_true", help="do not open a browser window")

    serving(sub.add_parser("start", help="start Marshie and open her in the browser"))
    serving(sub.add_parser("kiosk", help="start Marshie and open her full screen"))
    sub.add_parser("setup", help="first-time setup")
    sub.add_parser("build", help="rebuild the screen (needs Node.js)")
    v = sub.add_parser("voice", help="install the offline voice and listening")
    v.add_argument("--piper-voice", default=DEFAULT_PIPER_VOICE, help=f"Piper voice name, default {DEFAULT_PIPER_VOICE}. More lifelike: en_US-lessac-medium or en_US-amy-medium")
    v.add_argument("--only", choices=["both", "talk", "listen"], default="both")
    a = sub.add_parser("autostart", help="start Marshie when this computer starts")
    a.add_argument("--remove", action="store_true", help="turn it off again")
    a.add_argument("--no-kiosk", action="store_true", help="start the server only, without opening the screen")
    sub.add_parser("doctor", help="check what works and what is missing")
    sub.add_parser("test", help="run the self-tests")

    args = parser.parse_args()
    if not args.command:
        args = parser.parse_args(["start"])
    handlers = {"start": cmd_start, "kiosk": cmd_kiosk, "setup": cmd_setup, "build": cmd_build, "voice": cmd_voice,
                "autostart": cmd_autostart, "doctor": cmd_doctor, "test": cmd_test}
    try:
        handlers[args.command](args)
    except KeyboardInterrupt:
        say("\nStopped.")


if __name__ == "__main__":
    main()
