# Configuration Reference

## Environment Variables

All configuration is managed through environment variables loaded from `.env`.

### Core

| Variable | Default | Required | Description |
|---|---|---|---|
| `SECRET_KEY` | — | **Yes** | Flask session signing key. Generate with `secrets.token_hex(32)` |
| `LOCALNEURAL_HOST` | `0.0.0.0` | No | Bind address |
| `LOCALNEURAL_PORT` | `59869` | No | HTTP server port |
| `FLASK_DEBUG` | `0` | No | Set to `1` for debug mode |

### Session

| Variable | Default | Description |
|---|---|---|
| *(hardcoded)* | 72 hours | Session lifetime (`PERMANENT_SESSION_LIFETIME`) |
| *(hardcoded)* | `Lax` | `SESSION_COOKIE_SAMESITE` |
| *(hardcoded)* | `True` | `SESSION_COOKIE_HTTPONLY` |

### SMTP (Email)

| Variable | Default | Description |
|---|---|---|
| `LOCALNEURAL_SMTP_HOST` | `smtp.gmail.com` | SMTP server hostname |
| `LOCALNEURAL_SMTP_PORT` | `587` | SMTP server port |
| `LOCALNEURAL_SMTP_USER` | `` | SMTP username (full email) |
| `LOCALNEURAL_SMTP_PASSWORD` | `` | SMTP app password |
| `LOCALNEURAL_SMTP_FROM` | `` | From email address |

### Admin Seeding

| Variable | Description |
|---|---|
| `LOCALNEURAL_ADMIN_EMAIL` | Auto-creates super admin on first run |
| `LOCALNEURAL_ADMIN_PASSWORD` | Password for the admin account |

## Application Defaults (config.py)

| Setting | Default | Description |
|---|---|---|
| `OLLAMA_API_URL` | `http://localhost:11434` | Ollama server URL |
| `DB_FILE` | `.data/neural_memory.db` | SQLite database path |
| `DEFAULT_MODEL` | `tinyllama` | Fallback model |
| `DEFAULT_TEMP` | `0.7` | Default temperature |
| `DEFAULT_SYSTEM` | *(built-in)* | Default system prompt |

## Database Settings

Admin-configurable settings stored in the `settings` table:

| Key | Type | Description |
|---|---|---|
| `system_prompt` | text | Global default system prompt |
| `allow_registration` | `"true"`/`"false"` | Whether new users can register |
| `global_provider` | string | Default AI provider (admin dashboard) |
| `global_model` | string | Default model (admin dashboard) |

## Per-User Settings

Each user can override (stored in `user_settings` table):

| Key | Description |
|---|---|
| `model` | User's preferred model |
| `provider` | User's preferred AI provider |
| `api_key` | User's API key for cloud providers |
| `system_prompt` | User's custom system prompt |
| `temperature` | User's preferred temperature |
| `ollama_url` | User's custom Ollama URL |

## CSRF Protection

All `POST`, `PUT`, `DELETE`, `PATCH` requests to `/api/` (except `/api/auth/`) require:
```
X-Requested-With: XMLHttpRequest
```

This is automatically set by jQuery AJAX requests.

## Rate Limiting

| Endpoint | Limit |
|---|---|
| `/api/auth/login` | 10 per minute |
| `/api/auth/register` | 5 per minute |
| `/api/auth/forgot-password` | 3 per minute |
| `/api/account/delete` | 2 per minute |
| General API | 120 per minute |
