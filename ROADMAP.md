# Roadmap

## v0.1.0. Safe local state

- Agent Skill for Claude Code and Codex.
- Git-aware local checkpoints without automatic commits.
- Network job queue with explicit idempotency.
- Secret redaction for saved text.
- Bounded retries and a human-readable resume view.
- Cross-platform installer and automated tests.

## v0.2.0. Better failure recognition

- Redacted fixtures for Git, npm, pnpm, Yarn, pip, uv, Cargo, and common deployment CLIs.
- Structured error classification with confidence and source.
- Proxy, VPN, captive-portal, and DNS failure distinctions.
- More cache-aware command suggestions.

## v0.3.0. Agent hooks

- Optional pre-network checkpoints for supported agent hook systems.
- Post-command recording without storing secrets.
- Remote-state verification adapters for selected deployment platforms.
- A machine-readable resume protocol other agents can adopt.

## Later

- Additional coding-agent adapters.
- Local network quality history with opt-in collection only.
- Shared specification for interruption-safe agent work.

Roadmap items are proposals, not promises. Retry safety takes priority over feature count.
