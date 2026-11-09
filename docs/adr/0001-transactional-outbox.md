# ADR 0001: Transactional outbox for accepted events

## Status

Accepted.

## Context

An event persisted in PostgreSQL can be lost if a process fails between committing it and sending a separate message to Redis.

## Decision

Persist the event and its outbox message in one PostgreSQL transaction. A publisher claims pending outbox rows with `FOR UPDATE SKIP LOCKED`, sends the corresponding Celery task, and marks the row published only after broker acceptance.

## Consequences

Publishing can happen twice if the process fails after sending but before committing. Consumers must be idempotent. This is intentional and provides at-least-once delivery without a distributed transaction.
