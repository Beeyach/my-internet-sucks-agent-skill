<p align="center">
  <img src="assets/bloomwired-logo.png" alt="Bloomwired" width="220">
</p>

# My Internet Sucks

**An interruption-safe Agent Skill for Claude Code and OpenAI Codex on slow, unstable, metered, or frequently disconnecting internet.**

`/my-internet-sucks` changes how a coding agent plans network-dependent work. It finishes local work first, checkpoints before network operations, retries only repeat-safe commands, and records a local resume trail when Wi-Fi drops.

It is built for developers using rural broadband, mobile hotspots, airplane Wi-Fi, metered connections, unstable VPNs, or any connection that makes AI coding sessions fragile.

## What changes

Once active, the agent:

- Separates local work from network-dependent work.
- Batches remote reads instead of repeating searches and downloads.
- Preserves package and documentation caches.
- Saves a private local checkpoint before network work.
- Retries bounded, idempotent operations such as downloads and read-only fetches.
- Refuses to blindly retry deploys, releases, pushes, migrations, and uncertain remote writes.
- Leaves one clear resume trail for the next session.

The bundled `netmode.py` helper is dependency-free and works on macOS, Linux, and Windows with Python 3.10 or newer.

## Thirty-second example

Claude Code:

```text
/my-internet-sucks
Finish the feature and deploy it when the connection is stable enough.
```

Codex:

```text
$my-internet-sucks Finish the feature and deploy it when the connection is stable enough.
```

The agent now records local progress before the deploy:

```text
Low-bandwidth mode active.

Local work: implementation, focused tests, production build
Network work: package metadata check, deployment
Risk: deployment must be verified before any retry
```

If the connection fails later, `netmode.py resume` returns something like:

```text
[39db06a1] failed | safe to retry | Fetch package metadata
  Resume: npm view example version
[a8216c2d] pending | VERIFY REMOTE STATE FIRST | Production deployment
```

## Install

Clone the repository, then run one installer command from its root.

```bash
python3 install.py --target claude
python3 install.py --target codex
```

On Windows, use `py -3` when `python3` is unavailable.

User-level locations:

| Agent | Installed location | Invocation |
|---|---|---|
| Claude Code | `~/.claude/skills/my-internet-sucks` | `/my-internet-sucks` |
| OpenAI Codex | `~/.agents/skills/my-internet-sucks` | `$my-internet-sucks` |

To install only inside the current repository:

```bash
python3 install.py --target claude --scope project
python3 install.py --target codex --scope project
```

Claude Code and Codex both use the open Agent Skills format. Their discovery folders differ, so this repository keeps one canonical skill and copies it to the correct location. See the [Claude Code skills documentation](https://code.claude.com/docs/en/skills) and [Codex skill documentation](https://learn.chatgpt.com/docs/build-skills).

## Use the local helper directly

The skill handles these commands automatically, but they are also useful by hand:

```bash
# Record local progress and the next network step
python3 skill/my-internet-sucks/scripts/netmode.py checkpoint \
  --note "Feature complete; focused tests pass" \
  --next "Install locked dependencies"

# Queue a repeat-safe network job
python3 skill/my-internet-sucks/scripts/netmode.py queue \
  --label "Install locked dependencies" \
  --kind package-download \
  --idempotent \
  --resume "npm ci --prefer-offline"

# Queue a remote write that must be checked before retrying
python3 skill/my-internet-sucks/scripts/netmode.py queue \
  --label "Verify production deployment" \
  --kind deploy

# Inspect unfinished work after reconnecting
python3 skill/my-internet-sucks/scripts/netmode.py resume
```

The ledger lives at `.agent-netmode/state.json` inside the project. The directory ignores itself in Git. Stored labels, errors, and resume text pass through basic secret redaction, but you should never put credentials in a saved command.

## What it does not do

This skill cannot keep Claude Code or Codex responding when the agent's own API connection is gone. It reduces preventable network work and stores enough local state for a later session to continue safely.

It also does not automatically commit changes, clear caches, retry uncertain remote writes, or claim a deployment succeeded without checking it.

## Why this exists

Poor connections break agentic coding differently from ordinary browsing. One task may require many model turns, tool calls, package downloads, documentation fetches, Git operations, and a deployment. A short drop can leave the user unsure which remote action completed and which local work was preserved.

This project treats network instability as a workflow constraint the agent should plan around, not a generic error message.

## Contribute

Good first contributions include:

- Network-error fixtures from Git, npm, pnpm, pip, Cargo, and deployment CLIs.
- Cache-aware command guidance for more package managers.
- Windows and PowerShell test cases.
- Accessibility and plain-language improvements.
- Safe adapters for additional coding agents that support Agent Skills.

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Security concerns belong in [SECURITY.md](SECURITY.md), not a public issue.

## Status

Early public release. The core checkpoint, queue, redaction, guarded retry, and resume flows are tested. See [ROADMAP.md](ROADMAP.md) for the next milestones.

## License

[MIT](LICENSE). Built by Bloomwired and open-source contributors.
