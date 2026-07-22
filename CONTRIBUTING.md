# Contributing

Thanks for helping people keep coding on unreliable connections.

## Good contributions

- Add real, redacted network failure messages as test fixtures.
- Improve safe resume behavior for a package manager or deployment tool.
- Add Windows, macOS, or Linux compatibility coverage.
- Make the skill instructions shorter or clearer without weakening a safety rule.
- Document a coding agent that supports the open Agent Skills format.

Do not submit real tokens, private URLs, customer names, full terminal histories, or unredacted project paths.

## Development

Python 3.10 or newer is enough. The project has no runtime dependencies.

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile skill/my-internet-sucks/scripts/netmode.py install.py
python3 install.py --target codex --scope project --project-root /tmp/netmode-demo --dry-run
```

## Pull requests

1. Open an issue for behavior changes that affect retry or remote-write safety.
2. Add or update a test for the changed behavior.
3. Keep the local helper dependency-free unless an issue has established a strong reason otherwise.
4. Do not make the tool automatically commit, push, deploy, publish, migrate, or clear caches.
5. Describe the connection failure or working condition your change addresses.

Small fixture and documentation pull requests do not need a prior issue.
