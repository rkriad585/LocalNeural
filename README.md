<div align="center">

<img src="static/images/logo.svg" alt="LocalNeural Logo" width="120" height="120" />

# LocalNeural

**The Ultimate Private AI Interface. Local. Fast. Beautiful. Multi-Provider.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-black.svg)](https://flask.palletsprojects.com/)
[![Socket.IO](https://img.shields.io/badge/Socket.IO-5.0+-white.svg)](https://socket.io/)

[Explore the Code](https://github.com/rkriad585/LocalNeural) · [Report Bug](https://github.com/rkriad585/LocalNeural/issues) · [Request Feature](https://github.com/rkriad585/LocalNeural)

</div>

---

## Overview

LocalNeural is a self-hosted, multi-provider AI chat interface with a stunning **"Nothing OS" inspired UI**. It supports **local models** via Ollama and **cloud providers** like OpenAI, Anthropic, Google Gemini, OpenRouter, and Groq — all behind a single, consistent interface.

Built with **privacy-first** principles: your data stays on your server. Features include real-time streaming, file RAG, multimodal vision, conversation branching, token tracking, admin controls, and more.

---

## Key Features

- **Multi-Provider AI** — Ollama (local), OpenAI, Anthropic, Google Gemini, OpenRouter, Groq
- **Real-Time Streaming** — Word-by-word responses via WebSockets (Socket.IO)
- **Dark/Light Theme** — CSS custom properties, persists across sessions
- **Session Branching** — Fork conversations into new branches
- **Token Tracking** — Per-session token counts displayed in history
- **Markdown Toggle** — Render messages as plain text or formatted markdown
- **Message Export** — Export individual messages as markdown
- **File RAG** — Upload PDFs, code files, markdown notes as project knowledge bases
- **Multimodal Vision** — Drag & drop or paste images for AI analysis (vision models)
- **Conversation Management** — Pin, archive, tag, search, and organize sessions
- **Prompt Library** — Save and inject system prompt templates
- **Prompt Variables** — `{date}`, `{time}`, `{datetime}`, `{user}` auto-substitution
- **Admin Controls** — User management, global settings, global tools, user blocking
- **User Settings** — Per-user provider, model, temperature, system prompt
- **Tools System** — Define custom function-calling tools (global and per-user)
- **Data Export** — Export chats as Markdown, JSON, or HTML/PDF
- **Account Management** — Profile editing, password change, self-deletion
- **Security Hardened** — CSRF protection, rate limiting, 72h sessions, password min 8

---

## Screenshots

> *Coming soon — see the live demo or run locally.*

---

## Quick Start

### Prerequisites
- Python 3.8+
- Ollama (for local models) — [Download](https://ollama.com)
- Pull a model: `ollama pull llama3`

### Install & Run
```bash
git clone https://github.com/rkriad585/LocalNeural.git
cd LocalNeural
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open **http://localhost:59869** in your browser.

> **Note:** Default port is `59869`. Set `LOCALNEURAL_PORT` env var to change it.

### Docker
```bash
docker build -t localneural .
docker run -p 59869:59869 localneural
```

Or use docker-compose:
```bash
docker-compose up
```

---

## Configuration

Copy `.env.example` to `.env` and configure:

```env
SECRET_KEY=your-strong-random-secret-key
LOCALNEURAL_HOST=0.0.0.0
LOCALNEURAL_PORT=59869

# Optional: SMTP for password reset emails
LOCALNEURAL_SMTP_HOST=smtp.gmail.com
LOCALNEURAL_SMTP_PORT=587
LOCALNEURAL_SMTP_USER=your@email.com
LOCALNEURAL_SMTP_PASSWORD=your-app-password
LOCALNEURAL_SMTP_FROM=your@email.com

# Optional: Auto-create super admin on first run
LOCALNEURAL_ADMIN_EMAIL=admin@example.com
LOCALNEURAL_ADMIN_PASSWORD=your-admin-password
```

All settings are documented in [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

---

## Documentation

| Document | Description |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | System architecture, design decisions, data flow |
| [API Reference](docs/API.md) | Full API endpoint documentation |
| [Setup Guide](docs/SETUP.md) | Detailed installation and configuration |
| [User Guide](docs/USER_GUIDE.md) | How to use all features |
| [Deployment](docs/DEPLOYMENT.md) | Docker, production deployment |
| [Configuration](docs/CONFIGURATION.md) | All environment variables and settings |
| [Features](docs/FEATURES.md) | Detailed feature documentation |
| [Security](docs/SECURITY.md) | Security model, CSRF, rate limiting |
| [Development](docs/DEVELOPMENT.md) | Contributing, code style, testing |

---

## Tech Stack

- **Backend:** Python, Flask, Flask-SocketIO, Flask-Limiter
- **Database:** SQLite (via `sqlite3`)
- **Frontend:** HTML5, TailwindCSS (CDN), jQuery, Socket.IO Client
- **AI Providers:** Ollama API, OpenAI API, Anthropic API, Google Gemini API, OpenRouter API, Groq API
- **Markdown:** marked.js, highlight.js
- **Auth:** Session-based with werkzeug password hashing
- **Deployment:** Docker, docker-compose

---

## Project Structure

```
LocalNeural/
├── app.py                 # Main Flask app (routes, auth, admin, tools, chat)
├── config.py              # Configuration class (env vars, defaults)
├── database.py            # SQLite database operations
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker build
├── docker-compose.yml     # Docker compose
├── .env.example           # Environment template
├── LICENSE                # MIT License
├── README.md
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── .data/
│   └── neural_memory.db   # SQLite database file
├── docs/                  # Documentation
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── CONFIGURATION.md
│   ├── DEPLOYMENT.md
│   ├── DEVELOPMENT.md
│   ├── FEATURES.md
│   ├── SECURITY.md
│   ├── SETUP.md
│   └── USER_GUIDE.md
├── static/
│   ├── css/
│   │   └── style.css
│   ├── images/
│   │   └── logo.svg
│   ├── js/
│   │   └── main.js
│   └── uploads/
│       └── profiles/
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── settings.html
│   ├── settings_page.html
│   ├── profile.html
│   ├── admin.html
│   ├── admin_dashboard.html
│   ├── user_view.html
│   └── reset_password.html
└── utilities/
    ├── chat_logic.py      # Session context, title generation
    ├── email.py            # SMTP email sending
    ├── embeddings.py       # Document embeddings
    ├── file_parser.py      # PDF/code file parsing
    ├── providers.py        # Multi-AI provider abstraction
    ├── tools.py            # Function calling tools
    └── web_search.py       # Web search tool
```

---

## License

Distributed under the **MIT License**. See `LICENSE` for more information.

---

<div align="center">

Made with ❤️ by [rkriad585](https://github.com/rkriad585)

</div>
