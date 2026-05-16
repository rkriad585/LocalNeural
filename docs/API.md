# API Reference

## Authentication

All POST/PUT/DELETE requests to `/api/` (except `/api/auth/`) require the header:
```
X-Requested-With: XMLHttpRequest
```

Session-based authentication using cookies (SameSite=Lax, HttpOnly).

### `POST /api/auth/register`
- Body: `{username, password, email?, full_name?}`
- Returns: `{status, user_id}` or error

### `POST /api/auth/login`
- Body: `{username, password}`
- Returns: `{status, user_id}` or error (generic "Invalid username or password")
- Rate limited: 10/min, blocked accounts return 403

### `POST /api/auth/logout`
- Returns: `{status}`

### `GET /api/auth/me`
- Returns: `{user_id, username, email, full_name, role, profile_pic}`

## Chat

### `emit('send_message', data)` (SocketIO)
- Data: `{prompt, model, session_id?, temperature?, options?, images?, system_prompt?, file_context?}`
- Streams response via `stream_chunk` events, finalizes with `stream_done`

### `emit('regenerate', data)` (SocketIO)
- Data: `{session_id, model, temperature?, options?}`

### `emit('stop_generation')` (SocketIO)
- Stops current stream

## Sessions

### `GET /api/history`
- Query: `?archived=1`
- Returns: Array of sessions with tags

### `GET /api/sessions/<sid>/messages`
- Returns: Array of messages

### `POST /api/session/<sid>/config`
- Body: `{system_prompt}`
- Sets per-chat system prompt

### `GET /api/sessions/<sid>/branches`
- Returns: Branch tree for session

### `POST /api/sessions/<sid>/fork`
- Body: `{message_id}`
- Forks conversation at given message

### `DELETE /api/sessions/<sid>`
- Deletes session

### `POST /api/pin/<sid>`
- Toggles pin on session

### `POST /api/archive/<sid>`
- Toggles archive on session

### `POST /api/rename/<sid>`
- Body: `{title}`
- Renames session

### `GET /api/session/<sid>/config`
- Returns: `{model, system_prompt}`

### `POST /api/session/<sid>/config`
- Body: `{system_prompt, model?, temperature?}`

## Messages

### `GET /api/messages/<msg_id>/export`
- Returns: Markdown file of single message

## Provider Config

### `GET /api/provider/config`
- Returns: `{provider, api_key, ollama_url}`
- Reads per-user first, falls back to global

### `POST /api/provider/config`
- Body: `{provider, api_key, ollama_url}`
- Saves per-user (if logged in) or global

### `GET /api/provider/models`
- Returns: Array of available models for current provider

## Models

### `GET /api/models`
- Returns: `{models: [{name}]}` for current provider

## User Settings

### `GET /api/user/settings`
- Returns: `{model, provider, api_key, system_prompt, temperature}`

### `POST /api/user/settings`
- Body: any of `{model, provider, api_key, system_prompt, temperature}`
- Stores per-user values

## Account Management

### `POST /api/account/delete`
- Body: `{password}`
- Permanently deletes account (requires password confirmation)

## Admin

### `GET /api/admin/users`
- Returns: Array of all users
- Admin only

### `DELETE /api/admin/users/<uid>`
- Deletes user and all data
- Admin only

### `PUT /api/admin/users/<uid>/role`
- Body: `{role: "user" | "admin"}`
- Admin only

### `GET /api/admin/user/<uid>`
- Returns: `{user, stats: {session_count, message_count, total_tokens}, sessions: [...]}`
- Admin only

### `POST /api/admin/user/<uid>/password`
- Body: `{password}`
- Admin resets user password (min 8 chars)

### `POST /api/admin/user/<uid>/block`
- Body: `{blocked: true | false}`
- Blocks/unblocks user account

### `GET /api/admin/settings`
- Returns: `{system_prompt, allow_registration}`

### `POST /api/admin/settings`
- Body: `{system_prompt?, allow_registration?, provider?, model?}`

## Tools

### `GET /api/tools`
- Returns: Array of tools (global + user's own)

### `POST /api/tools`
- Body: `{name, description, definition, is_global?}`
- Creates a tool

### `PUT /api/tools/<tool_id>`
- Body: `{name?, description?, definition?, enabled?}`

### `DELETE /api/tools/<tool_id>`

## Tags & Groups

### `GET /api/tags`
### `POST /api/tags`
### `DELETE /api/tags/<tag>`

### `GET /api/groups`
### `POST /api/groups`
### `PUT /api/groups/<gid>`
### `DELETE /api/groups/<gid>`

## Projects

### `GET /api/projects`
### `POST /api/projects`
### `PUT /api/projects/<pid>`
### `DELETE /api/projects/<pid>`

### `POST /api/projects/<pid>/documents`
- Upload document to project knowledge base

### `DELETE /api/projects/<pid>/documents/<doc_id>`

## Prompts

### `GET /api/prompts`
### `POST /api/prompts`
### `DELETE /api/prompts/<pid>`

## Export

### `GET /api/export/<session_id>?format=md|json|html`
- Exports entire session in requested format

### `GET /api/export/db`
- Downloads database backup

### `POST /api/import/db`
- Uploads database backup (admin only)
