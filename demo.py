"""Run five independent processes and verify the two Challenge A requirements."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from memory_agent import MemoryStore, dumps


ROOT = Path(__file__).resolve().parent


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("offline", "openai"), default="offline")
    args = parser.parse_args()
    if args.provider == "openai" and not all(os.environ.get(k) for k in ("OPENAI_API_KEY", "OPENAI_MODEL")):
        parser.error("Cần OPENAI_API_KEY và OPENAI_MODEL cho demo LLM thật.")
    tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    output = ROOT / "output" / "demo" / tag
    output.mkdir(parents=True)
    db = output / "memory.sqlite3"
    initial = {"language": "TypeScript", "database": "PostgreSQL", "authentication": "JWT", "api_style": "REST /api/v1; snake_case JSON"}
    specs = [
        ("s1-establish", "Ghi nhận các quyết định dự án.", initial, "Demo user S1: thống nhất stack và API"),
        ("s2-cold-start", "Đề xuất kế hoạch triển khai endpoint lấy hồ sơ người dùng.", {}, None),
        ("s3-change", "Cập nhật quyết định authentication đã được xác nhận.", {"authentication": "session cookie"}, "Demo user S3: chuyển từ JWT sang session cookie"),
        ("s4-cold-start", "Đề xuất kế hoạch triển khai endpoint đăng xuất.", {}, None),
        ("s5-cold-start", "Đề xuất kế hoạch triển khai middleware kiểm tra đăng nhập.", {}, None),
    ]
    records = []
    for label, task, decisions, source in specs:
        command = [sys.executable, "-X", "utf8", str(ROOT / "memory_agent.py"), "run",
                   "--db", str(db), "--project", "course-project", "--provider", args.provider,
                   "--artifacts", str(output / label), "--task", task]
        for key, value in decisions.items():
            command.extend(["--remember", f"{key}={value}"])
        if source:
            command.extend(["--source", source])
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=90)
        (output / f"{label}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        print(f"\n--- {label}: exit={result.returncode} ---\n{result.stdout}", end="")
        if result.returncode:
            print(result.stderr)
            return result.returncode
        artifacts = list((output / label).glob("*.json"))
        if len(artifacts) != 1:
            raise AssertionError("Mỗi session phải có đúng một request/response artifact.")
        records.append(json.loads(artifacts[0].read_text(encoding="utf-8")))

    def injected(record: dict) -> dict:
        data = json.loads(record["request"]["input"][0]["content"].split("\n", 1)[1])
        return {item["key"]: item["value"] for item in data["active_conventions"]}

    checks = {}
    def check(name: str, condition: bool) -> None:
        checks[name] = bool(condition)
        if not condition:
            raise AssertionError(name)

    check("five_distinct_sessions", len({r["session_id"] for r in records}) == 5)
    check("five_distinct_processes", len({r["process_id"] for r in records}) == 5)
    check("s2_recalls_all_original_conventions", injected(records[1]) == initial)
    check("s2_task_does_not_repeat_conventions", all(v.lower() not in records[1]["request"]["input"][1]["content"].lower() for v in initial.values()))
    updated = {**initial, "authentication": "session cookie"}
    for i in (3, 4):
        check(f"s{i+1}_uses_new_memory", injected(records[i]) == updated)
        check(f"s{i+1}_no_stale_jwt_in_request", "jwt" not in dumps(records[i]["request"]).lower())
    check("no_previous_history_in_requests", all(len(r["request"]["input"]) == 2 and "previous_response_id" not in r["request"] for r in records))
    with MemoryStore(db) as store:
        history = store.history("course-project")
    (output / "memory-history.json").write_text(dumps(history) + "\n", encoding="utf-8")
    auth = [row for row in history if row["key"] == "authentication"]
    check("jwt_is_superseded", len(auth) == 2 and auth[0]["value"] == "JWT" and auth[0]["status"] == "superseded")
    check("cookie_is_active_v2", auth[1]["value"] == "session cookie" and auth[1]["status"] == "active" and auth[1]["version"] == 2)
    check("history_has_provenance", bool(auth[0]["source"] and auth[0]["created_at"] and auth[0]["superseded_at"] and auth[0]["superseded_by"] == auth[1]["id"]))
    if args.provider == "offline":
        check("s2_agent_uses_old_conventions", records[1]["response"]["conventions_used"] == initial)
        check("s4_agent_uses_new_conventions", records[3]["response"]["conventions_used"] == updated)
        check("s5_agent_uses_new_conventions", records[4]["response"]["conventions_used"] == updated)
    summary = {
        "provider": args.provider,
        "llm_called": args.provider == "openai",
        "llm_answer_semantics_verified": False,
        "note": "Offline asserts planner output. API mode asserts memory injection only; review model answers manually.",
        "checks": checks, "passed": all(checks.values()),
        "session_ids": [r["session_id"] for r in records],
        "process_ids": [r["process_id"] for r in records],
        "prompt_sha256": hashlib.sha256((ROOT / "PROMPT_CHALLENGE_A.md").read_bytes()).hexdigest(),
    }
    (output / "verification.json").write_text(dumps(summary) + "\n", encoding="utf-8")
    # Pointer only: never overwrite a previous run's database or evidence.
    (ROOT / "output" / "LATEST_DEMO.txt").write_text(str(output.relative_to(ROOT)) + "\n", encoding="utf-8")
    print(f"\nPASS: {len(checks)}/{len(checks)} checks. Evidence: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
