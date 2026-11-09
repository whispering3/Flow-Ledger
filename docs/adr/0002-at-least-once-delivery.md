# ADR 0002: At-least-once outbound delivery

## Status

Accepted.

## Context

An HTTP endpoint may process a request while its response is lost. Exactly-once delivery cannot be guaranteed across an external HTTP boundary.

## Decision

Each execution receives a stable `delivery_id`. Every attempt sends it in `X-FlowLedger-Delivery-Id`; retries and manual reprocessing keep the same ID. FlowLedger records each attempt rather than overwriting prior outcomes.

## Consequences

Destinations must deduplicate by delivery ID. FlowLedger documents and tests at-least-once semantics rather than making an unfulfillable exactly-once promise.
