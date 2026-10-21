from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

from memory_agent import MemoryStore, build_request, offline_agent, openai_agent, run_session


ROOT = Path(__file__).resolve().parents[1]


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        test_root = (ROOT / "tmp" / "tests").resolve()
        test_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=test_root)
        # TemporaryDirectory recursively cleans up; constrain it to this workspace.
        if not Path(self.temp.name).resolve().is_relative_to(test_root):
            raise RuntimeError("Test directory escaped workspace.")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / "memory.sqlite3"

    def write(self, store, value="JWT", project="p", session="s1"):
        return store.remember_many(project, [("authentication", value)], "User decision", session)

    def cli(self, *extra):
        command = [sys.executable, "-X", "utf8", str(ROOT / "memory_agent.py"), "run",
                   "--db", str(self.db), "--project", "p", "--artifacts", str(self.root / "sessions"),
                   "--task", "Lập kế hoạch endpoint hồ sơ.", *extra]
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        artifact = result.stdout.rsplit("ARTIFACT ", 1)[1].strip()
        return json.loads(Path(artifact).read_text(encoding="utf-8"))

    def test_new_process_remembers_and_later_process_uses_replacement(self):
        first = self.cli("--remember", "language=Rust", "--remember", "database=SQLite",
                         "--remember", "authentication=JWT", "--source", "User S1")
        second = self.cli()
        self.assertNotEqual(first["session_id"], second["session_id"])
        self.assertNotEqual(first["process_id"], second["process_id"])
        self.assertEqual(second["response"]["conventions_used"], {
            "language": "Rust", "database": "SQLite", "authentication": "JWT"})
        self.cli("--remember", "authentication=session cookie", "--source", "Replace JWT by cookie")
        fourth = self.cli()
        self.assertEqual(fourth["response"]["conventions_used"]["authentication"], "session cookie")
        self.assertNotIn("jwt", json.dumps(fourth["request"]).lower())
        self.assertEqual(len(fourth["request"]["input"]), 2)

    def test_history_preserves_source_time_session_and_successor(self):
        with MemoryStore(self.db) as store:
            self.write(store)
            self.write(store, "session cookie", session="s3")
            old, new = store.history("p")
            self.assertEqual((old["status"], new["status"]), ("superseded", "active"))
            self.assertEqual((old["version"], new["version"]), (1, 2))
            self.assertEqual(old["superseded_by"], new["id"])
            self.assertEqual(old["superseded_at"], new["created_at"])
            self.assertEqual((old["created_session"], new["created_session"]), ("s1", "s3"))
            self.assertEqual(old["source"], "User decision")
            self.assertTrue(old["created_at"])
            self.assertEqual(len(store.active("p")), 1)

    def test_same_value_is_noop_preserving_provenance(self):
        with MemoryStore(self.db) as store:
            self.write(store)
            before = store.history("p")
            result = self.write(store, session="s2")
            self.assertEqual(result[0]["action"], "unchanged")
            self.assertEqual(store.history("p"), before)

    def test_project_isolation(self):
        with MemoryStore(self.db) as store:
            self.write(store, project="a")
            self.write(store, "session cookie", project="b")
            self.assertEqual(store.active("a")[0]["value"], "JWT")
            self.assertEqual(store.active("b")[0]["value"], "session cookie")
            self.assertEqual(store.active("c"), [])

    def test_failed_insert_rolls_back_retirement_and_other_decisions(self):
        with MemoryStore(self.db) as store:
            self.write(store)
            before = store.history("p")
            store.db.executescript("""CREATE TRIGGER fail_cookie BEFORE INSERT ON conventions
                WHEN NEW.value = 'session cookie'
                BEGIN SELECT RAISE(ABORT, 'injected write failure'); END;""")
            with self.assertRaises(sqlite3.IntegrityError):
                store.remember_many("p", [("language", "Rust"), ("authentication", "session cookie")], "User S3", "s3")
            self.assertEqual(store.history("p"), before)
            self.assertEqual(store.active("p")[0]["value"], "JWT")

    def test_sqlite_prevents_two_active_versions(self):
        with MemoryStore(self.db) as store:
            self.write(store)
            with self.assertRaises(sqlite3.IntegrityError), store.db:
                store.db.execute("""INSERT INTO conventions
                    (project,key,value,version,status,source,created_session,created_at)
                    VALUES ('p','authentication','other',2,'active','x','s2','t')""")
            self.assertEqual(len(store.active("p")), 1)

    def test_reverting_to_old_value_creates_new_version(self):
        with MemoryStore(self.db) as store:
            self.write(store)
            self.write(store, "session cookie")
            self.write(store, "JWT")
            self.assertEqual([r["version"] for r in store.history("p")], [1, 2, 3])
            self.assertEqual(store.active("p")[0]["version"], 3)

    def test_invalid_or_duplicate_keys_do_not_partially_write(self):
        with MemoryStore(self.db) as store:
            for decisions in ([ ("language", "Rust"), ("INVALID KEY", "x") ],
                              [ ("language", "Rust"), ("language", "Go") ],
                              [ ("language", " ") ]):
                with self.subTest(decisions=decisions), self.assertRaises(ValueError):
                    store.remember_many("p", decisions, "User", "s")
                self.assertEqual(store.history("p"), [])

    def test_missing_source_is_rejected(self):
        with MemoryStore(self.db) as store:
            with self.assertRaises(ValueError):
                store.remember_many("p", [("language", "Go")], "", "s")
            self.assertEqual(store.history("p"), [])

    def test_empty_memory_does_not_invent_conventions(self):
        result = offline_agent(build_request("p", [], "Lập kế hoạch."))
        self.assertEqual(result["conventions_used"], {})
        self.assertNotIn("PostgreSQL", json.dumps(result))
        self.assertIn("authentication", result["plan"][0])

    def test_request_uses_retrieved_values_not_default_stack(self):
        with MemoryStore(self.db) as store:
            store.remember_many("p", [("language", "Go"), ("database", "MariaDB")], "User", "s")
            request = build_request("p", store.active("p"), "Lập kế hoạch.")
        output = offline_agent(request)
        self.assertEqual(output["conventions_used"], {"language": "Go", "database": "MariaDB"})
        self.assertNotIn("previous_response_id", request)
        self.assertNotIn("conversation", request)
        self.assertFalse(request["store"])

    def test_failed_model_call_saves_failure_and_keeps_explicit_decision(self):
        args = argparse.Namespace(db=self.db, project="p", provider="openai", task="Task",
                                  remember=[("language", "Go")], source="User", artifacts=self.root / "artifacts")
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-secret", "OPENAI_MODEL": "test-model"}), \
                patch("memory_agent.openai_agent", side_effect=RuntimeError("test failure")), \
                patch("sys.stdout", new_callable=io.StringIO):
            with self.assertRaisesRegex(RuntimeError, "test failure"):
                run_session(args)
        artifact = json.loads(next((self.root / "artifacts").glob("*.json")).read_text(encoding="utf-8"))
        self.assertEqual(artifact["status"], "failed")
        self.assertNotIn("test-secret", json.dumps(artifact))
        with MemoryStore(self.db) as store:
            self.assertEqual(store.active("p")[0]["value"], "Go")

    def test_missing_api_config_fails_before_writing_database(self):
        args = argparse.Namespace(db=self.db, project="p", provider="openai", task="Task",
                                  remember=[("language", "Go")], source="User", artifacts=self.root / "artifacts")
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            run_session(args)
        self.assertFalse(self.db.exists())


class ApiAdapterContractTests(unittest.TestCase):
    """Mocked HTTP contracts only, not evidence of actual model quality."""

    def response(self, payload):
        return io.BytesIO(json.dumps(payload).encode("utf-8"))

    def test_completed_response_skips_reasoning_and_sends_exact_memory(self):
        request = build_request("p", [], "Kế hoạch.")
        payload = {"status": "completed", "output": [
            {"type": "reasoning", "summary": []},
            {"type": "message", "content": [{"type": "output_text", "text": "Kế hoạch."}]}],
            "usage": {"input_tokens": 10}}
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-secret", "OPENAI_MODEL": "test-model"}), \
                patch("urllib.request.urlopen", return_value=self.response(payload)) as mocked:
            result = openai_agent(request)
        sent = mocked.call_args.args[0]
        self.assertEqual(sent.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(json.loads(sent.data), request)
        self.assertEqual(result["text"], "Kế hoạch.")
        self.assertEqual(result["model"], "test-model")
        self.assertNotIn("test-secret", json.dumps(request))

    def test_incomplete_or_refusal_is_not_success(self):
        for payload in ({"status": "incomplete", "output": []},
                        {"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "No"}]}]}):
            with self.subTest(payload=payload), \
                    patch.dict(os.environ, {"OPENAI_API_KEY": "test-secret", "OPENAI_MODEL": "test-model"}), \
                    patch("urllib.request.urlopen", return_value=self.response(payload)), \
                    self.assertRaises(RuntimeError):
                openai_agent(build_request("p", [], "Task"))

    def test_http_error_does_not_leak_key_or_fallback(self):
        error = urllib.error.HTTPError("https://api.openai.com/v1/responses", 401, "unauthorized", {}, None)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-secret", "OPENAI_MODEL": "test-model"}), \
                patch("urllib.request.urlopen", side_effect=error), \
                self.assertRaisesRegex(RuntimeError, "HTTP 401") as caught:
            openai_agent(build_request("p", [], "Task"))
        self.assertNotIn("test-secret", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
