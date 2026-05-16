# Setup Guide

## Prerequisites

- **Python 3.8+** — [Download](https://python.org)
- **Ollama** (for local models) — [Download](https://ollama.com)
- **Git** — [Download](https://git-scm.com)

## Step-by-Step

### 1. Clone the Repository

```bash
git clone https://github.com/rkriad585/LocalNeural.git
cd LocalNeural
```

### 2. Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
SECRET_KEY=your-very-long-random-secret-key-here
```

**Required**: `SECRET_KEY` — generate one with:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Pull an Ollama Model

```bash
ollama pull llama3
# Or smaller: ollama pull tinyllama
# Or vision: ollama pull llava
```

Make sure Ollama is running:
```bash
ollama serve
```

### 6. Run the App

```bash
python app.py
```

Open **http://localhost:59869** in your browser.

### 7. Create an Account

- Navigate to the login page
- Click "Register"
- Create your account

### 8. Configure AI Provider (Optional)

By default, the app uses Ollama (local). To use cloud providers:

1. Open Settings (gear icon)
2. Select a provider (OpenAI, Anthropic, etc.)
3. Enter your API key
4. Save

## Docker Setup

### Build and Run

```bash
docker build -t localneural .
docker run -p 59869:59869 \
  -e SECRET_KEY=your-secret-key \
  -v localneural-data:/app/.data \
  localneural
```

### Docker Compose

```bash
docker-compose up
```

This will build, expose port 59869, and persist the database.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | (required) | Flask session signing key |
| `LOCALNEURAL_HOST` | `0.0.0.0` | Bind address |
| `LOCALNEURAL_PORT` | `59869` | HTTP port |
| `LOCALNEURAL_SMTP_HOST` | `smtp.gmail.com` | SMTP server for emails |
| `LOCALNEURAL_SMTP_PORT` | `587` | SMTP port |
| `LOCALNEURAL_SMTP_USER` | `` | SMTP username |
| `LOCALNEURAL_SMTP_PASSWORD` | `` | SMTP password |
| `LOCALNEURAL_SMTP_FROM` | `` | From address |
| `LOCALNEURAL_ADMIN_EMAIL` | `` | Auto-create admin on first run |
| `LOCALNEURAL_ADMIN_PASSWORD` | `` | Admin password |

## Super Admin

To auto-create a super admin on first run:

```env
LOCALNEURAL_ADMIN_EMAIL=admin@example.com
LOCALNEURAL_ADMIN_PASSWORD=your-secure-password
```

If the admin email already exists, their role will be upgraded to admin.
