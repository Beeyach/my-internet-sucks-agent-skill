from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).parents[1] / "skill" / "my-internet-sucks" / "scripts" / "netmode.py"
SPEC = importlib.util.spec_from_file_location("netmode", SCRIPT)
netmode = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(netmode)


class NetmodeTests(unittest.TestCase):
    def test_redacts_common_credentials(self):
        value = "--token=abc123 ghp_abcdefghijklmnopqrstuvwxyz123456 sk-abcdefghijklmnop"
        cleaned = netmode.redact(value)
        self.assertNotIn("abc123", cleaned)
        self.assertNotIn("ghp_", cleaned)
        self.assertNotIn("sk-abcdefghijklmnop", cleaned)
        self.assertGreaterEqual(cleaned.count("[REDACTED]"), 3)

    def test_network_error_classification(self):
        self.assertTrue(netmode.is_network_error("npm ERR! code ETIMEDOUT"))
        self.assertTrue(netmode.is_network_error("fatal: Could not resolve host"))
        self.assertFalse(netmode.is_network_error("SyntaxError: unexpected token"))

    def test_checkpoint_records_git_state_without_tracking_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "work.txt").write_text("change", encoding="utf-8")
            ledger = netmode.Ledger(root)
            args = argparse.Namespace(note="local work", next="npm ci")
            self.assertEqual(netmode.cmd_checkpoint(args, ledger), 0)
            state = ledger.load()
            changed = state["checkpoint"]["git"]["dirty_files"]
            self.assertEqual(changed, ["work.txt"])
            self.assertTrue((root / ".agent-netmode" / ".gitignore").is_file())

    def test_queue_defaults_to_verify_before_retry(self):
        data = {"jobs": []}
        job = netmode.add_job(data, "Deploy", "deploy", None, False)
        self.assertFalse(job["idempotent"])
        self.assertEqual(job["state"], "pending")

    def test_idempotent_run_retries_network_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = netmode.Ledger(Path(directory))
            args = argparse.Namespace(
                command=["--", "fake-command"],
                label="Fetch",
                kind="fetch",
                idempotent=True,
                retries=1,
            )
            results = [
                subprocess.CompletedProcess(["fake-command"], 1, "", "ETIMEDOUT"),
                subprocess.CompletedProcess(["fake-command"], 0, "ok\n", ""),
            ]
            with mock.patch.object(netmode.subprocess, "run", side_effect=results), mock.patch.object(netmode.time, "sleep"):
                self.assertEqual(netmode.cmd_run(args, ledger), 0)
            job = ledger.load()["jobs"][0]
            self.assertEqual(job["attempts"], 2)
            self.assertEqual(job["state"], "done")

    def test_non_idempotent_run_never_retries(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = netmode.Ledger(Path(directory))
            args = argparse.Namespace(
                command=["--", "fake-deploy"],
                label="Deploy",
                kind="deploy",
                idempotent=False,
                retries=5,
            )
            failed = subprocess.CompletedProcess(["fake-deploy"], 1, "", "connection reset")
            with mock.patch.object(netmode.subprocess, "run", return_value=failed) as runner:
                self.assertEqual(netmode.cmd_run(args, ledger), 75)
            self.assertEqual(runner.call_count, 1)
            job = ledger.load()["jobs"][0]
            self.assertEqual(job["attempts"], 1)
            self.assertEqual(job["state"], "failed")

    def test_status_json_is_machine_readable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            completed = subprocess.run(
                ["python3", str(SCRIPT), "--root", str(root), "status", "--json"],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["root"], str(root))
            self.assertEqual(payload["counts"]["pending"], 0)


if __name__ == "__main__":
    unittest.main()
