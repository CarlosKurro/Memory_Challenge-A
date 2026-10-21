"""Local chatbot web app. Run: python -X utf8 webapp.py"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import threading
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from chat_engine import chat_request, demo_answer, extract_updates, responses_call
from memory_agent import MemoryStore, dumps, now

ROOT = Path(__file__).resolve().parent


class ChatApp:
    def __init__(self, db: Path | str):
        self.path = Path(db)
        self.lock = threading.RLock()
        self.config = {
            "provider": "openai" if os.environ.get("OPENAI_API_KEY") else "demo",
            "api_key": os.environ.get("OPENAI_API_KEY", ""),
            "model": os.environ.get("OPENAI_MODEL", "gpt-5-mini"),
        }
        with MemoryStore(self.path):
            pass
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS chats (
                    id TEXT PRIMARY KEY, project TEXT NOT NULL, title TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS turns (
                    id TEXT PRIMARY KEY, chat_id TEXT NOT NULL REFERENCES chats(id),
                    user_text TEXT NOT NULL, assistant_text TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending', error TEXT,
                    request_json TEXT, extraction_json TEXT, changes_json TEXT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS chat_turns ON turns(chat_id, created_at);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def public_config(self):
        return {"provider": self.config["provider"], "model": self.config["model"], "has_api_key": bool(self.config["api_key"])}

    def settings(self, body):
        provider = body.get("provider", "demo")
        model = body.get("model", self.config["model"])
        key = body.get("api_key", "")
        if provider not in ("demo", "openai") or not isinstance(model, str) or not model.strip() or len(model) > 100 or not isinstance(key, str):
            raise ValueError("Cấu hình không hợp lệ.")
        config = {"provider": provider, "model": model.strip(), "api_key": key.strip() or self.config["api_key"]}
        if provider == "openai" and not config["api_key"]:
            raise ValueError("Nhập OpenAI API key để dùng AI thật.")
        if body.get("test_connection") and provider == "openai":
            responses_call(config, {"instructions": "Reply with OK.", "input": "Connection test."})
        self.config = config
        return self.public_config()

    @staticmethod
    def project_name(value):
        if not isinstance(value, str) or not value.strip() or len(value) > 80:
            raise ValueError("Tên dự án cần từ 1 đến 80 ký tự.")
        return value.strip()

    def memory(self, project):
        with MemoryStore(self.path) as store:
            return {"active": store.active(project), "history": store.history(project)}

    def bootstrap(self, project):
        project = self.project_name(project)
        with self.connect() as db:
            chats = [dict(r) for r in db.execute("SELECT * FROM chats WHERE project=? ORDER BY updated_at DESC, rowid DESC", (project,))]
            projects = sorted({project, *[r[0] for r in db.execute("SELECT DISTINCT project FROM chats")], *[r[0] for r in db.execute("SELECT DISTINCT project FROM conventions")]})
        return {"project": project, "projects": projects, "chats": chats, "memory": self.memory(project), "config": self.public_config()}

    def create_chat(self, project):
        project = self.project_name(project)
        chat_id, stamp = uuid4().hex, now()
        with self.connect() as db:
            db.execute("INSERT INTO chats VALUES (?,?,?,?,?)", (chat_id, project, "Cuộc trò chuyện mới", stamp, stamp))
        return self.chat(chat_id)

    def chat(self, chat_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM chats WHERE id=?", (chat_id,)).fetchone()
            if not row:
                raise LookupError("Không tìm thấy cuộc trò chuyện.")
            turns = [self.decode_turn(r) for r in db.execute("SELECT * FROM turns WHERE chat_id=? ORDER BY created_at, rowid", (chat_id,))]
        return {**dict(row), "turns": turns}

    @staticmethod
    def decode_turn(row):
        turn = dict(row)
        for key in ("request", "extraction", "changes"):
            turn[key] = json.loads(turn.pop(key + "_json") or ("[]" if key == "changes" else "null"))
        return turn

    def send(self, body):
        chat_id, text, turn_id = body.get("chat_id"), body.get("text"), body.get("turn_id")
        if not isinstance(text, str) or not text.strip() or len(text) > 12000:
            raise ValueError("Tin nhắn cần từ 1 đến 12.000 ký tự.")
        if not isinstance(turn_id, str) or not re.fullmatch(r"[a-f0-9]{32}", turn_id):
            raise ValueError("Mã lượt chat không hợp lệ.")
        text = text.strip()
        chat = self.chat(chat_id)
        with self.connect() as db:
            existing = db.execute("SELECT * FROM turns WHERE id=?", (turn_id,)).fetchone()
            if existing and (existing["chat_id"] != chat_id or existing["user_text"] != text):
                raise ValueError("Mã lượt chat đã được dùng cho tin nhắn khác.")
            if existing and existing["status"] == "completed":
                return {"turn": self.decode_turn(existing), "memory": self.memory(chat["project"])}
            if not existing:
                stamp = now()
                db.execute("INSERT INTO turns (id,chat_id,user_text,created_at,updated_at) VALUES (?,?,?,?,?)", (turn_id, chat_id, text, stamp, stamp))
            else:
                db.execute("UPDATE turns SET status='pending', error=NULL WHERE id=?", (turn_id,))
        try:
            updates, extraction = extract_updates(text, self.config)
            with MemoryStore(self.path) as store:
                changes = store.remember_many(chat["project"], [(u["key"], u["value"]) for u in updates], f"User chat {chat_id}, turn {turn_id}: {text}", chat_id)
                active = store.active(chat["project"])
            history = []
            for turn in chat["turns"]:
                if turn["status"] == "completed":
                    history.extend([{"role": "user", "content": turn["user_text"]}, {"role": "assistant", "content": turn["assistant_text"]}])
            request = chat_request(chat["project"], active, history, text)
            with self.connect() as db:
                db.execute("UPDATE turns SET request_json=?,extraction_json=?,changes_json=? WHERE id=?", (dumps(request), dumps(extraction), dumps(changes), turn_id))
            if self.config["provider"] == "openai":
                result = responses_call(self.config, request)
                answer, request = result["text"], result["request"]
            else:
                answer = demo_answer(request, changes)
            with self.connect() as db:
                db.execute("UPDATE turns SET assistant_text=?,request_json=?,status='completed',error=NULL,updated_at=? WHERE id=?", (answer, dumps(request), now(), turn_id))
                title = chat["title"] if chat["title"] != "Cuộc trò chuyện mới" else text[:54]
                db.execute("UPDATE chats SET title=?,updated_at=? WHERE id=?", (title, now(), chat_id))
        except (ValueError, RuntimeError, sqlite3.Error) as exc:
            with self.connect() as db:
                db.execute("UPDATE turns SET status='failed',error=?,updated_at=? WHERE id=?", (str(exc), now(), turn_id))
            raise
        return {"turn": next(t for t in self.chat(chat_id)["turns"] if t["id"] == turn_id), "memory": self.memory(chat["project"])}

    def export(self, project):
        data = self.bootstrap(project)
        return {"project": project, "exported_at": now(), "memory": data["memory"], "chats": [self.chat(c["id"]) for c in data["chats"]]}


class ChatServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, app):
        self.app = app
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server: ChatServer

    def log_message(self, pattern, *args):
        # Never log request bodies or credentials.
        print(f"[web] {self.command} {urlsplit(self.path).path} {args[1] if len(args) > 1 else ''}", flush=True)

    def respond(self, status, body, content_type="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = dumps(body).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def allowed_host(self):
        port = self.server.server_port
        return self.headers.get("Host", "") in {f"127.0.0.1:{port}", f"localhost:{port}"}

    def do_GET(self):
        if not self.allowed_host():
            return self.respond(403, {"error": "Host không được phép."})
        url = urlsplit(self.path)
        query = parse_qs(url.query)
        try:
            with self.server.app.lock:
                if url.path == "/api/health":
                    return self.respond(200, {"ok": True, "app": "challenge-a-memory-chat"})
                if url.path == "/api/bootstrap":
                    return self.respond(200, self.server.app.bootstrap(query.get("project", ["Challenge A"])[0]))
                if url.path.startswith("/api/chats/"):
                    return self.respond(200, self.server.app.chat(url.path.rsplit("/", 1)[1]))
                if url.path == "/api/export":
                    return self.respond(200, self.server.app.export(query.get("project", ["Challenge A"])[0]))
            static = {"/": ("index.html", "text/html; charset=utf-8"), "/index.html": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/styles.css": ("styles.css", "text/css; charset=utf-8"), "/favicon.svg": ("favicon.svg", "image/svg+xml")}
            if url.path in static:
                filename, mime = static[url.path]
                return self.respond(200, (ROOT / "web" / filename).read_bytes(), mime)
            self.respond(404, {"error": "Không tìm thấy trang."})
        except (ValueError, LookupError) as exc:
            self.respond(404 if isinstance(exc, LookupError) else 400, {"error": str(exc)})

    def do_POST(self):
        origin = self.headers.get("Origin")
        if not self.allowed_host() or (origin and origin not in {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}) or self.headers.get("X-Memory-Chat") != "1":
            return self.respond(403, {"error": "Yêu cầu phải đến từ ứng dụng chat trên máy này."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 65536 or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                raise ValueError("Request JSON không hợp lệ hoặc quá lớn.")
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(body, dict):
                raise ValueError("Request phải là JSON object.")
            with self.server.app.lock:
                path = urlsplit(self.path).path
                if path == "/api/chats":
                    return self.respond(201, self.server.app.create_chat(body.get("project", "Challenge A")))
                if path == "/api/chat":
                    return self.respond(200, self.server.app.send(body))
                if path == "/api/settings":
                    return self.respond(200, self.server.app.settings(body))
                self.respond(404, {"error": "Không tìm thấy API."})
        except (ValueError, UnicodeDecodeError) as exc:
            self.respond(400, {"error": str(exc)})
        except LookupError as exc:
            self.respond(404, {"error": str(exc)})
        except RuntimeError as exc:
            self.respond(502, {"error": str(exc)})
        except sqlite3.Error:
            self.respond(500, {"error": "Không ghi được dữ liệu. Hãy thử lại."})


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", default=str(ROOT / "data" / "web-chat.sqlite3"))
    args = parser.parse_args()
    server = ChatServer(("127.0.0.1", args.port), ChatApp(args.db))
    if args.port == 8765:
        (ROOT / "output").mkdir(exist_ok=True)
        (ROOT / "output" / "web-server.pid").write_text(str(os.getpid()), encoding="utf-8")
    print(f"Memory Chat is running at http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
