import json
import os
import requests
import threading
import time
import shutil
import io
from flask import Flask, render_template, request, jsonify, Response, send_file
from flask_socketio import SocketIO, emit
from config import Config
import database as db
import utilities.chat_logic as utils
import utilities.file_parser as file_parser
import utilities.embeddings as embed_utils

app = Flask(__name__)
app.config.from_object(Config)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', max_http_buffer_size=10*1024*1024)

db.init_db()
active_streams = {}

_generation_start_time = {}
_token_count = {}


@app.route('/')
def home(): return render_template('index.html')


# --- PROJECTS ---
@app.route('/api/projects', methods=['GET'])
def get_projects(): return jsonify(db.get_projects())

@app.route('/api/projects', methods=['POST'])
def create_project():
    try:
        title = request.form.get('title')
        desc = request.form.get('description')
        project_id = db.create_project(title, desc)
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
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/projects/<pid>', methods=['DELETE'])
def delete_project(pid):
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


# --- STANDARD API ---
@app.route('/api/models')
def get_models():
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
        return jsonify({"error": str(e)}), 500

@app.route('/api/models/<name>', methods=['DELETE'])
def delete_ollama_model(name):
    try:
        resp = requests.delete(f'{Config.OLLAMA_API_URL}/api/delete', json={"name": name}, timeout=30)
        return jsonify({"status": "success" if resp.status_code == 200 else "error"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/history')
def history():
    include_archived = request.args.get('archived', '0') == '1'
    return jsonify(db.get_history(include_archived=include_archived))

@app.route('/api/search')
def search():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    return jsonify(db.search_messages(q))

@app.route('/api/chat/<session_id>')
def load_chat(session_id): 
    session_info = db.get_session_info(session_id)
    messages = db.get_messages(session_id)
    return jsonify({
        "messages": messages, 
        "model": session_info['model'] if session_info else None,
        "system_prompt": session_info['system_prompt'] if session_info else None,
        "project_id": session_info['project_id'] if session_info else None
    })

@app.route('/api/fork', methods=['POST'])
def fork_chat():
    session_id = request.json.get('session_id')
    msg_id = request.json.get('msg_id')
    if not session_id or not msg_id:
        return jsonify({"error": "session_id and msg_id required"}), 400
    new_id = db.fork_session(session_id, msg_id)
    if new_id:
        return jsonify({"session_id": new_id})
    return jsonify({"error": "Fork failed"}), 500

@app.route('/api/archive/<session_id>', methods=['POST'])
def archive(session_id):
    db.archive_session(session_id, request.json.get('archived', True))
    return jsonify({"status": "success"})

@app.route('/api/pin/<session_id>', methods=['POST'])
def pin(session_id):
    db.pin_session(session_id, request.json.get('pinned', True))
    return jsonify({"status": "success"})

@app.route('/api/bulk-delete', methods=['POST'])
def bulk_delete():
    ids = request.json.get('ids', [])
    if ids:
        db.bulk_delete_sessions(ids)
    return jsonify({"status": "success"})

@app.route('/api/rename', methods=['POST'])
def rename():
    db.rename_session(request.json['id'], request.json['title'])
    return jsonify({"status": "success"})

@app.route('/api/delete/<session_id>', methods=['DELETE'])
def delete(session_id):
    db.delete_session(session_id)
    return jsonify({"status": "success"})


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
    if os.path.exists(Config.DB_FILE):
        return send_file(Config.DB_FILE, as_attachment=True, download_name="neural_memory.db")
    return jsonify({"error": "DB not found"}), 404

@app.route('/api/db/import', methods=['POST'])
def import_db():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    f = request.files['file']
    backup = Config.DB_FILE + ".backup"
    if os.path.exists(Config.DB_FILE):
        shutil.copy2(Config.DB_FILE, backup)
    f.save(Config.DB_FILE)
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
        return jsonify({"error": str(e)}), 500


# --- AUDIO TRANSCRIBE ---
@app.route('/api/audio/transcribe', methods=['POST'])
def transcribe_audio():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file"}), 400
    f = request.files['audio']
    try:
        resp = requests.post(
            f'{Config.OLLAMA_API_URL}/api/chat',
            json={
                "model": "whisper",
                "messages": [{"role": "user", "content": "Transcribe this audio"}],
                "files": [{"name": "audio.wav", "data": f.read().hex()}]
            },
            timeout=30
        )
        if resp.status_code == 200:
            text = resp.json().get('message', {}).get('content', '')
            return jsonify({"text": text})
        return jsonify({"error": "Whisper failed"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
        return jsonify({"error": str(e)}), 500


# --- EXPORT ---
@app.route('/api/export/<session_id>')
def export(session_id):
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
    
    generate_response(session_id, model, temperature, options)

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
    
    project_id = data.get('project_id') 

    is_new_chat = False
    if not session_id:
        title = "New Chat..."
        session_id = db.create_session(title, model, req_system_prompt, project_id)
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

    generate_response(session_id, model, temperature, options)

def generate_response(session_id, model, temperature, options=None):
    history, system_prompt = utils.get_session_context(session_id)
    
    session_info = db.get_session_info(session_id)
    if session_info and session_info['project_id']:
        pid = session_info['project_id']
        # Try embedding-based retrieval first
        last_user_msg = ""
        for msg in reversed(history):
            if msg['role'] == 'user':
                last_user_msg = msg['content']
                break

        query_vec = embed_utils.embed_texts([last_user_msg]) if last_user_msg else None
        if query_vec:
            relevant = db.get_relevant_docs(pid, query_vec[0])
            if relevant:
                context_str = "\n\n[SYSTEM: Relevant project knowledge for context]\n"
                for score, filename, content in relevant:
                    snippet = content[:5000]
                    context_str += f"\n--- {filename} (relevance: {score:.2f}) ---\n{snippet}\n"
                context_str += "\n[END PROJECT FILES]\n"
                system_prompt = context_str + system_prompt
                print(f"Using embedding-based RAG for Session {session_id}")
        else:
            docs = db.get_project_documents(pid)
            if docs:
                context_str = "\n\n[SYSTEM: The user has attached the following Project Files/Knowledge Base. Use them to answer queries.]\n"
                for doc in docs:
                    content_snippet = doc['content'][:10000]
                    context_str += f"\n--- FILE: {doc['filename']} ---\n{content_snippet}\n"
                context_str += "\n[END PROJECT FILES]\n"
                system_prompt = context_str + system_prompt
                print(f"Using fallback RAG for Session {session_id}")

    ollama_messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        m_obj = {"role": msg['role'], "content": msg['content']}
        if msg['images']:
            try: m_obj['images'] = json.loads(msg['images'])
            except: pass
        ollama_messages.append(m_obj)

    active_streams[session_id] = True
    opts = {"temperature": temperature}
    if options:
        if options.get('top_p'): opts['top_p'] = float(options['top_p'])
        if options.get('top_k'): opts['top_k'] = int(options['top_k'])
        if options.get('repeat_penalty'): opts['repeat_penalty'] = float(options['repeat_penalty'])
        if options.get('max_tokens'): opts['num_predict'] = int(options['max_tokens'])
    payload = {
        "model": model, "messages": ollama_messages,
        "options": opts, "stream": True
    }

    full_resp = ""
    _generation_start_time[session_id] = time.time()
    _token_count[session_id] = 0
    try:
        with requests.post(f'{Config.OLLAMA_API_URL}/api/chat', json=payload, stream=True, timeout=120) as r:
            for line in r.iter_lines():
                if not active_streams.get(session_id, True): break
                if line:
                    j = json.loads(line)
                    if 'error' in j: emit('stream_chunk', {'chunk': f"\n**Error:** {j['error']}"}); break
                    if 'message' in j and 'content' in j['message']:
                        c = j['message']['content']
                        full_resp += c
                        _token_count[session_id] = _token_count.get(session_id, 0) + 1
                        elapsed = time.time() - _generation_start_time.get(session_id, time.time())
                        tps = round(_token_count[session_id] / elapsed, 1) if elapsed > 0 else 0
                        emit('stream_chunk', {'chunk': c, 'tps': tps, 'tokens': _token_count[session_id]})
    except Exception as e:
        emit('stream_chunk', {'chunk': f"**Error:** {str(e)}"})
    
    db.save_message(session_id, "assistant", full_resp)
    emit('stream_done', {})
    
if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000, host='0.0.0.0')
