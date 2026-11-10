"""Local HTTP server for the studio page and its JSON API."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from app.analyze import InputError, run_analysis
from app.chat import reply
from app.config import RUNTIME, WEB_PAGE
from app.llm import complete
from app.llm import ModelError
from app.search import search_public
from app.store import load_analysis, record_submission

MAX_BODY = 200_000


class StudioHandler(BaseHTTPRequestHandler):
    runtime = RUNTIME
    search = staticmethod(search_public)
    ask = staticmethod(complete)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send(200, WEB_PAGE.read_bytes(), "text/html; charset=utf-8")
            return
        if path == "/api/health":
            self._json(200, {"ok": True})
            return
        if path.startswith("/api/analyses/"):
            saved = load_analysis(path.removeprefix("/api/analyses/"), self.runtime)
            if saved is None:
                self._json(404, {"message": "没有找到这次分析。"})
                return
            self._json(200, saved)
            return
        self._json(404, {"message": "没有这个页面。"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
        except ValueError as error:
            self._json(400, {"message": str(error)})
            return
        try:
            if path == "/api/analyze":
                self._json(200, run_analysis(payload, search=self.search, ask=self.ask, directory=self.runtime))
                return
            if path == "/api/chat":
                self._json(200, reply(payload, search=self.search, ask=self.ask))
                return
            if path == "/api/submissions":
                self._json(200, record_submission(payload, self.runtime))
                return
        except InputError as error:
            self._json(400, {"message": str(error)})
            return
        except (ModelError, ValueError) as error:
            self._json(502, {"message": str(error)})
            return
        self._json(404, {"message": "没有这个接口。"})

    def _read_json(self) -> dict:
        length = int(self.headers.get("content-length", "0") or "0")
        if length < 0 or length > MAX_BODY:
            raise ValueError("请求太大。")
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("请求不是 JSON。") from None
        if not isinstance(payload, dict):
            raise ValueError("请求格式不对。")
        return payload

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[job-desk] {self.address_string()} {fmt % args}")


def serve(host: str = "127.0.0.1", port: int = 3000) -> None:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), StudioHandler)
    print(f"岗位系统 http://{host}:{port}/", flush=True)
    server.serve_forever()
