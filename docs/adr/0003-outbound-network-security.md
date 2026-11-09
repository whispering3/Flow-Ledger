# ADR 0003: Restrict outbound delivery networking

## Status

Accepted.

## Context

Customer-configured destinations can be abused to access internal services or cloud metadata endpoints.

## Decision

Before each delivery, resolve the hostname and reject addresses that are not globally routable. Allow only HTTP(S) ports `80` and `443`, disable redirects and environment proxies, and sign the exact transmitted body with a per-destination HMAC secret encrypted at rest.

## Consequences

The application check reduces SSRF risk but does not replace network egress policy; production deployments must restrict worker egress to public networks. Custom ports are not supported in the alpha release.
