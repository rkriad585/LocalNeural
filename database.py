import sqlite3
import uuid
import os
import json
import numpy as np
from datetime import datetime, timedelta
from config import Config

def get_db():
    conn = sqlite3.connect(Config.DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(Config.DB_FILE), exist_ok=True)
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions 
                 (id TEXT PRIMARY KEY, title TEXT, model TEXT, system_prompt TEXT, project_id TEXT, timestamp DATETIME)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT, images TEXT, timestamp DATETIME)''')
    c.execute('''CREATE TABLE IF NOT EXISTS prompts 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings 
                 (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS projects 
                 (id TEXT PRIMARY KEY, title TEXT, description TEXT, created_at DATETIME)''')
    c.execute('''CREATE TABLE IF NOT EXISTS project_documents 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, filename TEXT, content TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS doc_embeddings 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, document_id INTEGER, chunk_index INTEGER, embedding BLOB)''')

    c.execute('''CREATE TABLE IF NOT EXISTS groups 
                 (id TEXT PRIMARY KEY, title TEXT, sort_order INTEGER DEFAULT 0)''')

    c.execute('''CREATE TABLE IF NOT EXISTS session_tags 
                 (session_id TEXT, tag TEXT, PRIMARY KEY (session_id, tag))''')

    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id TEXT PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT, email TEXT, full_name TEXT, profile_pic TEXT, created_at DATETIME)''')

    for col in ['images', 'model', 'system_prompt', 'project_id', 'archived', 'pinned', 'group_id', 'user_id']:
        try: c.execute(f"ALTER TABLE sessions ADD COLUMN {col} TEXT")
        except: pass
    try: c.execute("ALTER TABLE sessions ADD COLUMN total_tokens INTEGER DEFAULT 0")
    except: pass
    try: c.execute("ALTER TABLE sessions ADD COLUMN forked_from TEXT")
    except: pass
    try: c.execute("ALTER TABLE messages ADD COLUMN images TEXT")
    except: pass
    try: c.execute("ALTER TABLE messages ADD COLUMN pinned INTEGER DEFAULT 0")
    except: pass
    for col in ['email', 'full_name', 'profile_pic', 'role']:
        try: c.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
        except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN blocked INTEGER DEFAULT 0")
    except: pass

    for col in ['user_id']:
        try: c.execute(f"ALTER TABLE projects ADD COLUMN {col} TEXT")
        except: pass

    c.execute('''CREATE TABLE IF NOT EXISTS tools 
                 (id TEXT PRIMARY KEY, name TEXT UNIQUE, description TEXT, definition TEXT, is_global INTEGER DEFAULT 1, user_id TEXT, created_at DATETIME)''')
    try: c.execute("ALTER TABLE tools ADD COLUMN enabled INTEGER DEFAULT 1")
    except: pass

    c.execute('''CREATE TABLE IF NOT EXISTS user_settings 
                 (user_id TEXT, key TEXT, value TEXT, PRIMARY KEY (user_id, key))''')

    c.execute('''CREATE TABLE IF NOT EXISTS password_reset_tokens
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, token TEXT UNIQUE, expires_at DATETIME, used INTEGER DEFAULT 0)''')

    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ("system_prompt", Config.DEFAULT_SYSTEM))
    conn.commit()
    conn.close()


def create_project(title, description, user_id=None):
    pid = str(uuid.uuid4())
    conn = get_db()
    conn.execute("INSERT INTO projects (id, title, description, created_at) VALUES (?, ?, ?, ?)", 
                 (pid, title, description, datetime.now()))
    if user_id:
        try: conn.execute("UPDATE projects SET user_id = ? WHERE id = ?", (user_id, pid))
        except: pass
    conn.commit()
    conn.close()
    return pid

def get_projects(user_id=None):
    conn = get_db()
    if user_id:
        cursor = conn.execute("SELECT * FROM projects WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    else:
        cursor = conn.execute("SELECT * FROM projects ORDER BY created_at DESC")
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data

def add_project_document(project_id, filename, content):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO project_documents (project_id, filename, content) VALUES (?, ?, ?)", 
                   (project_id, filename, content))
    conn.commit()
    doc_id = cursor.lastrowid
    conn.close()
    return doc_id

def get_project_documents(project_id):
    conn = get_db()
    cursor = conn.execute("SELECT id, filename, content FROM project_documents WHERE project_id = ?", (project_id,))
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data

def delete_project_document(doc_id):
    conn = get_db()
    conn.execute("DELETE FROM project_documents WHERE id = ?", (doc_id,))
    conn.execute("DELETE FROM doc_embeddings WHERE document_id = ?", (doc_id,))
    conn.commit()
    conn.close()

def save_doc_embeddings(document_id, chunks, vectors):
    conn = get_db()
    for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
        conn.execute("INSERT INTO doc_embeddings (document_id, chunk_index, embedding) VALUES (?, ?, ?)",
                     (document_id, i, json.dumps(vec)))
    conn.commit()
    conn.close()

def get_relevant_docs(project_id, query_vector, top_k=3):
    conn = get_db()
    rows = conn.execute("""
        SELECT d.id, d.filename, d.content, e.chunk_index, e.embedding
        FROM doc_embeddings e
        JOIN project_documents d ON e.document_id = d.id
        WHERE d.project_id = ?
    """, (project_id,)).fetchall()

    scored = []
    query_np = np.array(query_vector)
    for row in rows:
        vec = json.loads(row['embedding'])
        sim = float(np.dot(query_np, vec) / (np.linalg.norm(query_np) * np.linalg.norm(vec) + 1e-10))
        scored.append((sim, row['filename'], row['content']))

    scored.sort(key=lambda x: -x[0])
    conn.close()
    return scored[:top_k]

def delete_project(pid):
    conn = get_db()
    conn.execute("DELETE FROM doc_embeddings WHERE document_id IN (SELECT id FROM project_documents WHERE project_id = ?)", (pid,))
    conn.execute("DELETE FROM sessions WHERE project_id = ?", (pid,))
    conn.execute("DELETE FROM projects WHERE id = ?", (pid,))
    conn.execute("DELETE FROM project_documents WHERE project_id = ?", (pid,))
    conn.commit()
    conn.close()


def verify_session_owner(session_id, user_id):
    conn = get_db()
    row = conn.execute("SELECT user_id FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    return row and row['user_id'] == user_id

def verify_project_owner(project_id, user_id):
    conn = get_db()
    row = conn.execute("SELECT user_id FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    return row and row['user_id'] == user_id

def delete_last_ai_message(sid):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, role FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT 1", (sid,))
    row = cursor.fetchone()
    if row and row['role'] == 'assistant':
        cursor.execute("DELETE FROM messages WHERE id = ?", (row['id'],))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False


def get_system_prompt(user_id=None):
    if user_id:
        val = get_user_setting(user_id, 'system_prompt')
        if val:
            return val
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key = 'system_prompt'").fetchone()
    conn.close()
    return row['value'] if row else Config.DEFAULT_SYSTEM

def set_system_prompt(prompt, user_id=None):
    if user_id:
        set_user_setting(user_id, 'system_prompt', prompt)
        return
    conn = get_db()
    conn.execute("INSERT INTO settings (key, value) VALUES ('system_prompt', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (prompt,))
    conn.commit()
    conn.close()


def create_session(title, model, system_prompt=None, project_id=None, user_id=None):
    sid = str(uuid.uuid4())
    conn = get_db()
    conn.execute("INSERT INTO sessions (id, title, model, system_prompt, project_id, timestamp) VALUES (?, ?, ?, ?, ?, ?)", 
                 (sid, title, model, system_prompt, project_id, datetime.now()))
    if user_id:
        try: conn.execute("UPDATE sessions SET user_id = ? WHERE id = ?", (user_id, sid))
        except: pass
    conn.commit()
    conn.close()
    return sid

def update_session_model(sid, model):
    conn = get_db()
    conn.execute("UPDATE sessions SET model = ? WHERE id = ?", (model, sid))
    conn.commit()
    conn.close()

def update_session_system_prompt(sid, prompt):
    conn = get_db()
    conn.execute("UPDATE sessions SET system_prompt = ? WHERE id = ?", (prompt, sid))
    conn.commit()
    conn.close()

def get_session_info(sid):
    conn = get_db()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (sid,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_session_system_prompt(sid):
    conn = get_db()
    row = conn.execute("SELECT system_prompt FROM sessions WHERE id = ?", (sid,)).fetchone()
    conn.close()
    return row['system_prompt'] if row and row['system_prompt'] else None

def rename_session(sid, title):
    conn = get_db()
    conn.execute("UPDATE sessions SET title = ? WHERE id = ?", (title, sid))
    conn.commit()
    conn.close()

def delete_session(sid):
    conn = get_db()
    conn.execute("DELETE FROM sessions WHERE id = ?", (sid,))
    conn.execute("DELETE FROM messages WHERE session_id = ?", (sid,))
    conn.commit()
    conn.close()

def archive_session(sid, archived=True):
    conn = get_db()
    conn.execute("UPDATE sessions SET archived = ? WHERE id = ?", (1 if archived else None, sid))
    conn.commit()
    conn.close()

def get_history(user_id=None, include_archived=False):
    conn = get_db()
    conditions = []
    params = []
    if not include_archived:
        conditions.append("s.archived IS NULL")
    if user_id:
        conditions.append("s.user_id = ?")
        params.append(user_id)
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    cursor = conn.execute(f"""
        SELECT s.id, s.title, s.model, s.project_id, s.archived, s.pinned, s.group_id,
               p.title as project_title, s.total_tokens 
        FROM sessions s 
        LEFT JOIN projects p ON s.project_id = p.id 
        {where}
        ORDER BY CASE WHEN s.pinned = '1' THEN 0 ELSE 1 END, s.timestamp DESC
    """, params)
    data = [dict(row) for row in cursor.fetchall()]

    # Attach tags per session
    ids = [row['id'] for row in data]
    if ids:
        placeholders = ','.join('?' for _ in ids)
        tag_rows = conn.execute(f"""
            SELECT session_id, tag FROM session_tags WHERE session_id IN ({placeholders}) ORDER BY tag
        """, ids).fetchall()
        tag_map = {}
        for tr in tag_rows:
            tag_map.setdefault(tr['session_id'], []).append(tr['tag'])
        for row in data:
            row['tags'] = tag_map.get(row['id'], [])
    conn.close()
    return data

def pin_session(sid, pinned=True):
    conn = get_db()
    conn.execute("UPDATE sessions SET pinned = ? WHERE id = ?", ('1' if pinned else None, sid))
    conn.commit()
    conn.close()

def bulk_delete_sessions(ids):
    conn = get_db()
    placeholders = ','.join('?' for _ in ids)
    conn.execute(f"DELETE FROM messages WHERE session_id IN ({placeholders})", ids)
    conn.execute(f"DELETE FROM sessions WHERE id IN ({placeholders})", ids)
    conn.commit()
    conn.close()

def create_group(title):
    gid = str(uuid.uuid4())
    conn = get_db()
    conn.execute("INSERT INTO groups (id, title) VALUES (?, ?)", (gid, title))
    conn.commit()
    conn.close()
    return gid

def get_groups():
    conn = get_db()
    cursor = conn.execute("SELECT * FROM groups ORDER BY sort_order ASC")
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data

def delete_group(gid):
    conn = get_db()
    conn.execute("UPDATE sessions SET group_id = NULL WHERE group_id = ?", (gid,))
    conn.execute("DELETE FROM groups WHERE id = ?", (gid,))
    conn.commit()
    conn.close()

def set_session_group(sid, gid):
    conn = get_db()
    conn.execute("UPDATE sessions SET group_id = ? WHERE id = ?", (gid, sid))
    conn.commit()
    conn.close()

def get_db_size():
    try:
        return os.path.getsize(Config.DB_FILE)
    except:
        return 0

def get_stats(user_id=None):
    conn = get_db()
    session_filter = " WHERE user_id = ?" if user_id else ""
    sess_params = (user_id,) if user_id else ()
    total_sessions = conn.execute(f"SELECT COUNT(*) as c FROM sessions{session_filter}", sess_params).fetchone()['c']
    total_messages = conn.execute(f"""
        SELECT COUNT(*) as c FROM messages m
        JOIN sessions s ON m.session_id = s.id
        {session_filter.replace('user_id', 's.user_id')}
    """, sess_params).fetchone()['c']
    active_sessions = conn.execute(f"SELECT COUNT(*) as c FROM sessions WHERE archived IS NULL{session_filter.replace('WHERE', 'AND') if session_filter else ''}", sess_params).fetchone()['c']
    model_counts = conn.execute(f"""
        SELECT model, COUNT(*) as c FROM sessions 
        WHERE model IS NOT NULL AND model != ''{session_filter.replace('WHERE', 'AND') if session_filter else ''} 
        GROUP BY model ORDER BY c DESC
    """, sess_params).fetchall()
    sessions_per_day = conn.execute(f"""
        SELECT DATE(timestamp) as day, COUNT(*) as c FROM sessions 
        WHERE timestamp IS NOT NULL{session_filter.replace('WHERE', 'AND') if session_filter else ''} 
        GROUP BY day ORDER BY day DESC LIMIT 30
    """, sess_params).fetchall()
    messages_per_day = conn.execute(f"""
        SELECT DATE(m.timestamp) as day, COUNT(*) as c FROM messages m
        JOIN sessions s ON m.session_id = s.id
        WHERE m.timestamp IS NOT NULL{session_filter.replace('WHERE', 'AND').replace('user_id', 's.user_id') if session_filter else ''} 
        GROUP BY day ORDER BY day DESC LIMIT 30
    """, sess_params).fetchall()
    total_est_tokens = conn.execute(f"""
        SELECT SUM(LENGTH(m.content)) / 4 as t FROM messages m
        JOIN sessions s ON m.session_id = s.id
        {session_filter.replace('user_id', 's.user_id')}
    """, sess_params).fetchone()['t'] or 0
    conn.close()
    return {
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "active_sessions": active_sessions,
        "archived_sessions": total_sessions - active_sessions,
        "total_est_tokens": int(total_est_tokens),
        "model_counts": [dict(r) for r in model_counts],
        "sessions_per_day": [dict(r) for r in sessions_per_day],
        "messages_per_day": [dict(r) for r in messages_per_day],
    }

def search_messages(query, user_id=None, model=None, project_id=None, date_from=None, date_to=None):
    conn = get_db()
    like = f"%{query}%"
    conditions = ["m.content LIKE ?", "s.archived IS NULL"]
    params = [like]
    if user_id:
        conditions.append("s.user_id = ?")
        params.append(user_id)
    if model:
        conditions.append("s.model = ?")
        params.append(model)
    if project_id:
        conditions.append("s.project_id = ?")
        params.append(project_id)
    if date_from:
        conditions.append("m.timestamp >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("m.timestamp <= ?")
        params.append(date_to)
    where = " AND ".join(conditions)
    cursor = conn.execute(f"""
        SELECT m.id, m.session_id, m.role, m.content, m.timestamp,
               s.title as session_title, s.model
        FROM messages m
        JOIN sessions s ON m.session_id = s.id
        WHERE {where}
        ORDER BY m.timestamp DESC LIMIT 50
    """, params)
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data


def save_message(session_id, role, content, images=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (session_id, role, content, images, timestamp) VALUES (?, ?, ?, ?, ?)",
                 (session_id, role, content, images, datetime.now()))
    conn.commit()
    last_id = cursor.lastrowid 
    conn.close()
    return last_id 

def update_message(msg_id, new_content):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT session_id, id FROM messages WHERE id = ?", (msg_id,))
    row = cursor.fetchone()
    if row:
        session_id = row['session_id']
        current_id = row['id']
        cursor.execute("UPDATE messages SET content = ? WHERE id = ?", (new_content, msg_id))
        cursor.execute("DELETE FROM messages WHERE session_id = ? AND id > ?", (session_id, current_id))
        conn.commit()
        conn.close()
        return session_id
    conn.close()
    return None

def get_messages(session_id):
    conn = get_db()
    cursor = conn.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data

def toggle_pin_message(msg_id):
    conn = get_db()
    cursor = conn.execute("SELECT pinned FROM messages WHERE id = ?", (msg_id,))
    row = cursor.fetchone()
    if row:
        new_val = 0 if row['pinned'] else 1
        conn.execute("UPDATE messages SET pinned = ? WHERE id = ?", (new_val, msg_id))
        conn.commit()
        conn.close()
        return new_val
    conn.close()
    return None

def fork_session(session_id, up_to_msg_id):
    conn = get_db()
    src = get_session_info(session_id)
    if not src:
        conn.close()
        return None
    new_id = str(uuid.uuid4())
    conn.execute("""INSERT INTO sessions (id, title, model, system_prompt, project_id, timestamp, forked_from)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                 (new_id, src['title'] + " (fork)", src['model'], src['system_prompt'], src['project_id'], datetime.now(), session_id))
    cursor = conn.execute("SELECT * FROM messages WHERE session_id = ? AND id <= ? ORDER BY id ASC", (session_id, up_to_msg_id))
    msgs = [dict(row) for row in cursor.fetchall()]
    for m in msgs:
        conn.execute("INSERT INTO messages (session_id, role, content, images, timestamp) VALUES (?, ?, ?, ?, ?)",
                     (new_id, m['role'], m['content'], m['images'], m['timestamp']))
    conn.commit()
    conn.close()
    return new_id


def get_prompts():
    conn = get_db()
    cursor = conn.execute("SELECT * FROM prompts ORDER BY id DESC")
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data

def add_prompt(title, content):
    conn = get_db()
    conn.execute("INSERT INTO prompts (title, content) VALUES (?, ?)", (title, content))
    conn.commit()
    conn.close()

def delete_prompt(pid):
    conn = get_db()
    conn.execute("DELETE FROM prompts WHERE id = ?", (pid,))
    conn.commit()
    conn.close()


# --- USERS ---
def create_user(username, password_hash, email=None, full_name=None, role='user'):
    import uuid
    uid = str(uuid.uuid4())
    conn = get_db()
    conn.execute("INSERT INTO users (id, username, password_hash, email, full_name, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (uid, username, password_hash, email, full_name, role, datetime.now()))
    conn.commit()
    conn.close()
    return uid

def get_user_by_username(username):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_email(email):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(uid):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    conn.close()
    return dict(row) if row else None

def update_user(uid, username=None, email=None, full_name=None):
    conn = get_db()
    if username is not None:
        conn.execute("UPDATE users SET username = ? WHERE id = ?", (username, uid))
    if email is not None:
        conn.execute("UPDATE users SET email = ? WHERE id = ?", (email, uid))
    if full_name is not None:
        conn.execute("UPDATE users SET full_name = ? WHERE id = ?", (full_name, uid))
    conn.commit()
    conn.close()

def update_user_password(uid, password_hash):
    conn = get_db()
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, uid))
    conn.commit()
    conn.close()

def update_profile_pic(uid, pic_path):
    conn = get_db()
    conn.execute("UPDATE users SET profile_pic = ? WHERE id = ?", (pic_path, uid))
    conn.commit()
    conn.close()


# --- TAGS ---
def add_session_tag(session_id, tag):
    tag = tag.strip().lower().replace(' ', '-')
    if not tag:
        return
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO session_tags (session_id, tag) VALUES (?, ?)", (session_id, tag))
    conn.commit()
    conn.close()

def remove_session_tag(session_id, tag):
    tag = tag.strip().lower().replace(' ', '-')
    conn = get_db()
    conn.execute("DELETE FROM session_tags WHERE session_id = ? AND tag = ?", (session_id, tag))
    conn.commit()
    conn.close()

def get_session_tags(session_id):
    conn = get_db()
    rows = conn.execute("SELECT tag FROM session_tags WHERE session_id = ? ORDER BY tag", (session_id,)).fetchall()
    conn.close()
    return [row['tag'] for row in rows]

def get_all_tags(user_id=None):
    conn = get_db()
    if user_id:
        rows = conn.execute("""
            SELECT DISTINCT t.tag FROM session_tags t
            JOIN sessions s ON t.session_id = s.id
            WHERE s.user_id = ?
            ORDER BY t.tag
        """, (user_id,)).fetchall()
    else:
        rows = conn.execute("SELECT DISTINCT tag FROM session_tags ORDER BY tag").fetchall()
    conn.close()
    return [row['tag'] for row in rows]

def get_sessions_by_tag(tag, user_id=None):
    tag = tag.strip().lower().replace(' ', '-')
    conn = get_db()
    params = [tag]
    user_clause = ""
    if user_id:
        user_clause = " AND s.user_id = ?"
        params.append(user_id)
    rows = conn.execute(f"""
        SELECT s.id, s.title, s.model, s.project_id, s.archived, s.pinned,
               p.title as project_title
        FROM sessions s
        JOIN session_tags t ON s.id = t.session_id
        LEFT JOIN projects p ON s.project_id = p.id
        WHERE t.tag = ? AND s.archived IS NULL{user_clause}
        ORDER BY s.timestamp DESC
    """, params).fetchall()
    data = [dict(row) for row in rows]
    conn.close()
    return data


# --- PASSWORD RESET TOKENS ---
def create_password_reset_token(user_id):
    token = str(uuid.uuid4())
    expires_at = datetime.now() + timedelta(hours=1)
    conn = get_db()
    conn.execute("INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
                 (user_id, token, expires_at))
    conn.commit()
    conn.close()
    return token

def get_password_reset_token(token):
    conn = get_db()
    row = conn.execute("SELECT * FROM password_reset_tokens WHERE token = ? AND used = 0 AND expires_at > ?",
                       (token, datetime.now())).fetchone()
    conn.close()
    return dict(row) if row else None

def mark_password_reset_token_used(token):
    conn = get_db()
    conn.execute("UPDATE password_reset_tokens SET used = 1 WHERE token = ?", (token,))
    conn.commit()
    conn.close()

def update_session_tokens(session_id, tokens):
    conn = get_db()
    conn.execute("UPDATE sessions SET total_tokens = ? WHERE id = ?", (tokens, session_id))
    conn.commit()
    conn.close()

def get_provider_config(user_id=None):
    if user_id:
        u_provider = get_user_setting(user_id, 'provider')
        u_api_key = get_user_setting(user_id, 'api_key')
        u_ollama_url = get_user_setting(user_id, 'ollama_url')
        if u_provider or u_api_key or u_ollama_url:
            return {
                "provider": u_provider or 'ollama',
                "api_key": u_api_key or '',
                "ollama_url": u_ollama_url or 'http://localhost:11434',
            }
    conn = get_db()
    provider = conn.execute("SELECT value FROM settings WHERE key = 'provider'").fetchone()
    api_key = conn.execute("SELECT value FROM settings WHERE key = 'provider_api_key'").fetchone()
    ollama_url = conn.execute("SELECT value FROM settings WHERE key = 'ollama_url'").fetchone()
    conn.close()
    return {
        "provider": provider['value'] if provider else 'ollama',
        "api_key": api_key['value'] if api_key else '',
        "ollama_url": ollama_url['value'] if ollama_url else 'http://localhost:11434',
    }

def set_provider_config(provider, api_key='', ollama_url='', user_id=None):
    if user_id:
        set_user_setting(user_id, 'provider', provider)
        set_user_setting(user_id, 'api_key', api_key)
        if ollama_url:
            set_user_setting(user_id, 'ollama_url', ollama_url)
        return
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("provider", provider))
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("provider_api_key", api_key))
    if ollama_url:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("ollama_url", ollama_url))
    conn.commit()
    conn.close()

def get_setting(key, default=''):
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row['value'] if row else default

def set_setting(key, value):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_session_branch_info(session_id):
    conn = get_db()
    branches = []
    current = conn.execute("SELECT id, title, forked_from FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not current:
        conn.close()
        return []
    branches.append({"id": current['id'], "title": current['title'], "depth": 0})
    children = conn.execute("SELECT id, title, forked_from FROM sessions WHERE forked_from = ?", (session_id,)).fetchall()
    for child in children:
        branches.append({"id": child['id'], "title": child['title'], "depth": 1, "parent_id": session_id})
    if current['forked_from']:
        parent = conn.execute("SELECT id, title FROM sessions WHERE id = ?", (current['forked_from'],)).fetchone()
        if parent:
            branches.insert(0, {"id": parent['id'], "title": parent['title'], "depth": -1})
    conn.close()
    return branches


# --- TOOLS ---
def get_all_tools(global_only=False, user_id=None):
    conn = get_db()
    if global_only:
        rows = conn.execute("SELECT * FROM tools WHERE is_global = 1 AND enabled = 1 ORDER BY name").fetchall()
    elif user_id:
        rows = conn.execute("SELECT * FROM tools WHERE (is_global = 1 OR user_id = ?) AND enabled = 1 ORDER BY name", (user_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM tools ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_tool(tool_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_tool_by_name(name):
    conn = get_db()
    row = conn.execute("SELECT * FROM tools WHERE name = ?", (name,)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_tool(name, description, definition, is_global=1, user_id=None):
    import uuid
    tid = str(uuid.uuid4())
    conn = get_db()
    conn.execute("INSERT INTO tools (id, name, description, definition, is_global, user_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (tid, name, description, definition, is_global, user_id, datetime.now()))
    conn.commit()
    conn.close()
    return tid

def update_tool(tool_id, name=None, description=None, definition=None, enabled=None):
    conn = get_db()
    if name is not None:
        conn.execute("UPDATE tools SET name = ? WHERE id = ?", (name, tool_id))
    if description is not None:
        conn.execute("UPDATE tools SET description = ? WHERE id = ?", (description, tool_id))
    if definition is not None:
        conn.execute("UPDATE tools SET definition = ? WHERE id = ?", (definition, tool_id))
    if enabled is not None:
        conn.execute("UPDATE tools SET enabled = ? WHERE id = ?", (1 if enabled else 0, tool_id))
    conn.commit()
    conn.close()

def delete_tool(tool_id):
    conn = get_db()
    conn.execute("DELETE FROM tools WHERE id = ?", (tool_id,))
    conn.commit()
    conn.close()


# --- USER SETTINGS ---
def get_user_setting(user_id, key, default=''):
    conn = get_db()
    row = conn.execute("SELECT value FROM user_settings WHERE user_id = ? AND key = ?", (user_id, key)).fetchone()
    conn.close()
    return row['value'] if row else default

def set_user_setting(user_id, key, value):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO user_settings (user_id, key, value) VALUES (?, ?, ?)", (user_id, key, value))
    conn.commit()
    conn.close()

def delete_user(user_id):
    conn = get_db()
    conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM messages WHERE session_id IN (SELECT id FROM sessions WHERE user_id = ?)", (user_id,))
    conn.execute("DELETE FROM session_tags WHERE session_id IN (SELECT id FROM sessions WHERE user_id = ?)", (user_id,))
    conn.execute("DELETE FROM user_settings WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_db()
    rows = conn.execute("SELECT id, username, email, full_name, role, created_at FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_sessions(uid):
    conn = get_db()
    rows = conn.execute("""
        SELECT s.id, s.title, s.model, s.timestamp, s.total_tokens,
               (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.id) as msg_count
        FROM sessions s WHERE s.user_id = ? ORDER BY s.timestamp DESC
    """, (uid,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_message_count(uid):
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) as cnt FROM messages m JOIN sessions s ON m.session_id = s.id WHERE s.user_id = ?", (uid,)).fetchone()
    conn.close()
    return row['cnt'] if row else 0

def get_user_total_tokens(uid):
    conn = get_db()
    row = conn.execute("SELECT COALESCE(SUM(total_tokens), 0) as total FROM sessions WHERE user_id = ?", (uid,)).fetchone()
    conn.close()
    return row['total'] if row else 0

def is_user_blocked(uid):
    conn = get_db()
    row = conn.execute("SELECT blocked FROM users WHERE id = ?", (uid,)).fetchone()
    conn.close()
    return bool(row and row['blocked'])

def set_user_blocked(uid, blocked=True):
    conn = get_db()
    conn.execute("UPDATE users SET blocked = ? WHERE id = ?", (1 if blocked else 0, uid))
    conn.commit()
    conn.close()
