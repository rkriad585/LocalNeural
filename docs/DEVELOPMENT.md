# Development Guide

## Setting Up for Development

```bash
git clone https://github.com/rkriad585/LocalNeural.git
cd LocalNeural
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with:
```env
SECRET_KEY=dev-secret-key-change-in-production
FLASK_DEBUG=1
```

## Codebase Tour

### Entry Points

| File | Purpose |
|---|---|
| `app.py` | Flask app, routes, SocketIO events, main entry |
| `database.py` | All SQLite operations (~70 functions) |
| `config.py` | Configuration class (env vars + defaults) |

### Templates (`templates/`)

Jinja2 templates extending `base.html`:

- `index.html` — Main chat interface (heavy JS)
- `login.html` — Auth forms
- `settings.html` — Settings modal (included in index.html)
- `settings_page.html` — Standalone `/settings` page
- `profile.html` — Profile editing
- `admin.html` — Admin panel
- `admin_dashboard.html` — Full admin dashboard
- `user_view.html` — Admin user detail view

### Frontend (`static/js/main.js`)

Single-file JavaScript (~1488 lines) containing:

- Socket.IO event handlers
- jQuery AJAX calls for all API endpoints
- DOM manipulation for the chat interface
- Theme toggling, search, branch tree
- Settings and provider configuration

### Utilities (`utilities/`)

| File | Purpose |
|---|---|
| `providers.py` | AI provider abstraction (Ollama, OpenAI, etc.) |
| `tools.py` | Static tool definitions + execution |
| `chat_logic.py` | Session context, title generation |
| `email.py` | SMTP email sending |
| `embeddings.py` | Document embeddings for search |
| `file_parser.py` | PDF and code file parsing |
| `web_search.py` | Web search tool |

## Common Development Tasks

### Adding a New Route

```python
@app.route('/api/my/endpoint')
def my_endpoint():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    # ... logic ...
    return jsonify({"result": data})
```

### Adding a Database Function

```python
def my_function(param):
    conn = get_db()
    rows = conn.execute("SELECT * FROM table WHERE col = ?", (param,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

### Adding a New Provider

1. Add provider class in `utilities/providers.py`
2. Add to the provider switch in `chat_completion()` and `get_available_models()`
3. Add to the provider select dropdown in templates
4. Test with a valid API key

### Adding a New Template

1. Create the `.html` file in `templates/`
2. Extend `base.html`:
   ```jinja
   {% extends "base.html" %}
   {% block content %}
   ... your HTML ...
   {% endblock %}
   ```
3. Add the route in `app.py`
4. Add JavaScript in a `<script>` block at the end

## Database Migrations

The app uses a migration-by-ALTER-TABLE pattern:

```python
# In init_db():
for col in ['new_column']:
    try: c.execute(f"ALTER TABLE mytable ADD COLUMN {col} TEXT")
    except: pass  # Column already exists
```

This is safe for production — ALTER TABLE ADD COLUMN is a no-op if the column exists.

## Testing

Currently there are no automated tests. Manual testing:

1. Start the app: `python app.py`
2. Open browser to `http://localhost:59869`
3. Test your changes

Before committing, verify:
- `python -m py_compile app.py` — no syntax errors
- `python -m py_compile database.py` — no syntax errors
- App starts without errors
- No console errors in browser

## Code Style

- **Python**: PEP 8, 4-space indentation
- **JavaScript**: jQuery conventions, camelCase, 4-space indentation
- **HTML**: 4-space indentation, TailwindCSS classes
- **No extra comments**: Code should be self-documenting
- **No print statements** in production code paths (use sparingly)

## Git Workflow

```bash
# Create a feature branch
git checkout -b feature/my-feature

# Make changes, then
git add .
git commit -m "Description of changes"

# Push and create PR
git push origin feature/my-feature
```

PRs should target the `main` branch.
