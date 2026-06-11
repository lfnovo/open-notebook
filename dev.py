#!/usr/bin/env python3
"""Cross-platform dev launcher for Open Notebook (from source).

Brings up the whole stack and streams every service's logs into THIS
terminal with [db]/[api]/[worker]/[frontend] prefixes. Press Ctrl+C once
to tear everything down (the from-source processes AND the SurrealDB
container). Works on Windows, Linux and macOS.

    db        SurrealDB           docker compose            (port 8000)
    api       FastAPI / uvicorn   auto-reload api/ + open_notebook/  (5055)
    worker    surreal-commands    auto-reload via watchfiles (embeddings + podcasts)
    frontend  Next.js dev server  Turbopack HMR             (3000)

Usage:
    uv run python dev.py            # bring everything up (default)
    uv run python dev.py --skip-sync
    uv run python dev.py stop       # force-stop anything left running

The convenience wrappers dev.bat / dev.sh / dev.ps1 just call this.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / ".dev-logs"
PIDFILE = LOG_DIR / "dev.pids.json"
IS_WIN = os.name == "nt"

# Children emit UTF-8 (PYTHONIOENCODING below); the launcher's own stdout on
# Windows defaults to cp1252, so writing a child's "—"/emoji would raise
# UnicodeEncodeError and kill the log-reader thread. Force UTF-8 here.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
NPM = "npm.cmd" if IS_WIN else "npm"
VENV_PY = ROOT / ".venv" / ("Scripts" if IS_WIN else "bin") / ("python.exe" if IS_WIN else "python")

# ---- output -------------------------------------------------------------
COLORS = {"db": "\033[33m", "api": "\033[36m", "worker": "\033[35m",
          "frontend": "\033[32m", "sys": "\033[90m", "err": "\033[31m"}
RESET = "\033[0m"
_PAD = max(len(n) for n in ("db", "api", "worker", "frontend"))
_LOCK = threading.Lock()


def _enable_windows_ansi() -> bool:
    if not IS_WIN:
        return True
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if not k.GetConsoleMode(h, ctypes.byref(mode)):
            return False
        k.SetConsoleMode(h, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        return True
    except Exception:
        return False


if not _enable_windows_ansi():
    COLORS = {k: "" for k in COLORS}
    RESET = ""


def emit(name: str, line: str, color: str | None = None) -> None:
    c = color if color is not None else COLORS.get(name, "")
    with _LOCK:
        try:
            sys.stdout.write(f"{c}[{name.ljust(_PAD)}]{RESET} {line}\n")
        except UnicodeEncodeError:
            safe = line.encode("ascii", "replace").decode("ascii")
            sys.stdout.write(f"{c}[{name.ljust(_PAD)}]{RESET} {safe}\n")
        sys.stdout.flush()


def log(msg: str) -> None:
    emit("sys", msg, COLORS["sys"])


# ---- ports --------------------------------------------------------------
def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def wait_port(port: int, label: str, timeout: int = 60) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if port_open(port):
            return True
        time.sleep(0.5)
    log(f"WARN: {label} did not open port {port} within {timeout}s (continuing)")
    return False


# ---- process tree teardown ---------------------------------------------
def kill_tree(pid: int) -> None:
    if IS_WIN:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    import signal
    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        return
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return
    for _ in range(20):  # up to ~2s for graceful exit
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.1)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def popen(cmd: list[str], cwd: Path) -> subprocess.Popen:
    kwargs: dict = {}
    if IS_WIN:
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True  # own process group so Ctrl+C hits us, not them
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
    return subprocess.Popen(
        cmd, cwd=str(cwd),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        bufsize=1, text=True, encoding="utf-8", errors="replace",
        env=env, **kwargs,
    )


# ---- dependency bootstrap ----------------------------------------------
def ensure_deps() -> None:
    log("uv sync ...")
    subprocess.run(["uv", "sync"], cwd=ROOT, check=True,
                   stdout=subprocess.DEVNULL)
    # `uv sync` strips anything not in pyproject.toml. content-core needs
    # libmagic for file-type detection on uploads. Windows has no system
    # libmagic, so use python-magic-bin (bundles the DLL); elsewhere the
    # plain binding + the OS libmagic. `uv run` does NOT re-strip these, so
    # restoring once per launch is enough.
    pkg = "python-magic-bin" if IS_WIN else "python-magic"
    log(f"ensuring {pkg} (libmagic for uploads) ...")
    subprocess.run(["uv", "pip", "install", "-q", pkg], cwd=ROOT, check=True)
    # sanity-check libmagic via the venv python directly (no `uv run` -> no sync)
    if VENV_PY.exists():
        chk = subprocess.run([str(VENV_PY), "-c", "import magic; magic.from_buffer(b'x')"],
                             cwd=ROOT, capture_output=True, text=True)
        if chk.returncode != 0:
            hint = ("On Debian/Ubuntu: sudo apt-get install libmagic1  "
                    "(macOS: brew install libmagic)") if not IS_WIN else ""
            log(f"WARN: libmagic not usable yet - file uploads may fail. {hint}")
    if not (ROOT / "frontend" / "node_modules").exists():
        log("npm install (frontend) ...")
        subprocess.run([NPM, "install"], cwd=ROOT / "frontend", check=True,
                       stdout=subprocess.DEVNULL)


# ---- service definitions ------------------------------------------------
SERVICES = [
    ("api", [
        "uv", "run", "--env-file", ".env", "uvicorn", "api.main:app",
        "--host", "127.0.0.1", "--port", "5055",
        "--reload", "--reload-dir", "api", "--reload-dir", "open_notebook",
    ], ROOT),
    ("worker", [
        "uv", "run", "--env-file", ".env", "watchfiles", "--filter", "python",
        "surreal-commands-worker --import-modules commands",
        "commands", "open_notebook",
    ], ROOT),
    ("frontend", [NPM, "run", "dev"], ROOT / "frontend"),
]


def docker_compose(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "compose", *args], cwd=ROOT,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ---- commands -----------------------------------------------------------
def cmd_stop() -> None:
    log("stopping any running from-source services ...")
    killed = 0
    if PIDFILE.exists():
        try:
            for entry in json.loads(PIDFILE.read_text()):
                kill_tree(int(entry["pid"]))
                killed += 1
        except Exception as e:
            log(f"WARN: could not read pidfile: {e}")
        PIDFILE.unlink(missing_ok=True)
    log(f"signalled {killed} process group(s).")
    log("stopping SurrealDB container ...")
    docker_compose("stop", "surrealdb")
    log("done.")


def cmd_up(skip_sync: bool) -> None:
    for tool in ("docker", "uv", NPM):
        if subprocess.run(["where" if IS_WIN else "which", tool],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
            log(f"ERROR: required tool '{tool}' not found on PATH.")
            sys.exit(1)

    env_path = ROOT / ".env"
    if not env_path.exists():
        log(".env missing - creating from .env.example (SURREAL_URL -> localhost)")
        text = (ROOT / ".env.example").read_text()
        text = text.replace("ws://surrealdb:8000/rpc", "ws://localhost:8000/rpc")
        env_path.write_text(text)

    for port, who in ((5055, "API"), (3000, "frontend")):
        if port_open(port):
            log(f"ERROR: port {port} already in use ({who} already running?). "
                f"Run: {'dev.bat' if IS_WIN else './dev.sh'} stop")
            sys.exit(1)

    if not skip_sync:
        ensure_deps()

    LOG_DIR.mkdir(exist_ok=True)

    log("starting SurrealDB via docker compose ...")
    docker_compose("up", "-d", "surrealdb")
    if not wait_port(8000, "SurrealDB", 60):
        log("ERROR: SurrealDB never came up. Check: docker logs sai-notebook-surrealdb-1")
        sys.exit(1)
    emit("db", "ready on :8000", COLORS["db"])

    procs: list[tuple[str, subprocess.Popen]] = []
    for name, cmd, cwd in SERVICES:
        p = popen(cmd, cwd)
        procs.append((name, p))
        emit(name, f"started (pid {p.pid})", COLORS[name])
        t = threading.Thread(target=_pump, args=(name, p), daemon=True)
        t.start()

    PIDFILE.write_text(json.dumps([{"name": n, "pid": p.pid} for n, p in procs]))

    threading.Thread(target=_banner_when_ready, daemon=True).start()

    try:
        while True:
            for name, p in procs:
                if p.poll() is not None:
                    emit(name, f"process exited with code {p.returncode}", COLORS["err"])
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\n")
        log("shutting down ...")
        for _name, p in procs:
            if p.poll() is None:
                kill_tree(p.pid)
        log("stopping SurrealDB container ...")
        docker_compose("stop", "surrealdb")
        PIDFILE.unlink(missing_ok=True)
        log("done.")


def _pump(name: str, proc: subprocess.Popen) -> None:
    assert proc.stdout is not None
    for line in proc.stdout:
        emit(name, line.rstrip("\n"))


def _banner_when_ready() -> None:
    for _ in range(120):
        if port_open(5055) and port_open(3000):
            with _LOCK:
                g = COLORS.get("frontend", "")
                sys.stdout.write(
                    f"\n{g}  ============================================================\n"
                    f"   Open Notebook is up:\n"
                    f"     Frontend : http://localhost:3000\n"
                    f"     API docs : http://localhost:5055/docs\n"
                    f"     Database : http://localhost:8000\n"
                    f"   Press Ctrl+C to stop everything.\n"
                    f"  ============================================================{RESET}\n\n"
                )
                sys.stdout.flush()
            return
        time.sleep(1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Open Notebook dev launcher")
    ap.add_argument("command", nargs="?", default="up", choices=["up", "stop"])
    ap.add_argument("--skip-sync", action="store_true",
                    help="skip uv sync / npm install dependency checks")
    args = ap.parse_args()
    if args.command == "stop":
        cmd_stop()
    else:
        cmd_up(args.skip_sync)


if __name__ == "__main__":
    main()
