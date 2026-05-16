# Features

## AI Providers

LocalNeural supports six AI providers through a unified abstraction layer:

| Provider | Type | Models |
|---|---|---|
| **Ollama** | Local (self-hosted) | llama3, mixtral, codellama, tinyllama, llava (vision), etc. |
| **OpenAI** | Cloud (API key) | gpt-4o, gpt-4o-mini, gpt-4-turbo, o1, etc. |
| **Anthropic** | Cloud (API key) | claude-3-opus, claude-3-sonnet, claude-3-haiku |
| **Google Gemini** | Cloud (API key) | gemini-1.5-pro, gemini-1.5-flash |
| **OpenRouter** | Cloud (API key) | Unified access to 200+ models |
| **Groq** | Cloud (API key) | mixtral, llama3, gemma at high speed |

Each user can configure their own provider and API key in Settings, falling back to the global admin-configured defaults.

## Real-Time Streaming

Messages stream word-by-word via WebSockets (Socket.IO). Token-per-second speed is displayed in real-time during generation.

## Session Branching

Conversations can be forked at any message:
1. Click the fork button on any message
2. A new branch session is created
3. The branch tree panel shows parent-child relationships
4. Navigate between branches freely

## Token Tracking

Each session tracks total token usage across all messages. Token counts are:
- Displayed in the session history list
- Aggregated per user in the admin user detail page
- Updated in real-time during generation

## Markdown Rendering

Messages are rendered as Markdown by default. Toggle any message to plain text using the `</>` button in the message action bar.

Features:
- Syntax-highlighted code blocks (highlight.js)
- One-click code copy
- Tables, lists, headings
- Math formulas (via marked.js)

## Message Export

Export individual messages as Markdown files via the download button in the message action bar.

## Prompt Variables

System prompts support automatic variable substitution:

| Variable | Resolves To |
|---|---|
| `{date}` | Current date (e.g., "May 16, 2026") |
| `{time}` | Current time (e.g., "02:30 PM") |
| `{datetime}` | Combined date and time |
| `{user}` | User's username |

## File RAG (Projects)

Create projects and upload documents:
1. Click "+ New Project" in sidebar
2. Name your project
3. Upload PDFs, code files, or markdown notes
4. Chat inside the project — the AI reads your files as context

Supported file types: PDF, Python, JavaScript, TypeScript, Java, C++, Go, Rust, Markdown, plain text.

## Multimodal Vision

Drag & drop images or paste from clipboard. The AI analyzes them using vision-capable models (e.g., Ollama's `llava`, OpenAI's `gpt-4o`).

## Conversation Management

- **Pin** — Pin important sessions to the top of history
- **Archive** — Archive old sessions (toggle archived view)
- **Tag** — Add custom tags to sessions for organization
- **Groups** — Organize sessions into groups/categories
- **Search** — Ctrl+F to search within the current session
- **Rename** — Custom session titles

## Admin Dashboard

Available at `/admin_dashboard` for admin users:

- **User Management** — View all users, change roles, reset passwords, block, delete
- **User Detail View** — Click any user to see profile, stats, sessions, and admin actions
- **Global Provider** — Set default AI provider and model for all users
- **Global System Prompt** — Default system prompt for all users
- **Registration Toggle** — Enable/disable new user registration
- **Global Tools** — Add and manage function-calling tools available to all users

## Tools System

Define custom function-calling tools:

```json
{
  "name": "get_weather",
  "description": "Get current weather for a city",
  "parameters": {
    "type": "object",
    "properties": {
      "city": { "type": "string" }
    }
  }
}
```

Tools can be:
- **Global** (admin-managed, available to all users)
- **Personal** (user-managed, available only to them)

## Security Features

- **CSRF Protection** — Via `X-Requested-With` header + `SameSite=Lax` cookies
- **Rate Limiting** — Flask-Limiter on auth and sensitive endpoints
- **Password Policy** — Minimum 8 characters
- **Session Timeout** — 72 hours, no "Remember Me"
- **User Enumeration Prevention** — Generic "Invalid username or password" on login
- **Error Message Sanitization** — Internal errors never leak details to users
- **Account Blocking** — Admin can block users from logging in or sending messages
- **Password Hashing** — werkzeug `generate_password_hash` (scrypt-based)

## Themes

Switch between dark and light modes via the theme toggle button in the header. The choice persists via `localStorage`.

Customize:
- **Accent Color** — Pick any hex color in Settings
- **Font Size** — Adjust via slider in Settings
