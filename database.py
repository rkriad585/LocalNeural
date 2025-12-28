import sqlite3
import uuid
from datetime import datetime
from config import Config

def get_db():
    conn = sqlite3.connect(Config.DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Existing Tables
    c.execute('''CREATE TABLE IF NOT EXISTS sessions 
                 (id TEXT PRIMARY KEY, title TEXT, model TEXT, system_prompt TEXT, project_id TEXT, timestamp DATETIME)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT, images TEXT, timestamp DATETIME)''')
    c.execute('''CREATE TABLE IF NOT EXISTS prompts 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings 
                 (key TEXT PRIMARY KEY, value TEXT)''')
    
    # NEW: Project Tables
    c.execute('''CREATE TABLE IF NOT EXISTS projects 
                 (id TEXT PRIMARY KEY, title TEXT, description TEXT, created_at DATETIME)''')
    c.execute('''CREATE TABLE IF NOT EXISTS project_documents 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT, filename TEXT, content TEXT)''')

    # Migrations
    try: c.execute("ALTER TABLE messages ADD COLUMN images TEXT")
    except: pass
    try: c.execute("ALTER TABLE sessions ADD COLUMN model TEXT")
    except: pass
    try: c.execute("ALTER TABLE sessions ADD COLUMN system_prompt TEXT")
    except: pass
    try: c.execute("ALTER TABLE sessions ADD COLUMN project_id TEXT")
    except: pass
    
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ("system_prompt", Config.DEFAULT_SYSTEM))
    
    conn.commit()
    conn.close()

# --- PROJECTS (NEW) ---
def create_project(title, description):
    pid = str(uuid.uuid4())
    conn = get_db()
    conn.execute("INSERT INTO projects (id, title, description, created_at) VALUES (?, ?, ?, ?)", 
                 (pid, title, description, datetime.now()))
    conn.commit()
    conn.close()
    return pid

def get_projects():
    conn = get_db()
    cursor = conn.execute("SELECT * FROM projects ORDER BY created_at DESC")
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data

def add_project_document(project_id, filename, content):
    conn = get_db()
    conn.execute("INSERT INTO project_documents (project_id, filename, content) VALUES (?, ?, ?)", 
                 (project_id, filename, content))
    conn.commit()
    conn.close()

def get_project_documents(project_id):
    conn = get_db()
    cursor = conn.execute("SELECT filename, content FROM project_documents WHERE project_id = ?", (project_id,))
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data

def delete_project(pid):
    conn = get_db()
    conn.execute("DELETE FROM projects WHERE id = ?", (pid,))
    conn.execute("DELETE FROM project_documents WHERE project_id = ?", (pid,))
    # Also delete sessions associated? Optional. keeping them for now but unlinked.
    conn.commit()
    conn.close()

# --- REGENERATE HELPER ---
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

# --- SETTINGS ---
def get_system_prompt():
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key = 'system_prompt'").fetchone()
    conn.close()
    return row['value'] if row else Config.DEFAULT_SYSTEM

def set_system_prompt(prompt):
    conn = get_db()
    conn.execute("INSERT INTO settings (key, value) VALUES ('system_prompt', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (prompt,))
    conn.commit()
    conn.close()

# --- SESSIONS ---
def create_session(title, model, system_prompt=None, project_id=None):
    sid = str(uuid.uuid4())
    conn = get_db()
    conn.execute("INSERT INTO sessions (id, title, model, system_prompt, project_id, timestamp) VALUES (?, ?, ?, ?, ?, ?)", 
                 (sid, title, model, system_prompt, project_id, datetime.now()))
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

def get_history():
    conn = get_db()
    # Left join to get project title if exists
    cursor = conn.execute("""
        SELECT s.id, s.title, s.model, s.project_id, p.title as project_title 
        FROM sessions s 
        LEFT JOIN projects p ON s.project_id = p.id 
        ORDER BY s.timestamp DESC
    """)
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data

# --- MESSAGES ---
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

# --- PROMPTS ---
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
