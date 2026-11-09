# Roadmap

## Alpha: reliability core

- [x] Idempotent event ingestion and transactional outbox
- [x] Destination configuration and event filters
- [x] At-least-once delivery, retries, DLQ, and manual retry
- [x] SSRF validation and signed outbound requests
- [x] Unit tests and PostgreSQL migration verification in CI

## Before beta

- [x] User registration, JWT authentication, and initial owner membership
- [ ] Membership invitation, role management, and organization administration
- [ ] Cursor pagination and standardized API error schema
- [ ] Rate limits, audit log, OpenTelemetry, and Sentry
- [ ] PostgreSQL/Redis end-to-end test suite and load test baseline
- [ ] Backup/restore runbook and retention controls

## After beta validation

- [ ] Dashboard for events, executions, and DLQ
- [ ] Python SDK and integration examples
- [ ] Additional language SDKs and workflow orchestration features
