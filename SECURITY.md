# Security policy

## Supported versions

Only the latest version on the `main` branch is currently supported during the alpha period.

## Reporting a vulnerability

Do not open a public GitHub issue for a suspected vulnerability. Until a dedicated security contact is published, contact the repository maintainer privately through GitHub and include:

- a description of the issue and its impact;
- reproducible steps or a minimal proof of concept;
- affected version or commit; and
- any suggested mitigation, if available.

Please avoid accessing data that does not belong to you, interrupting service, or publishing proof-of-concept details before a fix is available.

## Deployment notes

Production deployments must use a unique `FLOWLEDGER_SECRETS_ENCRYPTION_KEY`, restrict worker egress, run PostgreSQL backups, and protect broker/database credentials. The development key in `.env.example` must never be used in production.
