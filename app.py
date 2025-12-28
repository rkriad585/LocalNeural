import json
import requests
import threading
from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO, emit
from config import Config
import database as db
import utilities.chat_logic as utils
import utilities.file_parser as file_parser # New Import

app = Flask(__name__)
app.config.from_object(Config)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', max_http_buffer_size=10*1024*1024)

db.init_db()
active_streams = {}
    
@app.route('/')
def home(): return render_template('index.html')

# --- PROJECT API (FIXED) ---
@app.route('/api/projects', methods=['GET'])
def get_projects(): return jsonify(db.get_projects())

# FUNCTION: create_project
# LINE: 35
@app.route('/api/projects', methods=['POST'])
def create_project():
    try:
        title = request.form.get('title')
        desc = request.form.get('description')
        
        # 1. Create Project Entry
        project_id = db.create_project(title, desc)
        
        # 2. Handle Files
        if 'files' in request.files:
            files = request.files.getlist('files')
            for f in files:
                if f.filename != '':
                    # Use the robust parser
                    content = file_parser.extract_text_from_file(f)
                    if content:
                        db.add_project_document(project_id, f.filename, content)
                        print(f"Saved document: {f.filename} ({len(content)} chars)")
                    
        return jsonify({"status": "success", "id": project_id})
    except Exception as e:
        print(f"Project Creation Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
        

@app.route('/api/projects/<pid>', methods=['DELETE'])
def delete_project(pid):
    db.delete_project(pid)
    return jsonify({"status": "success"})

# --- CONFIG API ---
@app.route('/api/config', methods=['GET'])
def get_config(): return jsonify({"system_prompt": db.get_system_prompt()})

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
    except: return {"error": "Ollama Down"}

@app.route('/api/history')
def history(): return jsonify(db.get_history())

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

@app.route('/api/rename', methods=['POST'])
def rename():
    db.rename_session(request.json['id'], request.json['title'])
    return jsonify({"status": "success"})

@app.route('/api/delete/<session_id>', methods=['DELETE'])
def delete(session_id):
    db.delete_session(session_id)
    return jsonify({"status": "success"})

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

@app.route('/api/export/<session_id>')
def export(session_id):
    fmt = request.args.get('format', 'md')
    msgs = db.get_messages(session_id)
    if fmt == 'json': return jsonify(msgs)
    if fmt == 'md':
        out = "# Chat Export\n\n"
        for m in msgs: out += f"### {m['role'].upper()}\n{m['content']}\n\n"
        return Response(out, mimetype='text/markdown', headers={"Content-disposition": "attachment; filename=chat.md"})
    if fmt == 'html':
        out = "<style>body{font-family:sans-serif;max-width:800px;margin:auto;padding:20px;background:#f4f4f4}.user{background:#fff;padding:15px;margin-bottom:10px;border-radius:8px}.ai{background:#e0f7fa;padding:15px;margin-bottom:10px;border-radius:8px}</style>"
        for m in msgs: out += f"<div class='{m['role']}'><strong>{m['role'].upper()}</strong><pre>{m['content']}</pre></div>"
        return Response(out, mimetype='text/html')
    return "Error", 400

# --- BACKGROUND TASK ---
def background_rename(sid, prompt, model):
    title = utils.generate_smart_title(prompt, model)
    db.rename_session(sid, title)
    socketio.emit('title_updated', {'session_id': sid, 'title': title})

# --- SOCKETS ---
@socketio.on('stop_generation')
def handle_stop(data):
    if data.get('session_id'): active_streams[data['session_id']] = False

@socketio.on('regenerate')
def handle_regenerate(data):
    session_id = data.get('session_id')
    model = data.get('model')
    temperature = float(data.get('temperature', Config.DEFAULT_TEMP))
    
    deleted = db.delete_last_ai_message(session_id)
    if not deleted: return 
    
    generate_response(session_id, model, temperature)

@socketio.on('user_message')
def handle_message(data):
    prompt = data.get('prompt', '')
    model = data.get('model')
    session_id = data.get('session_id')
    temperature = float(data.get('temperature', Config.DEFAULT_TEMP))
    is_edit = data.get('is_edit', False)
    msg_id = data.get('msg_id')
    images = data.get('images', [])
    req_system_prompt = data.get('system_prompt')
    
    # NEW: Project Link
    project_id = data.get('project_id') 

    is_new_chat = False
    if not session_id:
        title = "New Chat..."
        # Pass project_id to creation
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

    generate_response(session_id, model, temperature)

# FUNCTION: generate_response
def generate_response(session_id, model, temperature):
    """Generates response, injecting Project Knowledge if applicable"""
    
    # 1. Get History & Base System Prompt
    history, system_prompt = utils.get_session_context(session_id)
    
    # 2. Check for Project Knowledge
    session_info = db.get_session_info(session_id)
    if session_info and session_info['project_id']:
        docs = db.get_project_documents(session_info['project_id'])
        if docs:
            # Explicitly instruct AI to use this context
            context_str = "\n\n[SYSTEM: The user has attached the following Project Files/Knowledge Base. Use them to answer queries.]\n"
            for doc in docs:
                # Add file content (Safeguard: 10k chars per file max)
                content_snippet = doc['content'][:10000] 
                context_str += f"\n--- FILE: {doc['filename']} ---\n{content_snippet}\n"
            context_str += "\n[END PROJECT FILES]\n"
            
            # Prepend to system prompt
            system_prompt = context_str + system_prompt
            print(f"Injecting Project Context for Session {session_id}")

    ollama_messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        m_obj = {"role": msg['role'], "content": msg['content']}
        if msg['images']:
            try: m_obj['images'] = json.loads(msg['images'])
            except: pass
        ollama_messages.append(m_obj)

    active_streams[session_id] = True
    payload = {
        "model": model, "messages": ollama_messages, 
        "options": {"temperature": temperature}, "stream": True
    }

    full_resp = ""
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
                        emit('stream_chunk', {'chunk': c})
    except Exception as e:
        emit('stream_chunk', {'chunk': f"**Error:** {str(e)}"})
    
    db.save_message(session_id, "assistant", full_resp)
    emit('stream_done', {})
    
if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000, host='0.0.0.0')
