# API Reference

Complete reference for the project REST API.

## Authentication

All requests require a Bearer token in the `Authorization` header.

```
Authorization: Bearer <token>
```

Tokens are issued via `POST /auth/token` with your client credentials.
Token lifetime is 3600 seconds. Refresh via `POST /auth/refresh`.

## Endpoints

The base URL is `https://api.example.com/v1`.

| Method | Path | Description |
|--------|------|-------------|
| GET | /items | List all items |
| POST | /items | Create an item |
| GET | /items/{id} | Get one item |
| PUT | /items/{id} | Replace an item |
| DELETE | /items/{id} | Remove an item |

## Data Models

### Item

```json
{
  "id": "string",
  "name": "string",
  "created_at": "ISO-8601 datetime",
  "tags": ["string"]
}
```

### Error

```json
{
  "code": "string",
  "message": "string"
}
```

## Rate Limiting

Requests are capped at 1000 per minute per token. Excess requests receive
`429 Too Many Requests`. The `Retry-After` header indicates when to retry.
