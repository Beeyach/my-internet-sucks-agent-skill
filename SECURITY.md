# Security

## Report privately

Do not open a public issue for a vulnerability that could expose credentials, execute an unsafe saved command, corrupt a user's working tree, or cause a remote write to be repeated.

Use GitHub's private vulnerability reporting for this repository. If that option is unavailable, contact Bloomwired through https://bloomwired.io/contact and include only the minimum reproduction details needed.

## Local data

The helper writes `.agent-netmode/state.json` inside the active project. It stores checkpoint notes, Git metadata, job labels, redacted errors, and optional resume text. It does not upload the ledger.

Basic redaction covers common token and credential patterns. Redaction is a backstop, not a vault. Never place secrets, signed URLs, authentication headers, or private customer data in a saved command.

## Retry boundary

Only commands explicitly marked idempotent may be retried. Remote writes such as deployments, releases, pushes, publishing, payments, and database migrations must be verified before retrying.
