# MARS API Reference

> **Foundation phase** — only the health endpoint is currently implemented.
> This document will be expanded as new endpoints are added.

## Base URL

```
http://localhost:8000
```

## Interactive Docs

FastAPI generates interactive Swagger UI and ReDoc automatically:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI schema**: http://localhost:8000/openapi.json

---

## Endpoints

### GET /health

Check that the MARS backend is running and reachable.

**Response 200**

```json
{
  "status": "ok",
  "app_name": "MARS",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": "2024-03-15T14:00:00Z"
}
```

---

## Planned Endpoints (not yet implemented)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/events` | Ingest a text or speech event |
| `GET`  | `/state` | Get the current world state |
| `GET`  | `/plans` | List recent plans |
| `GET`  | `/plans/{id}` | Get a specific plan |
| `GET`  | `/ledger` | List ledger entries |
| `GET`  | `/ledger/verify` | Verify ledger chain integrity |
| `WS`   | `/ws/events` | Real-time event stream (WebSocket) |
| `WS`   | `/ws/state` | Real-time world-state updates (WebSocket) |

---

## Error Responses

All errors follow this envelope:

```json
{
  "error": "ErrorTypeName",
  "detail": "Human-readable description",
  "request_id": "uuid",
  "timestamp": "ISO-8601 UTC"
}
```
