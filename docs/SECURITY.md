# Security Model

## Overview

LocalNeural is designed for self-hosted deployment where security is a priority but the threat model assumes the deployment environment is controlled by the user. The following security measures are implemented.

## Authentication

### Session Management
- Sessions are signed with `SECRET_KEY` (required env var)
- Session lifetime: 72 hours (hardcoded, no "Remember Me" option)
- Cookies: `SameSite=Lax`, `HttpOnly`
- Session is regenerated on login to prevent session fixation

### Password Security
- Minimum length: 8 characters
- Hashed using werkzeug's `generate_password_hash` (scrypt-based)
- Passwords are never logged or exposed in responses

### User Enumeration Prevention
- Login always returns: "Invalid username or password" (whether the user exists or not)
- Registration always succeeds (ignoring duplicate errors)
- Forgot-password returns 404 with generic "user_not_found" whether or not the email exists

## CSRF Protection

All `POST`, `PUT`, `DELETE`, `PATCH` requests to `/api/` (except `/api/auth/*`) require:

```
X-Requested-With: XMLHttpRequest
```

This header is automatically set by jQuery's AJAX methods. Browsers enforce same-origin policy, preventing cross-origin requests from setting this header.

## Rate Limiting

Flask-Limiter with in-memory storage:

| Route | Limit |
|---|---|
| `/api/auth/login` | 10/minute |
| `/api/auth/register` | 5/minute |
| `/api/auth/forgot-password` | 3/minute |
| `/api/account/delete` | 2/minute |
| Default (all `/api/`) | 120/minute |

Note: Rate limits reset on server restart (memory storage).

## Database

- SQLite file at `.data/neural_memory.db`
- File is excluded from git via `.gitignore`
- Database import endpoint requires admin authentication
- Import validates that the file is a valid SQLite database

## Admin Access

- Admin routes (`/admin`, `/admin_dashboard`, `/admin/user/<uid>`) check for admin role
- Admin API endpoints (`/api/admin/*`) call `require_admin()` which returns 401/403
- Super admin is seeded on first run via `.env` variables
- Admin role re-checked on every request (no caching)

## Error Handling

- Internal exceptions never expose `str(e)` details to users
- API errors return structured JSON: `{"error": "message"}`
- Generic error messages for auth failures
- 500 errors return generic "An internal error occurred"

## User Blocking

Admins can block users. Blocked users:
- Cannot log in (403 on login)
- Cannot send messages (error emitted via WebSocket)
- Their existing sessions remain but they cannot create new ones

## Input Validation

- Username: trimmed, server-validated
- Email: optional, not validated format
- Password: minimum 8 characters
- API keys: stored as-is in database
- All inputs: Flask request.json parsing

## Deployment Recommendations

For production deployment:

1. Use a strong `SECRET_KEY` (256-bit random)
2. Run behind a reverse proxy (Nginx) with HTTPS
3. Restrict network access to the server
4. Back up the database regularly
5. Use Docker with read-only root filesystem
6. Monitor access logs
7. Keep Python dependencies updated
