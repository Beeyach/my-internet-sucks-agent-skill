#!/usr/bin/env python3
"""Install the canonical skill for Claude Code, Codex, or both."""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
import shutil
import sys

SKILL_NAME = "my-internet-sucks"
SOURCE = Path(__file__).resolve().parent / "skill" / SKILL_NAME


def destinations(targets: list[str], scope: str, project_root: Path) -> list[tuple[str, Path]]:
    roots = {
        "claude": project_root / ".claude" / "skills" if scope == "project" else Path.home() / ".claude" / "skills",
        "codex": project_root / ".agents" / "skills" if scope == "project" else Path.home() / ".agents" / "skills",
    }
    return [(target, roots[target] / SKILL_NAME) for target in targets]


def install(destination: Path, force: bool, dry_run: bool) -> Path | None:
    backup = None
    if destination.exists():
        if not force:
            raise FileExistsError(f"{destination} already exists. Re-run with --force to replace it with a backup.")
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = destination.with_name(f"{destination.name}.backup-{stamp}")
        if backup.exists():
            raise FileExistsError(f"Backup path already exists: {backup}")
    if dry_run:
        return backup
    destination.parent.mkdir(parents=True, exist_ok=True)
    if backup:
        destination.replace(backup)
    try:
        shutil.copytree(SOURCE, destination)
    except Exception:
        if backup and backup.exists() and not destination.exists():
            backup.replace(destination)
        raise
    return backup


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--target", action="append", choices=("claude", "codex"), required=True)
    command.add_argument("--scope", choices=("user", "project"), default="user")
    command.add_argument("--project-root", type=Path, default=Path.cwd())
    command.add_argument("--force", action="store_true", help="Replace an existing install after creating a backup")
    command.add_argument("--dry-run", action="store_true")
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if not (SOURCE / "SKILL.md").is_file():
        print(f"Missing canonical skill: {SOURCE}", file=sys.stderr)
        return 2
    unique_targets = list(dict.fromkeys(args.target))
    for target, destination in destinations(unique_targets, args.scope, args.project_root.resolve()):
        try:
            backup = install(destination, args.force, args.dry_run)
        except (OSError, FileExistsError) as exc:
            print(f"{target}: {exc}", file=sys.stderr)
            return 1
        verb = "Would install" if args.dry_run else "Installed"
        print(f"{target}: {verb} {destination}")
        if backup:
            print(f"{target}: Existing skill backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
