import sqlite3
import uuid
import os
import json
import numpy as np
from datetime import datetime
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

    for col in ['images', 'model', 'system_prompt', 'project_id', 'archived', 'pinned', 'group_id']:
        try: c.execute(f"ALTER TABLE sessions ADD COLUMN {col} TEXT")
        except: pass
    try: c.execute("ALTER TABLE messages ADD COLUMN images TEXT")
    except: pass

    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ("system_prompt", Config.DEFAULT_SYSTEM))
    conn.commit()
    conn.close()


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

def archive_session(sid, archived=True):
    conn = get_db()
    conn.execute("UPDATE sessions SET archived = ? WHERE id = ?", (1 if archived else None, sid))
    conn.commit()
    conn.close()

def get_history(include_archived=False):
    conn = get_db()
    where = "" if include_archived else " WHERE s.archived IS NULL "
    cursor = conn.execute(f"""
        SELECT s.id, s.title, s.model, s.project_id, s.archived, s.pinned, s.group_id,
               p.title as project_title 
        FROM sessions s 
        LEFT JOIN projects p ON s.project_id = p.id 
        {where}
        ORDER BY CASE WHEN s.pinned = '1' THEN 0 ELSE 1 END, s.timestamp DESC
    """)
    data = [dict(row) for row in cursor.fetchall()]
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

def search_messages(query):
    conn = get_db()
    like = f"%{query}%"
    cursor = conn.execute("""
        SELECT m.id, m.session_id, m.role, m.content, m.timestamp,
               s.title as session_title
        FROM messages m
        JOIN sessions s ON m.session_id = s.id
        WHERE m.content LIKE ? AND s.archived IS NULL
        ORDER BY m.timestamp DESC LIMIT 50
    """, (like,))
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

def fork_session(session_id, up_to_msg_id):
    conn = get_db()
    src = get_session_info(session_id)
    if not src:
        conn.close()
        return None
    new_id = str(uuid.uuid4())
    conn.execute("""INSERT INTO sessions (id, title, model, system_prompt, project_id, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                 (new_id, src['title'] + " (fork)", src['model'], src['system_prompt'], src['project_id'], datetime.now()))
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
