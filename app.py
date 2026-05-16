import json
import os
import base64
import requests
import threading
import time
import shutil
import io
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, Response, send_file, session, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
import database as db
import utilities.chat_logic as utils
import utilities.file_parser as file_parser
import utilities.embeddings as embed_utils
import utilities.tools as tool_utils
import utilities.email as email_utils
import utilities.providers as providers

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY
app.permanent_session_lifetime = Config.PERMANENT_SESSION_LIFETIME
socketio = SocketIO(app, cors_allowed_origins=[], async_mode='threading', max_http_buffer_size=10*1024*1024)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# --- Seed super admin on startup ---
_admin_seeded = False
@app.before_request
def _seed_admin():
    global _admin_seeded
    if _admin_seeded:
        return
    _admin_seeded = True
    admin_email = os.environ.get('LOCALNEURAL_ADMIN_EMAIL', '')
    admin_pass = os.environ.get('LOCALNEURAL_ADMIN_PASSWORD', '')
    if not admin_email or not admin_pass:
        return
    existing = db.get_user_by_email(admin_email)
    if existing:
        if (existing.get('role') or 'user') != 'admin':
            conn = db.get_db()
            conn.execute("UPDATE users SET role = 'admin' WHERE email = ?", (admin_email,))
            conn.commit()
            conn.close()
            print(f"Promoted user '{existing['username']}' to admin via .env config")
        return
    from werkzeug.security import generate_password_hash
    uid = db.create_user('admin', generate_password_hash(admin_pass), email=admin_email, full_name='Super Admin', role='admin')
    print(f"Super admin user created (id={uid})")


@app.route('/favicon.ico')
def favicon():
    return redirect(url_for('static', filename='images/logo.svg'))

db.init_db()
active_streams = {}


@app.before_request
def check_auth():
    if request.endpoint and request.endpoint not in ('static', 'favicon') and not request.path.startswith('/api/auth/') and request.path != '/login' and not request.path.startswith('/reset-password/'):
        if 'user_id' not in session and request.path != '/':
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for('login_page'))
        if 'user_id' not in session and request.path == '/':
            return redirect(url_for('login_page'))

@app.before_request
def csrf_check():
    if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
        if request.path.startswith('/api/') and not request.path.startswith('/api/auth/'):
            if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
                return jsonify({"error": "CSRF validation failed"}), 403


# --- AUTH ---
@app.route('/login', methods=['GET'])
def login_page():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/api/auth/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    username = request.json.get('username', '').strip()
    password = request.json.get('password', '').strip()
    cpassword = request.json.get('cpassword', '').strip()
    email = request.json.get('email', '').strip()
    full_name = request.json.get('full_name', '').strip()
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    if password != cpassword:
        return jsonify({"error": "Passwords do not match"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
    if email and '@' not in email:
        return jsonify({"error": "Invalid email address"}), 400
    existing_u = db.get_user_by_username(username)
    if existing_u:
        return jsonify({"error": "Username or email already registered"}), 409
    if email:
        existing_e = db.get_user_by_email(email)
        if existing_e:
            return jsonify({"error": "Username or email already registered"}), 409
    user_id = db.create_user(username, generate_password_hash(password), email=email or None, full_name=full_name or None)
    session.permanent = True
    session['user_id'] = user_id
    session['username'] = username
    return jsonify({"status": "success", "user_id": user_id})

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    username = request.json.get('username', '').strip()
    password = request.json.get('password', '').strip()
    user = db.get_user_by_username(username)
    if not user:
        user = db.get_user_by_email(username)
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({"error": "Invalid username or password"}), 401
    session_data = dict(session)
    session.clear()
    for k, v in session_data.items():
        session[k] = v
    session.permanent = True
    session['user_id'] = user['id']
    session['username'] = user['username']
    return jsonify({"status": "success", "user_id": user['id']})

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"status": "success"})

@app.route('/api/auth/me')
def auth_me():
    if 'user_id' in session:
        user = db.get_user_by_id(session['user_id'])
        if user:
            return jsonify({
                "user_id": user['id'],
                "username": user['username'],
                "email": user.get('email') or '',
                "full_name": user.get('full_name') or '',
                "profile_pic": user.get('profile_pic') or '',
                "role": user.get('role', 'user'),
                "created_at": user.get('created_at') or ''
            })
        return jsonify({"user_id": session['user_id'], "username": session.get('username')})
    return jsonify({"user_id": None}), 401


@app.route('/api/auth/forgot-password', methods=['POST'])
@limiter.limit("3 per minute")
def forgot_password():
    email = request.json.get('email', '').strip()
    if not email or '@' not in email:
        return jsonify({"error": "Valid email required"}), 400
    user = db.get_user_by_email(email)
    if not user:
        return jsonify({"error": "user_not_found"}), 404
    token = db.create_password_reset_token(user['id'])
    reset_url = url_for('reset_password_page', token=token, _external=True)
    sent = email_utils.send_reset_email(email, reset_url)
    if sent:
        return jsonify({"status": "success", "message": "Reset link sent to your email"})
    return jsonify({"error": "Failed to send email. SMTP not configured."}), 500


@app.route('/api/auth/reset-password', methods=['POST'])
@limiter.limit("5 per minute")
def reset_password():
    token = request.json.get('token', '').strip()
    password = request.json.get('password', '').strip()
    cpassword = request.json.get('cpassword', '').strip()
    if not token or not password or not cpassword:
        return jsonify({"error": "All fields required"}), 400
    if password != cpassword:
        return jsonify({"error": "Passwords do not match"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
    row = db.get_password_reset_token(token)
    if not row:
        return jsonify({"error": "Invalid or expired reset token"}), 400
    db.update_user_password(row['user_id'], generate_password_hash(password))
    db.mark_password_reset_token_used(token)
    return jsonify({"status": "success", "message": "Password reset successfully"})


@app.route('/reset-password/<token>')
def reset_password_page(token):
    row = db.get_password_reset_token(token)
    if not row:
        return render_template('reset_password.html', token=token, expired=True)
    return render_template('reset_password.html', token=token, expired=False)


# --- SETTINGS PAGE ---
@app.route('/settings')
def settings_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('settings_page.html')


# --- ADMIN PAGE ---
@app.route('/admin')
def admin_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    user = db.get_user_by_id(session['user_id'])
    if not user or (user.get('role') or 'user') != 'admin':
        return redirect(url_for('home'))
    return render_template('admin.html')


# --- PROFILE ---
UPLOAD_DIR = os.path.join(app.static_folder, 'uploads', 'profiles')
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route('/profile')
def profile_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('profile.html')

@app.route('/api/profile', methods=['GET'])
def get_profile():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user = db.get_user_by_id(session['user_id'])
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        "id": user['id'],
        "username": user['username'],
        "email": user.get('email') or '',
        "full_name": user.get('full_name') or '',
        "profile_pic": user.get('profile_pic') or '',
        "created_at": user.get('created_at') or ''
    })

@app.route('/api/profile', methods=['PUT'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user = db.get_user_by_id(session['user_id'])
    username = request.json.get('username', '').strip()
    email = request.json.get('email', '').strip()
    full_name = request.json.get('full_name', '').strip()
    if username and username != user['username']:
        existing = db.get_user_by_username(username)
        if existing:
            return jsonify({"error": "Username or email already registered"}), 409
        db.update_user(session['user_id'], username=username)
        session['username'] = username
    if email and email != (user.get('email') or ''):
        existing = db.get_user_by_email(email)
        if existing and existing['id'] != session['user_id']:
            return jsonify({"error": "Username or email already registered"}), 409
        if '@' not in email:
            return jsonify({"error": "Invalid email"}), 400
        db.update_user(session['user_id'], email=email)
    if full_name is not None:
        db.update_user(session['user_id'], full_name=full_name or None)
    return jsonify({"status": "success"})

@app.route('/api/profile/pic', methods=['POST'])
def upload_profile_pic():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    if 'pic' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files['pic']
    if f.filename == '':
        return jsonify({"error": "Empty filename"}), 400
    if not f.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
        return jsonify({"error": "Unsupported image format"}), 400
    ext = f.filename.rsplit('.', 1)[1].lower()
    filename = f"user_{session['user_id']}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    f.save(filepath)
    pic_url = url_for('static', filename=f'uploads/profiles/{filename}')
    db.update_profile_pic(session['user_id'], pic_url)
    return jsonify({"status": "success", "profile_pic": pic_url})

@app.route('/api/profile/password', methods=['POST'])
@limiter.limit("5 per minute")
def change_password():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user = db.get_user_by_id(session['user_id'])
    current = request.json.get('current_password', '')
    newpass = request.json.get('new_password', '')
    cnewpass = request.json.get('confirm_new_password', '')
    if not check_password_hash(user['password_hash'], current):
        return jsonify({"error": "Current password is incorrect"}), 400
    if newpass != cnewpass:
        return jsonify({"error": "New passwords do not match"}), 400
    if len(newpass) < 8:
        return jsonify({"error": "New password must be at least 8 characters"}), 400
    db.update_user_password(session['user_id'], generate_password_hash(newpass))
    return jsonify({"status": "success"})

@app.route('/api/account/delete', methods=['POST'])
@limiter.limit("2 per minute")
def delete_account():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user = db.get_user_by_id(session['user_id'])
    password = request.json.get('password', '')
    if not check_password_hash(user['password_hash'], password):
        return jsonify({"error": "Password incorrect"}), 400
    db.delete_user(session['user_id'])
    session.clear()
    return jsonify({"status": "success"})

_generation_start_time = {}
_token_count = {}


@app.route('/')
def home(): return render_template('index.html')


# --- PROJECTS ---
@app.route('/api/projects', methods=['GET'])
def get_projects(): return jsonify(db.get_projects(user_id=session.get('user_id')))

@app.route('/api/projects', methods=['POST'])
def create_project():
    try:
        title = request.form.get('title')
        desc = request.form.get('description')
        project_id = db.create_project(title, desc, user_id=session.get('user_id'))
        if 'files' in request.files:
            for f in request.files.getlist('files'):
                if f.filename != '':
                    content = file_parser.extract_text_from_file(f)
                    if content and content.strip():
                        doc_id = db.add_project_document(project_id, f.filename, content)
                        # Generate embeddings in background
                        threading.Thread(target=index_document_embeddings, args=(doc_id, content), daemon=True).start()
        return jsonify({"status": "success", "id": project_id})
    except Exception as e:
        return jsonify({"status": "error", "message": "Project creation failed"}), 500

@app.route('/api/projects/<pid>', methods=['DELETE'])
def delete_project(pid):
    if not db.verify_project_owner(pid, session.get('user_id')):
        return jsonify({"error": "Forbidden"}), 403
    db.delete_project(pid)
    return jsonify({"status": "success"})

@app.route('/api/projects/<pid>/documents', methods=['GET'])
def get_documents(pid):
    docs = db.get_project_documents(pid)
    return jsonify([{"id": d['id'], "filename": d['filename'], "size": len(d['content'])} for d in docs])

@app.route('/api/documents/<did>', methods=['DELETE'])
def delete_document(did):
    db.delete_project_document(did)
    return jsonify({"status": "success"})


# --- CONFIG ---
@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify({"system_prompt": db.get_system_prompt(), "templates": Config.PROMPT_TEMPLATES})

@app.route('/api/config', methods=['POST'])
def set_config():
    db.set_system_prompt(request.json['system_prompt'])
    return jsonify({"status": "success"})

@app.route('/api/session/<sid>/config', methods=['POST'])
def set_session_config(sid):
    db.update_session_system_prompt(sid, request.json['system_prompt'])
    return jsonify({"status": "success"})


@app.route('/api/user/settings', methods=['GET'])
def get_user_settings():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    uid = session['user_id']
    return jsonify({
        "model": db.get_user_setting(uid, 'model', ''),
        "provider": db.get_user_setting(uid, 'provider', ''),
        "api_key": db.get_user_setting(uid, 'api_key', ''),
        "system_prompt": db.get_user_setting(uid, 'system_prompt', ''),
        "temperature": db.get_user_setting(uid, 'temperature', ''),
    })

@app.route('/api/user/settings', methods=['POST'])
def set_user_settings_route():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    uid = session['user_id']
    data = request.json
    for key in ('model', 'provider', 'api_key', 'system_prompt', 'temperature'):
        if key in data:
            db.set_user_setting(uid, key, str(data[key]))
    return jsonify({"status": "success"})


# --- TOOLS API ---
@app.route('/api/tools', methods=['GET'])
def list_tools():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    tools = db.get_all_tools(user_id=session['user_id'])
    return jsonify(tools)

@app.route('/api/tools', methods=['POST'])
def create_tool_route():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    name = data.get('name', '').strip()
    if not name:
        return jsonify({"error": "Tool name required"}), 400
    existing = db.get_tool_by_name(name)
    if existing:
        return jsonify({"error": "Tool with this name already exists"}), 409
    try:
        defn = json.dumps({"type": "function", "function": data.get('definition', {})})
    except:
        return jsonify({"error": "Invalid tool definition"}), 400
    is_global = 1 if data.get('is_global') and require_admin() is None else 0
    tid = db.create_tool(name, data.get('description', ''), defn, is_global=is_global, user_id=session['user_id'])
    return jsonify({"status": "success", "id": tid})

@app.route('/api/tools/<tool_id>', methods=['PUT'])
def update_tool_route(tool_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    tool = db.get_tool(tool_id)
    if not tool:
        return jsonify({"error": "Not found"}), 404
    if not tool['is_global'] and tool['user_id'] != session['user_id']:
        return jsonify({"error": "Forbidden"}), 403
    if tool['is_global']:
        err = require_admin()
        if err: return err
    data = request.json
    db.update_tool(tool_id, name=data.get('name'), description=data.get('description'),
                   definition=json.dumps(data.get('definition', {})) if 'definition' in data else None,
                   enabled=data.get('enabled'))
    return jsonify({"status": "success"})

@app.route('/api/tools/<tool_id>', methods=['DELETE'])
def delete_tool_route(tool_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    tool = db.get_tool(tool_id)
    if not tool:
        return jsonify({"error": "Not found"}), 404
    if not tool['is_global'] and tool['user_id'] != session['user_id']:
        return jsonify({"error": "Forbidden"}), 403
    if tool['is_global']:
        err = require_admin()
        if err: return err
    db.delete_tool(tool_id)
    return jsonify({"status": "success"})


# --- PROVIDER CONFIG ---
@app.route('/api/provider/config', methods=['GET'])
def get_provider_config():
    return jsonify(db.get_provider_config())

@app.route('/api/provider/config', methods=['POST'])
def set_provider_config():
    data = request.json
    db.set_provider_config(data.get('provider', 'ollama'), data.get('api_key', ''), data.get('ollama_url', ''))
    if data.get('ollama_url'):
        Config.OLLAMA_API_URL = data['ollama_url']
    return jsonify({"status": "success"})

@app.route('/api/provider/models')
def get_provider_models():
    pconf = db.get_provider_config()
    provider = pconf.get('provider', 'ollama')
    api_key = pconf.get('api_key', '')
    try:
        models = providers.get_available_models(provider, api_key=api_key or None)
        return jsonify(models if isinstance(models, list) else [])
    except Exception:
        return jsonify([])


# --- STANDARD API ---
@app.route('/api/models')
def get_models():
    pconf = db.get_provider_config()
    provider = pconf.get('provider', 'ollama')
    if provider != 'ollama':
        api_key = pconf.get('api_key', '')
        try:
            models = providers.get_available_models(provider, api_key=api_key or None)
            return jsonify({"models": models if isinstance(models, list) else []})
        except Exception:
            return {"error": f"{provider.title()} unavailable"}
    try:
        resp = requests.get(f'{Config.OLLAMA_API_URL}/api/tags', timeout=2)
        return resp.json() if resp.status_code == 200 else {"models": []}
    except:
        return {"error": "Ollama Down"}

@app.route('/api/models/manage', methods=['GET'])
def list_ollama_models():
    try:
        resp = requests.get(f'{Config.OLLAMA_API_URL}/api/tags', timeout=2)
        if resp.status_code == 200:
            return jsonify(resp.json().get('models', []))
        return jsonify([])
    except:
        return jsonify({"error": "Ollama Down"}), 503

@app.route('/api/models/pull', methods=['POST'])
def pull_ollama_model():
    name = request.json.get('name', '')
    if not name:
        return jsonify({"error": "Model name required"}), 400
    try:
        resp = requests.post(f'{Config.OLLAMA_API_URL}/api/pull', json={"name": name, "stream": False}, timeout=600)
        return jsonify({"status": "success" if resp.status_code == 200 else "error", "message": resp.text})
    except Exception as e:
        return jsonify({"error": "Failed to pull model"}), 500

@app.route('/api/models/<name>', methods=['DELETE'])
def delete_ollama_model(name):
    try:
        resp = requests.delete(f'{Config.OLLAMA_API_URL}/api/delete', json={"name": name}, timeout=30)
        return jsonify({"status": "success" if resp.status_code == 200 else "error"})
    except Exception as e:
        return jsonify({"error": "Failed to delete model"}), 500

@app.route('/api/history')
def history():
    include_archived = request.args.get('archived', '0') == '1'
    return jsonify(db.get_history(user_id=session.get('user_id'), include_archived=include_archived))

@app.route('/api/search')
def search():
    q = request.args.get('q', '').strip()
    model = request.args.get('model', '').strip()
    project_id = request.args.get('project_id', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    if not q:
        return jsonify([])
    return jsonify(db.search_messages(q, user_id=session.get('user_id'), model=model or None, project_id=project_id or None, date_from=date_from or None, date_to=date_to or None))

@app.route('/api/chat/<session_id>')
def load_chat(session_id): 
    if not db.verify_session_owner(session_id, session.get('user_id')):
        return jsonify({"error": "Forbidden"}), 403
    session_info = db.get_session_info(session_id)
    messages = db.get_messages(session_id)
    return jsonify({
        "messages": messages, 
        "model": session_info['model'] if session_info else None,
        "system_prompt": session_info['system_prompt'] if session_info else None,
        "project_id": session_info['project_id'] if session_info else None
    })

def _check_session(session_id):
    if not db.verify_session_owner(session_id, session.get('user_id')):
        return jsonify({"error": "Forbidden"}), 403

@app.route('/api/fork', methods=['POST'])
def fork_chat():
    session_id = request.json.get('session_id')
    msg_id = request.json.get('msg_id')
    if not session_id or not msg_id:
        return jsonify({"error": "session_id and msg_id required"}), 400
    err = _check_session(session_id)
    if err: return err
    new_id = db.fork_session(session_id, msg_id)
    if new_id:
        return jsonify({"session_id": new_id})
    return jsonify({"error": "Fork failed"}), 500

@app.route('/api/archive/<session_id>', methods=['POST'])
def archive(session_id):
    err = _check_session(session_id)
    if err: return err
    db.archive_session(session_id, request.json.get('archived', True))
    return jsonify({"status": "success"})

@app.route('/api/pin/<session_id>', methods=['POST'])
def pin(session_id):
    err = _check_session(session_id)
    if err: return err
    db.pin_session(session_id, request.json.get('pinned', True))
    return jsonify({"status": "success"})

@app.route('/api/bulk-delete', methods=['POST'])
def bulk_delete():
    ids = request.json.get('ids', [])
    if ids:
        for sid in ids:
            if not db.verify_session_owner(sid, session.get('user_id')):
                return jsonify({"error": "Forbidden"}), 403
        db.bulk_delete_sessions(ids)
    return jsonify({"status": "success"})

@app.route('/api/rename', methods=['POST'])
def rename():
    sid = request.json['id']
    err = _check_session(sid)
    if err: return err
    db.rename_session(sid, request.json['title'])
    return jsonify({"status": "success"})

@app.route('/api/delete/<session_id>', methods=['DELETE'])
def delete(session_id):
    err = _check_session(session_id)
    if err: return err
    db.delete_session(session_id)
    return jsonify({"status": "success"})

@app.route('/api/messages/<msg_id>/pin', methods=['POST'])
def pin_message(msg_id):
    new_val = db.toggle_pin_message(msg_id)
    if new_val is not None:
        return jsonify({"status": "success", "pinned": new_val})
    return jsonify({"error": "Message not found"}), 404


# --- GROUPS ---
@app.route('/api/groups', methods=['GET'])
def get_groups():
    return jsonify(db.get_groups())

@app.route('/api/groups', methods=['POST'])
def create_group():
    title = request.json.get('title', 'New Group')
    gid = db.create_group(title)
    return jsonify({"id": gid, "title": title})

@app.route('/api/groups/<gid>', methods=['DELETE'])
def delete_group(gid):
    db.delete_group(gid)
    return jsonify({"status": "success"})

@app.route('/api/sessions/group', methods=['POST'])
def set_session_group():
    db.set_session_group(request.json['session_id'], request.json.get('group_id'))
    return jsonify({"status": "success"})


# --- TAGS ---
@app.route('/api/tags', methods=['GET'])
def get_tags():
    return jsonify(db.get_all_tags(user_id=session.get('user_id')))

@app.route('/api/sessions/<sid>/tags', methods=['GET'])
def get_session_tags(sid):
    err = _check_session(sid)
    if err: return err
    return jsonify(db.get_session_tags(sid))

@app.route('/api/sessions/<sid>/tags', methods=['POST'])
def add_session_tag_route(sid):
    err = _check_session(sid)
    if err: return err
    tag = request.json.get('tag', '')
    if not tag:
        return jsonify({"error": "Tag required"}), 400
    db.add_session_tag(sid, tag)
    return jsonify({"status": "success", "tags": db.get_session_tags(sid)})

@app.route('/api/sessions/<sid>/tags/<tag>', methods=['DELETE'])
def remove_session_tag_route(sid, tag):
    err = _check_session(sid)
    if err: return err
    db.remove_session_tag(sid, tag)
    return jsonify({"status": "success", "tags": db.get_session_tags(sid)})

@app.route('/api/tags/<tag>/sessions', methods=['GET'])
def get_sessions_by_tag_route(tag):
    return jsonify(db.get_sessions_by_tag(tag, user_id=session.get('user_id')))


# --- PROMPTS ---
@app.route('/api/prompts', methods=['GET'])
def get_prompts(): return jsonify(db.get_prompts())
@app.route('/api/prompts', methods=['POST'])
def add_prompt():
    db.add_prompt(request.json['title'], request.json['content'])
    return jsonify({"status": "success"})
@app.route('/api/prompts/<pid>', methods=['DELETE'])
def del_prompt(pid):
    db.delete_prompt(pid)
    return jsonify({"status": "success"})


# --- HEALTH ---
@app.route('/api/health')
def health():
    ollama_ok = False
    try:
        r = requests.get(f'{Config.OLLAMA_API_URL}/api/tags', timeout=2)
        ollama_ok = r.status_code == 200
    except:
        pass
    return jsonify({
        "ollama": ollama_ok,
        "db_size": db.get_db_size(),
        "db_path": Config.DB_FILE,
        "status": "ok" if ollama_ok else "degraded"
    })


# --- DB BACKUP ---
@app.route('/api/db/export')
def export_db():
    uid = session.get('user_id')
    sessions = db.get_history(user_id=uid, include_archived=True)
    data = {"exported_at": str(datetime.now()), "user_id": uid, "sessions": []}
    for s in sessions:
        msgs = db.get_messages(s['id'])
        data["sessions"].append({"title": s['title'], "model": s['model'], "messages": msgs})
    return Response(
        json.dumps(data, indent=2, default=str),
        mimetype='application/json',
        headers={"Content-disposition": "attachment; filename=localneural_export.json"}
    )

@app.route('/api/db/import', methods=['POST'])
def import_db():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    f = request.files['file']
    tmp_path = Config.DB_FILE + ".tmp_import"
    f.save(tmp_path)
    try:
        with open(tmp_path, 'rb') as fh:
            header = fh.read(16)
        if header != b'SQLite format 3\x00':
            os.remove(tmp_path)
            return jsonify({"error": "Invalid database file"}), 400
        conn = sqlite3.connect(tmp_path)
        conn.execute("SELECT COUNT(*) FROM sqlite_master")
        conn.close()
    except Exception:
        os.remove(tmp_path)
        return jsonify({"error": "Invalid database file"}), 400
    backup = Config.DB_FILE + ".backup"
    if os.path.exists(Config.DB_FILE):
        shutil.copy2(Config.DB_FILE, backup)
    os.replace(tmp_path, Config.DB_FILE)
    db.init_db()
    return jsonify({"status": "success", "backup": os.path.exists(backup)})


# --- URL SCRAPER ---
@app.route('/api/urlscrape', methods=['POST'])
def url_scrape():
    url = request.json.get('url', '').strip()
    if not url:
        return jsonify({"error": "No URL"}), 400
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        text = file_parser.extract_html_text(resp.text) or resp.text[:50000]
        return jsonify({"content": text[:50000], "url": url})
    except Exception as e:
        return jsonify({"error": "Failed to scrape URL"}), 500


# --- AUDIO TRANSCRIBE ---
@app.route('/api/audio/transcribe', methods=['POST'])
def transcribe_audio():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file"}), 400
    f = request.files['audio']
    try:
        audio_bytes = f.read()
        b64 = base64.b64encode(audio_bytes).decode('utf-8')
        resp = requests.post(
            f'{Config.OLLAMA_API_URL}/api/chat',
            json={
                "model": "whisper",
                "messages": [{"role": "user", "content": "Transcribe this audio", "images": [b64]}]
            },
            timeout=60
        )
        if resp.status_code == 200:
            text = resp.json().get('message', {}).get('content', '')
            return jsonify({"text": text})
        return jsonify({"error": f"Whisper failed: {resp.text}"}), 500
    except Exception as e:
        return jsonify({"error": "Transcription failed"}), 500


# --- FILE UPLOAD (Ad-hoc Q&A) ---
MAX_FILE_SIZE = 5 * 1024 * 1024

@app.route('/api/chat/upload', methods=['POST'])
def chat_file_upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files['file']
    if f.filename == '':
        return jsonify({"error": "Empty filename"}), 400
    if not f.filename.lower().endswith(('.pdf', '.docx', '.csv', '.json', '.txt', '.md', '.py', '.js', '.ts', '.html', '.css', '.xml', '.yaml', '.yml', '.log', '.ini', '.cfg')):
        return jsonify({"error": "Unsupported file type"}), 400
    content = file_parser.extract_text_from_file(f)
    if not content or not content.strip():
        return jsonify({"error": "Could not extract text from file"}), 400
    return jsonify({"filename": f.filename, "content": content[:100000], "size": len(content)})


def _path_safe(path):
    real = os.path.realpath(path)
    return any(real.startswith(d) for d in Config.ALLOWED_FILE_DIRS)

# --- FILE READ (for /file command) ---
@app.route('/api/file/read', methods=['POST'])
def file_read():
    path = request.json.get('path', '').strip()
    if not path:
        return jsonify({"error": "No path provided"}), 400
    if not _path_safe(path):
        return jsonify({"error": "Access denied: path not in allowed directories"}), 403
    try:
        if not os.path.isfile(path):
            return jsonify({"error": "File not found"}), 404
        if os.path.getsize(path) > MAX_FILE_SIZE:
            return jsonify({"error": "File too large (max 5MB)"}), 400
        with open(path, 'r', encoding='utf-8', errors='replace') as fh:
            content = fh.read(100000)
        return jsonify({"filename": os.path.basename(path), "content": content, "path": path})
    except Exception as e:
        return jsonify({"error": "Failed to read file"}), 500


# --- STATS ---
@app.route('/api/stats')
def get_stats():
    return jsonify(db.get_stats(user_id=session.get('user_id')))


# --- SUMMARIZE ---
@app.route('/api/summarize/<session_id>', methods=['POST'])
def summarize_session(session_id):
    err = _check_session(session_id)
    if err: return err
    msgs = db.get_messages(session_id)
    if not msgs:
        return jsonify({"error": "No messages"}), 400
    conversation_text = "\n".join(f"{m['role'].upper()}: {m['content'][:2000]}" for m in msgs[-50:])
    try:
        resp = requests.post(f'{Config.OLLAMA_API_URL}/api/chat', json={
            "model": request.json.get('model', Config.DEFAULT_MODEL),
            "messages": [
                {"role": "system", "content": "Summarize this conversation concisely in 3-5 bullet points. Focus on key decisions, questions, and answers."},
                {"role": "user", "content": conversation_text}
            ],
            "options": {"temperature": 0.3},
            "stream": False
        }, timeout=60)
        if resp.status_code == 200:
            summary = resp.json().get('message', {}).get('content', '')
            return jsonify({"summary": summary})
        return jsonify({"error": "Summarization failed"}), 500
    except Exception as e:
        return jsonify({"error": "Summarization failed"}), 500


# --- WEB SEARCH ---
@app.route('/api/websearch', methods=['POST'])
def web_search():
    query = request.json.get('query', '').strip()
    if not query:
        return jsonify({"error": "No query"}), 400
    try:
        from utilities.web_search import search_duckduckgo
        results = search_duckduckgo(query)
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": "Search failed"}), 500


# --- EXPORT ---
@app.route('/api/export/<session_id>')
def export(session_id):
    err = _check_session(session_id)
    if err: return err
    fmt = request.args.get('format', 'md')
    msgs = db.get_messages(session_id)

    def render_content(m):
        img_html = ""
        if m.get('images'):
            try:
                for img in json.loads(m['images']):
                    img_html += f"\n![image](data:image/jpeg;base64,{img})\n"
            except:
                pass
        return m['content'] + img_html

    if fmt == 'json':
        enriched = []
        for m in msgs:
            entry = dict(m)
            if entry.get('images'):
                try: entry['images'] = json.loads(entry['images'])
                except: pass
            enriched.append(entry)
        return jsonify(enriched)

    if fmt == 'md':
        out = "# Chat Export\n\n"
        for m in msgs:
            out += f"### {m['role'].upper()}\n{render_content(m)}\n\n"
        return Response(out, mimetype='text/markdown', headers={"Content-disposition": "attachment; filename=chat.md"})

    if fmt == 'html':
        style = ("<style>body{font-family:sans-serif;max-width:800px;margin:auto;padding:20px;"
                 "background:#f4f4f4}.user{background:#fff;padding:15px;margin-bottom:10px;"
                 "border-radius:8px}.ai{background:#e0f7fa;padding:15px;margin-bottom:10px;"
                 "border-radius:8px}img{max-width:300px;border-radius:4px}</style>")
        out = style
        for m in msgs:
            out += f"<div class='{m['role']}'><strong>{m['role'].upper()}</strong><pre>{m['content']}</pre>{render_content(m)}</div>"
        return Response(out, mimetype='text/html')

    return "Error", 400


# --- MESSAGE EXPORT ---
@app.route('/api/messages/<msg_id>/export')
def export_message(msg_id):
    fmt = request.args.get('format', 'md')
    conn = db.get_db()
    msg = conn.execute("SELECT * FROM messages WHERE id = ?", (msg_id,)).fetchone()
    conn.close()
    if not msg:
        return jsonify({"error": "Message not found"}), 404
    content = msg['content']
    role = msg['role'].upper()
    if fmt == 'md':
        out = f"> *Exported from LocalNeural — {role}*\n\n{content}"
        return Response(out, mimetype='text/markdown', headers={"Content-disposition": f"attachment; filename=message_{msg_id}.md"})
    return jsonify({"role": role, "content": content})


# --- FORK / BRANCH INFO ---
@app.route('/api/sessions/<sid>/branches')
def get_session_branches(sid):
    if not db.verify_session_owner(sid, session.get('user_id')):
        return jsonify({"error": "Forbidden"}), 403
    return jsonify(db.get_session_branch_info(sid))


# --- ADMIN ---
def require_admin():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user = db.get_user_by_id(session['user_id'])
    if not user or (user.get('role') or 'user') != 'admin':
        return jsonify({"error": "Forbidden"}), 403
    return None

@app.route('/api/admin/users', methods=['GET'])
def admin_list_users():
    err = require_admin()
    if err: return err
    conn = db.get_db()
    rows = conn.execute("SELECT id, username, email, full_name, role, created_at FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/admin/users/<uid>', methods=['DELETE'])
def admin_delete_user(uid):
    err = require_admin()
    if err: return err
    conn = db.get_db()
    conn.execute("DELETE FROM sessions WHERE user_id = ?", (uid,))
    conn.execute("DELETE FROM users WHERE id = ?", (uid,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/admin/settings', methods=['GET'])
def admin_get_settings():
    err = require_admin()
    if err: return err
    return jsonify({
        "system_prompt": db.get_system_prompt(),
        "allow_registration": db.get_setting('allow_registration', 'true'),
    })

@app.route('/api/admin/settings', methods=['POST'])
def admin_set_settings():
    err = require_admin()
    if err: return err
    data = request.json
    if 'system_prompt' in data:
        db.set_system_prompt(data['system_prompt'])
    if 'allow_registration' in data:
        db.set_setting('allow_registration', data['allow_registration'])
    if 'provider' in data:
        db.set_setting('global_provider', data['provider'])
    if 'model' in data:
        db.set_setting('global_model', data['model'])
    return jsonify({"status": "success"})


# --- ADMIN DASHBOARD PAGE ---
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    user = db.get_user_by_id(session['user_id'])
    if not user or (user.get('role') or 'user') != 'admin':
        return redirect(url_for('home'))
    return render_template('admin_dashboard.html')


@app.route('/api/admin/users/<uid>/role', methods=['PUT'])
def admin_set_user_role(uid):
    err = require_admin()
    if err: return err
    role = request.json.get('role', 'user')
    if role not in ('user', 'admin'):
        return jsonify({"error": "Invalid role"}), 400
    conn = db.get_db()
    conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, uid))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})


# --- BACKGROUND TASKS ---
def background_rename(sid, prompt, model):
    title = utils.generate_smart_title(prompt, model)
    db.rename_session(sid, title)
    socketio.emit('title_updated', {'session_id': sid, 'title': title})

def index_document_embeddings(doc_id, content):
    try:
        chunks = [content[i:i+2000] for i in range(0, len(content), 2000)]
        vectors = embed_utils.embed_texts(chunks)
        if vectors:
            db.save_doc_embeddings(doc_id, chunks, vectors)
            print(f"Indexed {len(chunks)} chunks for document {doc_id}")
    except Exception as e:
        print(f"Embedding indexing error: {e}")

# --- SOCKETS ---
@socketio.on('stop_generation')
def handle_stop(data):
    if data.get('session_id'): active_streams[data['session_id']] = False

@socketio.on('regenerate')
def handle_regenerate(data):
    session_id = data.get('session_id')
    model = data.get('model')
    temperature = float(data.get('temperature', Config.DEFAULT_TEMP))
    options = data.get('options', {})
    
    deleted = db.delete_last_ai_message(session_id)
    if not deleted: return 
    
    generate_response(session_id, model, temperature, options, file_context=None)

@socketio.on('user_message')
def handle_message(data):
    prompt = data.get('prompt', '')
    model = data.get('model')
    session_id = data.get('session_id')
    temperature = float(data.get('temperature', Config.DEFAULT_TEMP))
    options = data.get('options', {})
    is_edit = data.get('is_edit', False)
    msg_id = data.get('msg_id')
    images = data.get('images', [])
    req_system_prompt = data.get('system_prompt')
    file_context = data.get('file_context')  # {filename, content} for ad-hoc file Q&A
    
    project_id = data.get('project_id') 

    is_new_chat = False
    uid = session.get('user_id')
    if not session_id:
        title = "New Chat..."
        session_id = db.create_session(title, model, req_system_prompt, project_id, user_id=uid)
        emit('session_created', {'session_id': session_id, 'title': title})
        is_new_chat = True
    else:
        db.update_session_model(session_id, model)

    current_msg_id = None
    if is_edit and msg_id:
        session_id = db.update_message(msg_id, prompt)
        current_msg_id = msg_id
    else:
        img_str = json.dumps(images) if images else None
        current_msg_id = db.save_message(session_id, "user", prompt, img_str)
    
    emit('message_saved', {'temp_id': data.get('temp_id'), 'db_id': current_msg_id})

    if is_new_chat:
        threading.Thread(target=background_rename, args=(session_id, prompt, model)).start()

    generate_response(session_id, model, temperature, options, file_context=file_context)

def generate_response(session_id, model, temperature, options=None, file_context=None):
    history, system_prompt = utils.get_session_context(session_id)

    now = datetime.now()
    username = session.get('username', 'User')
    system_prompt = system_prompt.replace('{date}', now.strftime('%B %d, %Y'))
    system_prompt = system_prompt.replace('{time}', now.strftime('%I:%M %p'))
    system_prompt = system_prompt.replace('{datetime}', now.strftime('%B %d, %Y at %I:%M %p'))
    system_prompt = system_prompt.replace('{user}', username)

    if file_context and file_context.get('content'):
        fc = file_context
        context_str = f"\n\n[SYSTEM: The user has attached the file '{fc['filename']}'. Use its contents to answer the user's query.]\n--- BEGIN FILE: {fc['filename']} ---\n{fc['content'][:50000]}\n--- END FILE ---\n"
        system_prompt = context_str + system_prompt
        print(f"Using ad-hoc file context for Session {session_id}: {fc['filename']}")

    ollama_messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        m_obj = {"role": msg['role'], "content": msg['content']}
        if msg['images']:
            try: m_obj['images'] = json.loads(msg['images'])
            except: pass
        ollama_messages.append(m_obj)

    active_streams[session_id] = True
    opts = {"temperature": temperature}
    max_tokens_val = None
    if options:
        if options.get('top_p'): opts['top_p'] = float(options['top_p'])
        if options.get('top_k'): opts['top_k'] = int(options['top_k'])
        if options.get('repeat_penalty'): opts['repeat_penalty'] = float(options['repeat_penalty'])
        if options.get('max_tokens'): 
            opts['num_predict'] = int(options['max_tokens'])
            max_tokens_val = int(options['max_tokens'])

    # Load provider config
    pconf = db.get_provider_config()
    provider = pconf.get('provider', 'ollama')
    api_key = pconf.get('api_key', '')
    ollama_url = pconf.get('ollama_url', '')
    if ollama_url:
        Config.OLLAMA_API_URL = ollama_url

    # Build tool definitions from static + DB tools
    tool_defs = list(tool_utils.TOOL_DEFINITIONS)
    uid = session.get('user_id')
    if uid:
        db_tools = db.get_all_tools(user_id=uid)
        for t in db_tools:
            try:
                defn = json.loads(t['definition'])
                if isinstance(defn, dict):
                    tool_defs.append(defn)
            except:
                pass

    # Tool use loop: up to 5 rounds of tool calls
    max_tool_rounds = 5
    for _ in range(max_tool_rounds):
        full_resp = ""
        tool_calls = []
        _generation_start_time[session_id] = time.time()
        _token_count[session_id] = 0
        try:
            stream_gen = providers.chat_completion(
                provider=provider, model=model, messages=ollama_messages,
                options=opts, api_key=api_key or None, stream=True,
                tools=tool_defs if tool_defs else None
            )
            for chunk in stream_gen:
                if not active_streams.get(session_id, True): break
                if 'content' in chunk and chunk['content']:
                    c = chunk['content']
                    full_resp += c
                    _token_count[session_id] = _token_count.get(session_id, 0) + 1
                    elapsed = time.time() - _generation_start_time.get(session_id, time.time())
                    tps = round(_token_count[session_id] / elapsed, 1) if elapsed > 0 else 0
                    emit('stream_chunk', {'chunk': c, 'tps': tps, 'tokens': _token_count[session_id], 'max_tokens': max_tokens_val})
                if 'tool_calls' in chunk and chunk['tool_calls']:
                    tool_calls = chunk['tool_calls']
                if 'error' in chunk:
                    emit('stream_chunk', {'chunk': f"\n**Error:** {chunk['error']}"})
        except requests.exceptions.ConnectionError:
            emit('stream_chunk', {'chunk': "**Error:** Cannot connect to AI provider. Is it running?"})
            db.save_message(session_id, "assistant", full_resp)
            emit('stream_done', {})
            return
        except Exception:
            emit('stream_chunk', {'chunk': "**Error:** Generation failed"})

        if not tool_calls:
            break

        # Execute tool calls
        for tc in tool_calls:
            name = tc["function"]["name"]
            emit('stream_chunk', {'chunk': f"\n> **Using tool:** `{name}`..."})
            result = tool_utils.execute_tool(tc)
            ollama_messages.append({"role": "assistant", "content": "", "tool_calls": [tc]})
            ollama_messages.append({"role": "tool", "content": result})
            emit('stream_chunk', {'chunk': f" done.\n\n"})

    db.save_message(session_id, "assistant", full_resp)
    db.update_session_tokens(session_id, _token_count.get(session_id, 0))
    emit('stream_done', {})
    
if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    socketio.run(app, debug=debug_mode, port=Config.PORT, host=Config.HOST)
