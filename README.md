# nail-app-client

Telegram bot for **clients** (booking, favorites, “my bookings”) for Nail App.

This repository is **public by design**. Secrets must be provided via environment variables.

## Run locally

1) Create `.env`:

```bash
TELEGRAM_BOT_TOKEN=...
CLIENT_API_BASE_URL=http://localhost:8000
CLIENT_API_HMAC_SECRET=...
```

2) Install and run:

```bash
poetry install
poetry run python -m app
```

## Server API contract

This bot talks to the server (master/admin deployment) via HTTP API:

- `GET /client/masters`
- `GET /client/masters/{slug}`
- `GET /client/masters/{slug}/services`
- `GET /client/masters/{slug}/availability?service_id=...&days=...`
- `POST /client/bookings`
- `POST /client/bookings/{id}/cancel`
- `GET /client/clients/me/bookings`
- favorites: `/client/clients/me/favorites`

