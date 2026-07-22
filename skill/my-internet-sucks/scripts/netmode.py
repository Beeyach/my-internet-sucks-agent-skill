#!/usr/bin/env python3
"""A local checkpoint and network-job ledger for interruption-prone agent work."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
from pathlib import Path
import re
import shlex
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid

SCHEMA_VERSION = 1
STATE_DIR = ".agent-netmode"
STATE_FILE = "state.json"
NETWORK_PATTERNS = (
    "temporary failure in name resolution",
    "could not resolve host",
    "connection reset",
    "connection timed out",
    "network is unreachable",
    "no route to host",
    "tls handshake timeout",
    "unable to access",
    "econnreset",
    "etimedout",
    "enetunreach",
    "eai_again",
    "socket hang up",
    "remote end closed connection",
)
SECRET_PATTERNS = (
    re.compile(r"(?i)\b(token|password|passwd|secret|api[_-]?key|authorization)(\s*[:=]\s*|\s+)([^\s]+)"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"(https?://[^\s/:]+:)([^@\s]+)(@)"),
)


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def redact(value: str) -> str:
    text = value
    text = SECRET_PATTERNS[0].sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", text)
    for pattern in SECRET_PATTERNS[1:5]:
        text = pattern.sub("[REDACTED]", text)
    text = SECRET_PATTERNS[5].sub(r"\1[REDACTED]\3", text)
    return text


def run_git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def project_root(start: Path) -> Path:
    found = run_git(start, "rev-parse", "--show-toplevel")
    return Path(found).resolve() if found else start.resolve()


class Ledger:
    def __init__(self, root: Path):
        self.root = root
        self.directory = root / STATE_DIR
        self.path = self.directory / STATE_FILE
        self.lock_path = self.directory / ".lock"

    def _new(self) -> dict:
        timestamp = now()
        return {
            "version": SCHEMA_VERSION,
            "root": str(self.root),
            "created_at": timestamp,
            "updated_at": timestamp,
            "checkpoint": None,
            "jobs": [],
        }

    def load(self) -> dict:
        if not self.path.exists():
            return self._new()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"Cannot read {self.path}: {exc}") from exc
        if data.get("version") != SCHEMA_VERSION:
            raise SystemExit(f"Unsupported ledger version in {self.path}")
        return data

    @contextlib.contextmanager
    def lock(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        ignore = self.directory / ".gitignore"
        if not ignore.exists():
            ignore.write_text("*\n", encoding="utf-8")
        deadline = time.monotonic() + 2.0
        handle = None
        while handle is None:
            try:
                handle = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise SystemExit(f"Ledger is busy: {self.lock_path}")
                time.sleep(0.05)
        try:
            os.write(handle, str(os.getpid()).encode("ascii"))
            os.close(handle)
            yield
        finally:
            with contextlib.suppress(FileNotFoundError):
                self.lock_path.unlink()

    def save(self, data: dict) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        ignore = self.directory / ".gitignore"
        if not ignore.exists():
            ignore.write_text("*\n", encoding="utf-8")
        data["updated_at"] = now()
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.directory, delete=False
        ) as tmp:
            json.dump(data, tmp, indent=2, sort_keys=True)
            tmp.write("\n")
            temp_path = Path(tmp.name)
        os.replace(temp_path, self.path)


def git_snapshot(root: Path) -> dict:
    branch = run_git(root, "branch", "--show-current")
    head = run_git(root, "rev-parse", "--short", "HEAD")
    porcelain = run_git(root, "status", "--porcelain=v1")
    files = [] if porcelain is None else [line[3:] for line in porcelain.splitlines()]
    return {
        "branch": branch,
        "head": head,
        "dirty_files": files[:200],
        "dirty_file_count": len(files),
    }


def find_job(data: dict, job_id: str) -> dict:
    for job in data["jobs"]:
        if job["id"] == job_id:
            return job
    raise SystemExit(f"Unknown job id: {job_id}")


def add_job(data: dict, label: str, kind: str, resume: str | None, idempotent: bool) -> dict:
    job = {
        "id": uuid.uuid4().hex[:8],
        "label": redact(label),
        "kind": kind,
        "resume": redact(resume) if resume else None,
        "idempotent": idempotent,
        "state": "pending",
        "attempts": 0,
        "created_at": now(),
        "updated_at": now(),
        "last_error": None,
    }
    data["jobs"].append(job)
    return job


def command_text(argv: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(argv)
    return shlex.join(argv)


def is_network_error(text: str) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in NETWORK_PATTERNS)


def cmd_checkpoint(args: argparse.Namespace, ledger: Ledger) -> int:
    with ledger.lock():
        data = ledger.load()
        data["checkpoint"] = {
            "at": now(),
            "note": redact(args.note),
            "next": redact(args.next) if args.next else None,
            "git": git_snapshot(ledger.root),
        }
        ledger.save(data)
    print(f"Checkpoint saved to {ledger.path}")
    return 0


def cmd_queue(args: argparse.Namespace, ledger: Ledger) -> int:
    with ledger.lock():
        data = ledger.load()
        job = add_job(data, args.label, args.kind, args.resume, args.idempotent)
        ledger.save(data)
    print(f"Queued {job['id']}: {job['label']}")
    return 0


def update_job(args: argparse.Namespace, ledger: Ledger, state: str) -> int:
    with ledger.lock():
        data = ledger.load()
        job = find_job(data, args.job_id)
        job["state"] = state
        job["updated_at"] = now()
        if state == "running":
            job["attempts"] += 1
        if state == "failed":
            job["last_error"] = redact(args.error)[:4000]
        elif state == "done":
            job["last_error"] = None
        ledger.save(data)
    print(f"{job['id']} marked {state}")
    return 0


def summary(data: dict) -> dict:
    counts = {state: 0 for state in ("pending", "running", "failed", "done")}
    for job in data["jobs"]:
        counts[job["state"]] = counts.get(job["state"], 0) + 1
    return {
        "root": data["root"],
        "updated_at": data["updated_at"],
        "checkpoint": data["checkpoint"],
        "counts": counts,
        "jobs": data["jobs"],
    }


def cmd_status(args: argparse.Namespace, ledger: Ledger) -> int:
    data = ledger.load()
    view = summary(data)
    if args.json:
        print(json.dumps(view, indent=2, sort_keys=True))
        return 0
    print(f"Root: {view['root']}")
    checkpoint = view["checkpoint"]
    if checkpoint:
        print(f"Checkpoint: {checkpoint['at']} | {checkpoint['note']}")
        if checkpoint.get("next"):
            print(f"Next: {checkpoint['next']}")
        git = checkpoint.get("git", {})
        if git.get("branch") or git.get("head"):
            print(f"Git: {git.get('branch') or '(detached)'} @ {git.get('head') or 'unknown'}")
        print(f"Changed files at checkpoint: {git.get('dirty_file_count', 0)}")
    else:
        print("Checkpoint: none")
    print("Jobs: " + ", ".join(f"{key}={value}" for key, value in view["counts"].items()))
    return 0


def cmd_resume(_args: argparse.Namespace, ledger: Ledger) -> int:
    data = ledger.load()
    active = [job for job in data["jobs"] if job["state"] != "done"]
    if not active:
        print("No unfinished network jobs.")
        return 0
    for job in active:
        caution = "safe to retry" if job["idempotent"] else "VERIFY REMOTE STATE FIRST"
        print(f"[{job['id']}] {job['state']} | {caution} | {job['label']}")
        if job.get("resume"):
            print(f"  Resume: {job['resume']}")
        if job.get("last_error"):
            print(f"  Last error: {job['last_error']}")
    return 0


def probe_once(url: str, timeout: float) -> tuple[bool, float, str | None]:
    started = time.monotonic()
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "netmode/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout):
            pass
        return True, time.monotonic() - started, None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, time.monotonic() - started, redact(str(exc))


def cmd_probe(args: argparse.Namespace, _ledger: Ledger) -> int:
    results = []
    for url in args.url:
        samples = []
        errors = []
        for _ in range(args.attempts):
            ok, elapsed, error = probe_once(url, args.timeout)
            if ok:
                samples.append(elapsed)
            elif error:
                errors.append(error)
        results.append({
            "url": redact(url),
            "attempts": args.attempts,
            "successes": len(samples),
            "median_ms": round(statistics.median(samples) * 1000) if samples else None,
            "max_ms": round(max(samples) * 1000) if samples else None,
            "errors": errors,
        })
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for item in results:
            latency = "n/a" if item["median_ms"] is None else f"{item['median_ms']} ms median"
            print(f"{item['url']}: {item['successes']}/{item['attempts']} successful, {latency}")
            for error in item["errors"]:
                print(f"  {error}")
    if all(item["successes"] == 0 for item in results):
        return 2
    if any(item["successes"] < item["attempts"] for item in results):
        return 1
    return 0


def cmd_run(args: argparse.Namespace, ledger: Ledger) -> int:
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise SystemExit("Provide a command after --")
    attempts_allowed = 1 + (args.retries if args.idempotent else 0)
    with ledger.lock():
        data = ledger.load()
        job = add_job(data, args.label, args.kind, command_text(command), args.idempotent)
        ledger.save(data)
    for attempt in range(1, attempts_allowed + 1):
        with ledger.lock():
            data = ledger.load()
            current = find_job(data, job["id"])
            current["state"] = "running"
            current["attempts"] = attempt
            current["updated_at"] = now()
            ledger.save(data)
        try:
            completed = subprocess.run(command, check=False, capture_output=True, text=True)
            stdout, stderr = completed.stdout, completed.stderr
        except FileNotFoundError as exc:
            stdout, stderr = "", str(exc)
            completed = None
        if stdout:
            print(stdout, end="")
        if stderr:
            print(stderr, end="", file=sys.stderr)
        returncode = completed.returncode if completed is not None else 127
        if returncode == 0:
            done_args = argparse.Namespace(job_id=job["id"])
            update_job(done_args, ledger, "done")
            return 0
        network_failure = is_network_error(f"{stdout}\n{stderr}")
        if attempt < attempts_allowed and network_failure:
            delay = min(2 ** attempt, 15)
            print(f"Network failure. Retrying in {delay}s ({attempt}/{attempts_allowed - 1}).", file=sys.stderr)
            time.sleep(delay)
            continue
        fail_args = argparse.Namespace(job_id=job["id"], error=stderr or stdout or f"exit {returncode}")
        update_job(fail_args, ledger, "failed")
        return 75 if network_failure else returncode
    return 1


def parser() -> argparse.ArgumentParser:
    main = argparse.ArgumentParser(description=__doc__)
    main.add_argument("--root", type=Path, default=Path.cwd(), help="Project directory (defaults to current Git root)")
    commands = main.add_subparsers(dest="subcommand", required=True)

    checkpoint = commands.add_parser("checkpoint", help="Record local progress and Git state")
    checkpoint.add_argument("--note", required=True)
    checkpoint.add_argument("--next")
    checkpoint.set_defaults(handler=cmd_checkpoint)

    queue = commands.add_parser("queue", help="Record unfinished network-dependent work")
    queue.add_argument("--label", required=True)
    queue.add_argument("--kind", default="network")
    queue.add_argument("--resume")
    queue.add_argument("--idempotent", action="store_true", help="Mark this job safe to repeat")
    queue.set_defaults(handler=cmd_queue)

    for name, state in (("start", "running"), ("done", "done")):
        action = commands.add_parser(name, help=f"Mark a job {state}")
        action.add_argument("job_id")
        action.set_defaults(handler=lambda a, l, target=state: update_job(a, l, target))
    failed = commands.add_parser("fail", help="Mark a job failed")
    failed.add_argument("job_id")
    failed.add_argument("--error", required=True)
    failed.set_defaults(handler=lambda a, l: update_job(a, l, "failed"))

    status = commands.add_parser("status", help="Show the saved checkpoint and job counts")
    status.add_argument("--json", action="store_true")
    status.set_defaults(handler=cmd_status)

    resume = commands.add_parser("resume", help="List unfinished jobs and safe resume commands")
    resume.set_defaults(handler=cmd_resume)

    probe = commands.add_parser("probe", help="Run small bounded reachability checks")
    probe.add_argument("--url", action="append", default=[])
    probe.add_argument("--attempts", type=int, default=3, choices=range(1, 6))
    probe.add_argument("--timeout", type=float, default=4.0)
    probe.add_argument("--json", action="store_true")
    probe.set_defaults(handler=cmd_probe)

    run = commands.add_parser("run", help="Run and track one network-dependent command")
    run.add_argument("--label", required=True)
    run.add_argument("--kind", default="network-command")
    run.add_argument("--idempotent", action="store_true")
    run.add_argument("--retries", type=int, default=0, choices=range(0, 6))
    run.add_argument("command", nargs=argparse.REMAINDER)
    run.set_defaults(handler=cmd_run)
    return main


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = project_root(args.root)
    if args.subcommand == "probe" and not args.url:
        args.url = ["https://github.com"]
    return args.handler(args, Ledger(root))


if __name__ == "__main__":
    raise SystemExit(main())
