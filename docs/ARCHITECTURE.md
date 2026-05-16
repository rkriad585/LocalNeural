# Architecture

## Overview

LocalNeural follows a **client-server** architecture with a Python/Flask backend serving a jQuery/TailwindCSS frontend over HTTP and WebSocket (Socket.IO) connections.

```
Browser (jQuery + TailwindCSS)
    │
    ├── HTTP/HTTPS (Flask routes) ──────► Flask App (app.py)
    │                                       │
    └── WebSocket (Socket.IO) ──────────► SocketIO Handlers
                                            │
                                            ▼
                                    ┌─────────────────┐
                                    │   SQLite DB      │
                                    │  (.data/         │
                                    │   neural_mem.db) │
                                    └─────────────────┘
                                            │
                                            ▼
                                    ┌─────────────────┐
                                    │   AI Providers   │
                                    │  (utilities/     │
                                    │   providers.py)  │
                                    └─────────────────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    ▼                       ▼                       ▼
                Ollama                  OpenAI              Anthropic / Gemini
              (localhost)            (API Key)              (API Key)
```

## Components

### Frontend (`templates/` + `static/js/main.js`)

| File | Purpose |
|---|---|
| `base.html` | Root template, TailwindCDN, Socket.IO client, theme init |
| `index.html` | Main chat interface with sidebar, settings modal, search |
| `login.html` | Login/register forms, forgot-password flow |
| `settings.html` | Settings modal (provider, model, prompt, tools) |
| `settings_page.html` | Standalone `/settings` page |
| `profile.html` | User profile editing |
| `admin.html` | Admin panel (user list) |
| `admin_dashboard.html` | Full admin dashboard (users, global settings, tools) |
| `user_view.html` | Admin user detail view (profile, stats, sessions, actions) |
| `main.js` | All frontend logic (1488+ lines) |

### Backend (`app.py`)

| Module | Purpose |
|---|---|
| Flask routes | REST API endpoints for CRUD operations |
| SocketIO events | Real-time chat, streaming, regeneration |
| Session management | Login, logout, auth checks |
| Rate limiting | Flask-Limiter on auth and sensitive endpoints |
| CSRF protection | `X-Requested-With` header check on all POST/PUT/DELETE |

### Database (`database.py`)

~70 functions covering:
- Users (CRUD, auth, settings)
- Sessions (CRUD, branching, pin, archive, tags)
- Messages (CRUD, pin, tokens)
- Projects & documents (RAG knowledge bases)
- Prompts (library)
- Tools (CRUD, global/per-user)
- User settings (per-user key-value)
- Password reset tokens
- File embeddings

### AI Providers (`utilities/providers.py`)

An abstraction layer supporting:

| Provider | API Format | Auth |
|---|---|---|
| Ollama | HTTP REST | None (local) |
| OpenAI | OpenAI SDK-compatible | API key |
| Anthropic | Anthropic SDK-compatible | API key |
| Google Gemini | Google AI API | API key |
| OpenRouter | OpenAI-compatible | API key |
| Groq | OpenAI-compatible | API key |

### Configuration (`config.py`)

Centralized configuration via:
- Environment variables (loaded via `python-dotenv`)
- Default values in `Config` class
- Database-stored settings (admin-configurable)

## Data Flow: Chat Message

```
1. User types message → main.js creates SocketIO emit('send_message', data)
2. Flask handle_message() receives event
3. Checks auth, user not blocked, session validity
4. Saves user message to SQLite
5. Calls generate_response() which:
   a. Loads session context (history + system prompt)
   b. Resolves per-user provider config (with global fallback)
   c. Builds tool definitions (static + DB tools)
   d. Calls providers.chat_completion() with streaming
   e. Emits 'stream_chunk' events for each token
   f. Handles tool calls in a loop (max 5 rounds)
6. Saves final AI response to SQLite
7. Emits 'stream_done' event
```

## Permission Model

| Role | Access |
|---|---|
| Anonymous | Login/register only |
| User (role='user') | Own chats, own settings, profile |
| Admin (role='admin') | All users, all chats, global settings, tools |
| Blocked (blocked=1) | Cannot login, cannot send messages |
