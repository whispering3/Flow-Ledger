# FlowLedger

Reliable webhook delivery and execution monitoring for SaaS teams.

FlowLedger accepts an event, persists it transactionally with an outbox record, and returns `202 Accepted`. The delivery worker is intentionally separate from ingestion so a broker outage cannot make an accepted event disappear.

## Status

**Alpha / not production-ready.** The backend currently includes onboarding, JWT authentication, durable idempotent ingestion, transactional outbox publishing, destinations, at-least-once HTTP delivery, retries, DLQ, and execution history. It does not yet include a dashboard, production observability, audit logs, or full multi-tenant administration.

## Development

Requires Python 3.13+ and Docker.

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
docker compose up -d postgres redis
alembic upgrade head
python -m apps.cli.bootstrap --organization Acme --slug acme --project Billing
```

Start the API, worker, and scheduler in separate terminals:

```powershell
uvicorn apps.api.main:app --reload
celery -A apps.workers.celery_app.celery_app worker --loglevel=INFO
celery -A apps.workers.celery_app.celery_app beat --loglevel=INFO
```

The bootstrap command prints an API key once. Store it securely. Alternatively, create an account, organization, project, and initial API key through `POST /v1/auth/register`. The health check is available at `GET /health`, and interactive API documentation at `/docs`.

## Quick example

```powershell
$headers = @{ "X-API-Key" = "flk_replace_me" }
Invoke-RestMethod -Method Post -Uri http://localhost:8000/v1/events -Headers $headers -ContentType "application/json" -Body @'
{
  "event_type": "payment.approved",
  "idempotency_key": "payment-123",
  "payload": { "payment_id": "123", "amount": 199.90, "currency": "BRL" }
}
'@
```

## Reliability contract

- A `202` is returned only after the event and its outbox message commit in PostgreSQL.
- Delivery will be **at least once**. Consumers must deduplicate using the stable delivery ID that will accompany outbound requests.
- The outbox publisher and workers must tolerate duplicate broker messages.

## Open source

FlowLedger is licensed under the [Apache License 2.0](LICENSE). Read [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and the [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.
