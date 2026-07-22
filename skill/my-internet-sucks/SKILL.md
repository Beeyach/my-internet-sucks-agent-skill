---
name: my-internet-sucks
description: Make Claude Code or Codex work safely on slow, unstable, metered, or frequently disconnecting internet. Use when the user mentions bad Wi-Fi, weak internet, packet loss, mobile hotspots, airplane Wi-Fi, failed downloads, repeated network timeouts, interrupted deployments, or needing work to resume after connectivity returns.
---

# My Internet Sucks

Switch the current task to a low-bandwidth, interruption-safe workflow. Keep useful local work moving, minimize network round trips, and leave a durable resume trail before risky network operations.

## Start the mode

1. Say `Low-bandwidth mode active.`
2. Identify the project root, current Git state, and the task's remaining network dependencies.
3. Classify remaining work:
   - **Local:** edits, local inspection, cached documentation, focused tests, builds with installed dependencies.
   - **Safe to retry:** read-only fetches, package downloads, remote status checks, and other idempotent operations.
   - **Verify before retry:** deploys, releases, publishing, pushes, writes to remote services, migrations, and commands with uncertain side effects.
4. Run local work first. Batch necessary network reads instead of repeating searches or downloads.
5. Before the first network-dependent action, record a checkpoint with the bundled helper.

Resolve this skill's directory from the loaded `SKILL.md`, then run:

```bash
python3 <skill-dir>/scripts/netmode.py checkpoint --note "<what is complete>" --next "<next network action>"
```

On Windows, use `py -3` when `python3` is unavailable.

## Work rules

- Do not clear package, build, browser, or documentation caches to troubleshoot unless corruption is proven.
- Prefer existing lockfiles and installed dependencies. Avoid unnecessary upgrades.
- Run focused tests before broad suites. Save heavy remote checks for the end.
- Never create a Git commit merely because this mode is active. Preserve the user's Git workflow.
- Never store passwords, tokens, API keys, signed URLs, or commands containing secrets in the resume ledger.
- Keep retries bounded. Use short exponential backoff only for idempotent operations.
- When a side-effectful command loses its connection after starting, check remote state before retrying it.
- If a network step fails, record it and continue any useful local work that remains.

Queue unfinished work:

```bash
python3 <skill-dir>/scripts/netmode.py queue \
  --label "Install locked dependencies" \
  --kind package-download \
  --idempotent \
  --resume "npm ci --prefer-offline"
```

For an operation that may have succeeded remotely, mark it non-idempotent:

```bash
python3 <skill-dir>/scripts/netmode.py queue \
  --label "Verify deployment before retrying" \
  --kind deploy
```

Use the helper's guarded runner only when repeating the command is safe:

```bash
python3 <skill-dir>/scripts/netmode.py run \
  --label "Fetch package metadata" \
  --idempotent --retries 2 -- npm view <package> version
```

## Recover after a failure

1. Run `status` to inspect the checkpoint and pending jobs.
2. For each non-idempotent or uncertain job, verify the remote result before any retry.
3. Resume safe jobs from the ledger.
4. Mark each job complete after verification.

```bash
python3 <skill-dir>/scripts/netmode.py status
python3 <skill-dir>/scripts/netmode.py resume
python3 <skill-dir>/scripts/netmode.py done <job-id>
```

End a disrupted turn with four short fields:

```text
Saved: <local work and checks>
Blocked: <network-dependent step>
Verify first: <remote state to inspect, or none>
Resume: <one exact safe command or ledger command>
```

## Limit

This skill cannot keep a cloud coding agent responding when the agent's own API connection is down. It reduces wasted work and records enough local state for a later session to continue safely.
