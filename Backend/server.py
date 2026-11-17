"""Local HTTP server and JSON API for the memory simulator."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from .memory import MemoryManager

ROOT = Path(__file__).resolve().parent.parent
LIVE_SERVER_ORIGINS = {
    "http://127.0.0.1:5501",
    "http://localhost:5501",
}
manager = MemoryManager()
manager_lock = threading.RLock()


class SimulatorHandler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_cors_headers(self):
        origin = self.headers.get("Origin")
        if origin in LIVE_SERVER_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def _send_file(self, path):
        content_types = {
            ".css": "text/css; charset=utf-8",
            ".html": "text/html; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".mjs": "text/javascript; charset=utf-8",
        }
        try:
            body = path.read_bytes()
        except OSError:
            self.send_error(404, "File not found")
            return
        self.send_response(200)
        self.send_header("Content-Type", content_types.get(path.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path == "/api/state":
            raw_size = parse_qs(parsed.query).get("size", [""])[0]
            try:
                requested_size = int(raw_size) if raw_size else None
            except ValueError:
                self._send_json(400, {"error": "Preview size must be a whole number."})
                return
            with manager_lock:
                self._send_json(200, {"state": manager.snapshot(requested_size)})
            return

        requested = unquote(parsed.path).lstrip("/") or "index.html"
        path = (ROOT / requested).resolve()
        if path != ROOT and ROOT not in path.parents:
            self.send_error(403, "Path is outside the project")
            return
        if path.is_dir():
            path = path / "index.html"
        self._send_file(path)

    def do_OPTIONS(self):
        if urlsplit(self.path).path not in ("/api/action", "/api/state"):
            self._send_json(404, {"error": "Unknown API endpoint."})
            return
        if self.headers.get("Origin") not in LIVE_SERVER_ORIGINS:
            self._send_json(403, {"error": "Cross-origin requests are not allowed."})
            return
        self.send_response(204)
        self._send_cors_headers()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        if urlsplit(self.path).path != "/api/action":
            self._send_json(404, {"error": "Unknown API endpoint."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 16384:
                raise ValueError("Request body must be between 1 and 16384 bytes.")
            body = self.rfile.read(length)
            if len(body) != length:
                raise ValueError("Request body was incomplete.")
            payload = json.loads(body)
            if not isinstance(payload, dict):
                raise ValueError("Request body must be a JSON object.")
            result = self._perform_action(payload)
        except (ValueError, UnicodeDecodeError) as error:
            self._send_json(400, {"error": str(error)})
            return
        self._send_json(200, result)

    def _perform_action(self, payload):
        action = payload.get("action")
        with manager_lock:
            if action == "reset":
                manager.reset(payload.get("total"))
                return {"state": manager.snapshot()}
            if action == "strategy":
                manager.set_strategy(payload.get("strategy"))
            elif action == "allocate":
                outcome = manager.allocate(payload.get("size"), payload.get("name", ""))
                return {"outcome": outcome, "state": manager.snapshot(payload.get("size"))}
            elif action == "free":
                process = manager.free(payload.get("pid"))
                return {"process": process, "state": manager.snapshot()}
            elif action == "compact":
                outcome = manager.compact()
                return {"outcome": outcome, "state": manager.snapshot()}
            elif action == "demo":
                outcome = manager.load_demo()
                return {"outcome": outcome, "state": manager.snapshot(outcome["suggested_size"])}
            else:
                raise ValueError("Unknown action.")
            return {"state": manager.snapshot(payload.get("size"))}


if __name__ == "__main__":
    address = ("127.0.0.1", 8000)
    print(f"Memory simulator running at http://{address[0]}:{address[1]}", flush=True)
    try:
        ThreadingHTTPServer(address, SimulatorHandler).serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
