# Contributing to FlowLedger

Thanks for helping improve FlowLedger. This project is in an alpha stage, so please open an issue before starting large changes or new integrations.

## Local setup

Follow the development instructions in the README, apply migrations, then run the quality checks:

```powershell
python -m ruff check .
python -m pytest
```

## Pull requests

- Keep each pull request focused on one change.
- Add or update tests for behavioral changes.
- Do not include credentials, payloads containing real customer data, or generated local files.
- Preserve the reliability contract: accepted events are durable, delivery is at-least-once, and consumers must tolerate duplicates.
- Document schema changes with an Alembic migration and update the README when user-facing behavior changes.

## Commit messages

Use short, imperative summaries, such as `Add delivery retry scheduler` or `Fix outbox lock handling`.

## Reporting vulnerabilities

Please follow [SECURITY.md](SECURITY.md) rather than opening a public issue for security-sensitive reports.
