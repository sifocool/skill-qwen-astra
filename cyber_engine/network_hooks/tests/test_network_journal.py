#!/usr/bin/env python3
"""Offline behavioral tests; no network operations or model calls."""

import concurrent.futures
import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "network_journal.py"
SPEC = importlib.util.spec_from_file_location("network_journal", SCRIPT)
journal = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(journal)


def event(command="curl https://example.invalid/", kind="PreToolUse", **changes):
    data = {
        "hook_event_name": kind, "tool_name": "Bash",
        "session_id": "test-session", "tool_use_id": "test-call",
        "cwd": "/private/project", "tool_input": {"command": command},
    }
    data.update(changes)
    return data


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qwen-network-test-")
        self.root = Path(self.temp.name)
        self.logs = self.root / "logs"

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self, payload):
        raw = payload if isinstance(payload, str) else json.dumps(payload)
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--log-dir", str(self.logs)],
            input=raw, text=True, capture_output=True, timeout=10,
        )

    def test_secret_minimization(self):
        command = "curl -H 'Authorization: Bearer HEADER_SECRET' -d 'BODY_SECRET' 'https://USER_SECRET:PASS_SECRET@example.invalid/private/PATH_SECRET?api_key=QUERY_SECRET#FRAGMENT_SECRET'"
        record = journal.make_record(event(command, kind="PostToolUse", tool_response={
            "stdout": "RESPONSE_SECRET", "stderr": "ERROR_SECRET", "exit_code": 7,
        }))
        text = json.dumps(record)
        for secret in ("HEADER", "BODY", "USER", "PASS", "PATH", "QUERY", "FRAGMENT", "RESPONSE", "ERROR"):
            self.assertNotIn(secret + "_SECRET", text)
        self.assertNotIn("/private/project", text)
        self.assertEqual(record["origins"], ["https://example.invalid"])
        self.assertEqual(record["exit_code"], 7)
        self.assertEqual(record["outcome"], "tool_returned")

    def test_stable_correlation_and_honest_status(self):
        records = [journal.make_record(event(kind=kind)) for kind in sorted(journal.EVENTS)]
        self.assertEqual(len({r["tool_use_id_sha256"] for r in records}), 1)
        self.assertEqual(len({r["session_id_sha256"] for r in records}), 1)
        self.assertEqual({r["outcome"] for r in records}, {"requested", "tool_returned", "tool_failed"})
        self.assertTrue(all(r["network_observed"] is False for r in records))

    def test_urls_inside_shell_headers_and_bodies_are_excluded(self):
        command = "curl -H 'Referer: https://header-secret.invalid' --data='https://body-secret.invalid' -bhttps://cookie-secret.invalid --url=https://example.invalid/a"
        record = journal.make_record(event(command))
        self.assertEqual(record["origins"], ["https://example.invalid"])

    def test_local_commands_and_unrelated_events_ignored(self):
        for cmd in ("git status --short", "python3 local_test.py", "ls -la", "rg TODO src"):
            self.assertIsNone(journal.make_record(event(cmd)))
        self.assertIsNone(journal.make_record(event(kind="SessionStart")))
        self.assertIsNone(journal.make_record(event(tool_name="Read", tool_input={"file_path": "x"})))

    def test_network_commands_without_literal_url(self):
        for cmd in ("dig example.invalid", "git fetch origin", "curl \"$TARGET\"", "npm install", "/usr/bin/ssh test-host"):
            result = journal.make_record(event(cmd))
            self.assertIsNotNone(result, cmd)
            self.assertEqual(result["origins"], [])

    def test_web_and_mcp_metadata_only(self):
        result = journal.make_record(event(tool_name="mcp__real-browser-mcp__browser_navigate", tool_input={
            "url": "https://example.invalid/path?token=SECRET",
            "headers": {"Referer": "https://secret.invalid"},
            "body": {"url": "https://body-secret.invalid"},
        }))
        self.assertEqual(result["origins"], ["https://example.invalid"])
        result = journal.make_record(event(tool_name="WebSearch", tool_input={"query": "SEARCH_SECRET"}))
        self.assertEqual(result["origins"], [])
        self.assertNotIn("SEARCH_SECRET", json.dumps(result))
        result = journal.make_record(event(tool_name="mcp__custom__call", tool_input={"arguments": {"url": "https://example.invalid"}}))
        self.assertIsNotNone(result)

    def test_invalid_urls_and_ipv6(self):
        self.assertEqual(journal.origins(["https://[::1]:8443/a?key=x"]), ["https://[::1]:8443"])
        self.assertEqual(journal.origins(["https://example.invalid:BAD/x https://[broken/x"]), [])

    def test_failure_does_not_save_error(self):
        result = journal.make_record(event(kind="PostToolUseFailure", error="Exit code 28\nSECRET", duration_ms=22, is_interrupt=False))
        self.assertEqual(result["exit_code"], 28)
        self.assertEqual(result["duration_ms"], 22)
        self.assertNotIn("SECRET", json.dumps(result))

    def test_never_executes_input_or_emits_permission_decision(self):
        sentinel = self.root / "must-not-exist"
        result = self.invoke(event("curl https://example.invalid; touch " + str(sentinel)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse(sentinel.exists())
        self.assertEqual(len((self.logs / "network.jsonl").read_text().splitlines()), 1)

    def test_malformed_payload_is_nonblocking_and_private(self):
        for raw in ('{"SECRET":', 'x' * (journal.MAX_INPUT + 1)):
            result = self.invoke(raw)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("SECRET", result.stderr)
        self.assertFalse(self.logs.exists())

    def test_concurrent_appends_and_permissions(self):
        def call(number):
            return self.invoke(event(tool_use_id=str(number)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(call, range(40)))
        self.assertTrue(all(r.returncode == 0 for r in results), [r.stderr for r in results if r.returncode])
        path = self.logs / "network.jsonl"
        records = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual(len(records), 40)
        self.assertEqual(len({r["tool_use_id_sha256"] for r in records}), 40)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.logs.stat().st_mode), 0o700)

    def test_rotation_is_bounded_and_preserves_recent_records(self):
        for number in range(20):
            journal.append_record({"sequence": number}, self.logs, max_bytes=40)
        files = list(self.logs.glob("network.jsonl*"))
        self.assertEqual(len(files), journal.BACKUPS + 1)
        values = [json.loads(line)["sequence"] for path in files for line in path.read_text().splitlines()]
        self.assertIn(19, values)
        self.assertNotIn(0, values)
        self.assertEqual(len(values), len(set(values)))

    def test_symlink_does_not_overwrite_another_file(self):
        self.logs.mkdir()
        target = self.root / "protected"
        target.write_text("unchanged")
        (self.logs / "network.jsonl").symlink_to(target)
        result = self.invoke(event())
        self.assertEqual(result.returncode, 1)
        self.assertEqual(target.read_text(), "unchanged")

    def test_payload_cannot_choose_output_path(self):
        other = self.root / "not-a-log"
        result = self.invoke(event(log_dir=str(other), transcript_path=str(other)))
        self.assertEqual(result.returncode, 0)
        self.assertFalse(other.exists())
        self.assertTrue((self.logs / "network.jsonl").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
