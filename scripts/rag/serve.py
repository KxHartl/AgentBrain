"""Warm RAG query server — keeps the embedding model(s) loaded so queries are instant.

A plain `rag query` reloads torch + the embedding model on every call (~10s of pure
startup). This little localhost HTTP server loads them once and answers queries over
127.0.0.1, so repeated queries return in well under a second. `rag query` finds it via
a per-project descriptor file and uses it automatically (auto-starting it if needed);
without the server, query still works standalone.

  rag serve                # start for the current project (scope=both)
  rag serve --scope local  # only the project DB
  rag serve --stop         # stop it
  rag serve --status       # show the descriptor

The server binds to localhost only, requires a random token (written to the descriptor),
and auto-exits after a period of inactivity (--idle, default 900s).
"""

import argparse
import json
import os
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rag_paths import serve_state_path, enable_utf8_io

IDLE_DEFAULT = 900  # seconds of inactivity before the server exits on its own


def ensure_brain_venv():
    """Re-exec under the AgentBrain venv (which has lancedb/torch); build it if missing."""
    import importlib.util
    import subprocess
    if importlib.util.find_spec("lancedb") is not None:
        return
    brain = Path(os.environ.get("AGENTBRAIN_PATH") or (Path.home() / ".agentbrain"))
    venv_pythons = (brain / ".venv" / "bin" / "python", brain / ".venv" / "Scripts" / "python.exe")
    vpy = next((c for c in venv_pythons if c.exists()), None)
    if vpy and Path(sys.executable).resolve() != vpy.resolve():
        sys.exit(subprocess.run([str(vpy), *sys.argv]).returncode)


class _State:
    def __init__(self, scope, token, idle):
        self.scope = scope
        self.token = token
        self.idle = idle
        self.embedders = {}      # dim -> embed_fn, loaded once and reused
        self.lock = threading.Lock()
        self.last = time.time()


def _make_handler(state):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # silence default access logging
            pass

        def _send(self, code, obj):
            body = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except Exception:
                pass

        def _authed(self):
            return self.headers.get("X-RAG-Token", "") == state.token

        def do_GET(self):
            if self.path.startswith("/health"):
                if not self._authed():
                    return self._send(403, {"ok": False})
                state.last = time.time()
                return self._send(200, {"ok": True, "scope": state.scope, "pid": os.getpid()})
            self._send(404, {"error": "not found"})

        def do_POST(self):
            if not self._authed():
                return self._send(403, {"error": "forbidden"})
            state.last = time.time()
            if self.path.startswith("/shutdown"):
                self._send(200, {"ok": True})
                _cleanup_state()
                threading.Thread(target=lambda: (time.sleep(0.2), os._exit(0)),
                                 daemon=True).start()
                return
            if self.path.startswith("/query"):
                length = int(self.headers.get("Content-Length", 0) or 0)
                try:
                    req = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
                except Exception:
                    req = {}
                from query import query as run_query
                q = req.get("question", "")
                k = int(req.get("k", 5))
                scope = req.get("scope", state.scope)
                try:
                    with state.lock:
                        results = run_query(q, k=k, scope=scope, embedders=state.embedders)
                    self._send(200, {"results": results})
                except SystemExit:
                    self._send(200, {"results": [], "error": "no vector stores / deps"})
                except Exception as e:
                    self._send(200, {"results": [], "error": str(e)})
                return
            self._send(404, {"error": "not found"})

    return Handler


def _cleanup_state():
    try:
        serve_state_path().unlink()
    except Exception:
        pass


def _idle_watch(state):
    while True:
        time.sleep(5)
        if time.time() - state.last > state.idle:
            _cleanup_state()
            os._exit(0)


def serve(scope, host, port, idle):
    from query import query as run_query

    token = secrets.token_hex(16)
    state = _State(scope, token, idle)

    # Preload the embedding model(s) so the descriptor only appears once we're warm
    # (the client waits for it, so even the first query is fast). Best-effort.
    try:
        run_query("warmup", k=1, scope=scope, embedders=state.embedders)
    except (SystemExit, Exception):
        pass

    httpd = ThreadingHTTPServer((host, port), _make_handler(state))
    real_host, real_port = httpd.server_address[0], httpd.server_address[1]

    sp = serve_state_path()
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps({
        "host": real_host, "port": real_port, "token": token,
        "pid": os.getpid(), "scope": scope, "started": time.time(),
    }), encoding="utf-8")

    threading.Thread(target=_idle_watch, args=(state,), daemon=True).start()
    print(f"RAG warm server on http://{real_host}:{real_port} "
          f"(scope={scope}, idle={idle}s)\n  descriptor: {sp}")
    try:
        httpd.serve_forever()
    finally:
        _cleanup_state()


def stop():
    sp = serve_state_path()
    if not sp.exists():
        print("No warm server registered for this project.")
        return
    try:
        info = json.loads(sp.read_text(encoding="utf-8"))
        import urllib.request
        req = urllib.request.Request(
            f"http://{info['host']}:{info['port']}/shutdown", data=b"{}",
            headers={"X-RAG-Token": info.get("token", ""), "Content-Type": "application/json"},
            method="POST")
        urllib.request.urlopen(req, timeout=3).read()
        print("Warm server stopped.")
    except Exception as e:
        print(f"Could not reach server ({e}); removed stale descriptor.")
    try:
        sp.unlink()
    except Exception:
        pass


if __name__ == "__main__":
    enable_utf8_io()
    ensure_brain_venv()
    p = argparse.ArgumentParser(description="Warm RAG query server (keeps models loaded).")
    p.add_argument("--scope", choices=["local", "global", "both"], default="both")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=0, help="0 = pick a free port.")
    p.add_argument("--idle", type=int, default=IDLE_DEFAULT,
                   help="Exit after this many idle seconds (default 900).")
    p.add_argument("--stop", action="store_true", help="Stop the running server.")
    p.add_argument("--status", action="store_true", help="Show the server descriptor.")
    args = p.parse_args()

    if args.stop:
        stop()
    elif args.status:
        sp = serve_state_path()
        print(sp.read_text(encoding="utf-8") if sp.exists() else "No warm server for this project.")
    else:
        serve(args.scope, args.host, args.port, args.idle)
