# Design notes

## Goal

Make agentic coding less wasteful and ambiguous on unstable connections. Preserve local progress, reduce avoidable network work, and distinguish a safe retry from a remote action that must be checked first.

## Boundaries

The project cannot make a cloud model available without internet. It does not replace Git, a package-manager cache, or a deployment provider. It coordinates those tools and records a small local recovery state.

## State model

The local ledger has two parts:

1. A checkpoint containing a timestamp, note, next action, branch, commit, and changed-file list.
2. Network jobs with an explicit idempotency flag, state, attempt count, redacted resume text, and redacted last error.

Writes use a temporary file followed by an atomic replacement. A short-lived local lock prevents two helper processes from updating the ledger at the same time.

## Safety model

Idempotency is opt-in. A queued job is unsafe to repeat unless the caller marks it idempotent. The guarded runner ignores retry counts for non-idempotent commands.

This is deliberately conservative. A false “verify first” costs time. A false “safe to retry” can publish twice, run a migration twice, or hide an already-successful deployment behind a second failure.

## Privacy model

The ledger stays inside the project and its directory ignores itself in Git. Common credential patterns are redacted before text is saved. The tool does not collect analytics or call a telemetry service.

The safest rule remains: do not put credentials in a command that will be recorded.
