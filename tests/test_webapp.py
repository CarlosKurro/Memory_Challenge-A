from __future__ import annotations

import http.client
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from uuid import uuid4

from chat_engine import demo_updates, validate_updates
from webapp import ChatApp, ChatServer

ROOT = Path(__file__).resolve().parents[1]


class WebChatTests(unittest.TestCase):
    def setUp(self):
        base = (ROOT / "tmp" / "web-tests").resolve()
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=base)
        if not Path(self.temp.name).resolve().is_relative_to(base):
            raise RuntimeError("Temp escaped workspace")
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "chat.sqlite3"
        self.start_server()
        self.addCleanup(self.stop_server)

    def start_server(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "OPENAI_MODEL": "gpt-5-mini"}):
            self.app = ChatApp(self.db)
        self.server = ChatServer(("127.0.0.1", 0), self.app)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        self.thread.start()

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def request(self, method, path, data=None, headers=None):
        client = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)
        body = None if data is None else json.dumps(data).encode("utf-8")
        sent_headers = {"Content-Type": "application/json", "X-Memory-Chat": "1", **(headers or {})}
        client.request(method, path, body, sent_headers)
        response = client.getresponse()
        content = response.read()
        status, mime = response.status, response.getheader("Content-Type", "")
        client.close()
        return status, json.loads(content) if "application/json" in mime else content

    def create(self, project="test-project"):
        status, data = self.request("POST", "/api/chats", {"project": project})
        self.assertEqual(status, 201)
        return data

    def send(self, chat, text, turn=None):
        return self.request("POST", "/api/chat", {"chat_id": chat["id"], "text": text, "turn_id": turn or uuid4().hex})

    def test_challenge_a_in_natural_chat_and_new_sessions(self):
        first = self.create()
        status, result = self.send(first, "Dự án dùng TypeScript, PostgreSQL và JWT. Chúng ta chọn API REST /api/v1 với JSON snake_case.")
        self.assertEqual(status, 200)
        self.assertEqual(len(result["memory"]["active"]), 4)
        second = self.create()
        self.assertEqual(second["turns"], [])
        status, recalled = self.send(second, "Hãy lên kế hoạch endpoint hồ sơ theo quy ước dự án.")
        self.assertEqual(status, 200)
        self.assertIn("TypeScript", recalled["turn"]["assistant_text"])
        self.assertIn("JWT", recalled["turn"]["assistant_text"])
        self.assertEqual(len(recalled["turn"]["request"]["input"]), 2)
        self.assertEqual(self.send(second, "Chuyển authentication từ JWT sang session cookie.")[0], 200)
        for _ in range(2):
            later = self.create()
            status, result = self.send(later, "Lập kế hoạch middleware đăng nhập.")
            self.assertEqual(status, 200)
            self.assertIn("session cookie", result["turn"]["assistant_text"])
            self.assertNotIn("jwt", json.dumps(result["turn"]["request"]).lower())
            self.assertEqual(len(result["turn"]["request"]["input"]), 2)
        auth = [m for m in result["memory"]["history"] if m["key"] == "authentication"]
        self.assertEqual([m["status"] for m in auth], ["superseded", "active"])
        self.assertEqual(auth[0]["superseded_by"], auth[1]["id"])

    def test_history_belongs_only_to_current_chat(self):
        first = self.create()
        self.send(first, "Xin chào")
        _, result = self.send(first, "Tin nhắn trước của tôi là gì?")
        self.assertIn("Xin chào", result["turn"]["assistant_text"])
        self.assertEqual(len(result["turn"]["request"]["input"]), 4)
        second = self.create()
        _, fresh = self.send(second, "Tin nhắn trước của tôi là gì?")
        self.assertNotIn("Xin chào", json.dumps(fresh["turn"]["request"]))
        self.assertEqual(len(fresh["turn"]["request"]["input"]), 2)

    def test_restart_retains_chats_and_memory_but_not_config_key(self):
        chat = self.create()
        self.send(chat, "Dự án dùng Python và SQLite.")
        self.app.config["api_key"] = "fake-secret-only-in-ram"
        self.stop_server()
        self.start_server()
        status, saved = self.request("GET", "/api/chats/" + chat["id"])
        self.assertEqual(status, 200)
        self.assertEqual(len(saved["turns"]), 1)
        new = self.create()
        _, result = self.send(new, "Dự án đang dùng stack nào?")
        self.assertIn("SQLite", result["turn"]["assistant_text"])
        self.assertEqual(self.app.config["api_key"], "")

    def test_projects_are_isolated(self):
        first, second = self.create("a"), self.create("b")
        self.send(first, "Dự án dùng TypeScript và JWT.")
        _, result = self.send(second, "Bạn đang nhớ quy ước gì của dự án?")
        self.assertEqual(result["memory"]["active"], [])
        self.assertNotIn("TypeScript", json.dumps(result["turn"]["request"]))

    def test_questions_quotes_hypotheticals_and_negations_are_not_decisions(self):
        samples = ["Có nên dùng PostgreSQL và JWT không?", "Nếu dự án dùng Python thì sao?", "Ví dụ dự án dùng Go.", 'Ví dụ: "Dự án dùng TypeScript".', "Dự án không dùng JWT.", "Không chuyển authentication sang session cookie.", "Xin chào", "Hãy giải thích PostgreSQL."]
        for text in samples:
            with self.subTest(text=text):
                self.assertEqual(demo_updates(text), [])
        chat = self.create()
        self.send(chat, "Dự án dùng JWT.")
        _, result = self.send(chat, "Có nên chuyển sang session cookie không?")
        self.assertEqual(result["memory"]["active"][0]["value"], "JWT")
        self.assertEqual(len(result["memory"]["history"]), 1)

    def test_same_turn_is_idempotent_and_new_value_same_is_noop(self):
        chat = self.create()
        turn = uuid4().hex
        self.send(chat, "Dự án dùng JWT.", turn)
        self.assertEqual(self.send(chat, "Dự án dùng JWT.", turn)[0], 200)
        _, saved = self.request("GET", "/api/chats/" + chat["id"])
        self.assertEqual(len(saved["turns"]), 1)
        _, result = self.send(chat, "Dự án dùng JWT.")
        self.assertEqual(result["turn"]["changes"][0]["action"], "unchanged")
        self.assertEqual(len(result["memory"]["history"]), 1)
        self.assertEqual(self.send(chat, "Tin nhắn khác", turn)[0], 400)

    def test_extractor_validates_exact_evidence_and_secret_keys(self):
        for update in [{"key": "language", "value": "Go", "evidence": "not in user message"}, {"key": "api_key", "value": "fake", "evidence": "message"}]:
            with self.subTest(update=update), self.assertRaises(ValueError):
                validate_updates({"updates": [update]}, "message")

    def test_settings_export_and_disk_do_not_reveal_api_key(self):
        fake = "test-only-secret-never-write-to-disk"
        status, config = self.request("POST", "/api/settings", {"provider": "openai", "model": "test-model", "api_key": fake})
        self.assertEqual(status, 200)
        self.assertTrue(config["has_api_key"])
        chat = self.create()
        _, bootstrap = self.request("GET", "/api/bootstrap?project=test-project")
        _, exported = self.request("GET", "/api/export?project=test-project")
        self.assertNotIn(fake, json.dumps([config, bootstrap, exported]))
        self.assertNotIn(fake.encode(), self.db.read_bytes())
        self.assertEqual(chat["turns"], [])

    def test_missing_key_blocks_ai_configuration(self):
        status, result = self.request("POST", "/api/settings", {"provider": "openai", "model": "test-model"})
        self.assertEqual(status, 400)
        self.assertEqual(self.app.config["provider"], "demo")

    def test_ai_uses_two_stages_and_updated_memory_in_final_request(self):
        chat = self.create()
        self.send(chat, "Dự án dùng JWT.")
        self.app.config.update(provider="openai", api_key="fake", model="test-model")
        text = "Chuyển authentication sang session cookie."
        calls = []
        def fake_call(config, request):
            calls.append(request)
            if "text" in request:
                return {"text": json.dumps({"updates": [{"key": "authentication", "value": "session cookie", "evidence": text}]}), "usage": {}, "request": request}
            return {"text": "Đã đổi sang session cookie.", "usage": {}, "request": {**request, "model": config["model"]}}
        with patch("chat_engine.responses_call", side_effect=fake_call), patch("webapp.responses_call", side_effect=fake_call):
            status, result = self.send(chat, text)
        self.assertEqual(status, 200)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["input"], [{"role": "user", "content": text}])
        injected = json.loads(calls[1]["input"][0]["content"].split("\n", 1)[1])
        self.assertEqual(injected["active_conventions"][0]["value"], "session cookie")
        self.assertNotIn("JWT", calls[1]["input"][0]["content"])
        self.assertEqual(result["turn"]["extraction"]["method"], "openai-structured-output")

    def test_generation_failure_is_retryable_without_duplicate_user_message(self):
        chat = self.create()
        self.app.config.update(provider="openai", api_key="fake", model="test-model")
        text, turn_id = "Dự án dùng Python.", uuid4().hex
        extraction = {"text": json.dumps({"updates": [{"key": "language", "value": "Python", "evidence": text}]}), "usage": {}, "request": {}}
        with patch("chat_engine.responses_call", return_value=extraction), patch("webapp.responses_call", side_effect=RuntimeError("Model unavailable")):
            self.assertEqual(self.send(chat, text, turn_id)[0], 502)
        _, failed = self.request("GET", "/api/chats/" + chat["id"])
        self.assertEqual(failed["turns"][0]["status"], "failed")
        self.assertIsNotNone(failed["turns"][0]["request"])
        self.app.config["provider"] = "demo"
        status, result = self.send(chat, text, turn_id)
        self.assertEqual(status, 200)
        self.assertEqual(len(result["memory"]["history"]), 1)
        _, saved = self.request("GET", "/api/chats/" + chat["id"])
        self.assertEqual(len(saved["turns"]), 1)
        self.assertEqual(saved["turns"][0]["status"], "completed")

    def test_static_and_request_boundaries(self):
        for path in ("/", "/styles.css", "/app.js", "/favicon.svg"):
            self.assertEqual(self.request("GET", path)[0], 200)
        self.assertEqual(self.request("GET", "/slide.pdf")[0], 404)
        self.assertEqual(self.request("POST", "/api/chats", {"project": "x"}, {"Origin": "https://unrelated.example"})[0], 403)
        self.assertEqual(self.request("POST", "/api/chats", {"project": "x"}, {"X-Memory-Chat": ""})[0], 403)
        self.assertEqual(self.request("GET", "/api/health", headers={"Host": "unrelated.example"})[0], 403)
        self.assertEqual(self.request("POST", "/api/chat", {"text": ""})[0], 400)


if __name__ == "__main__":
    unittest.main()
