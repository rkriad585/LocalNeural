import requests
import json
from config import Config
import database as db

def generate_smart_title(user_prompt, model):
    try:
        system_instruction = "You are a title generator. Summarize the user's input into a 3 to 5 word concise title. Do not use quotes. Do not say 'Here is a title'."

        resp = requests.post(
            f'{Config.OLLAMA_API_URL}/api/chat',
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {"temperature": 0.3}
            },
            timeout=5
        )

        if resp.status_code == 200:
            data = resp.json()
            title = data.get('message', {}).get('content', '').strip()
            title = title.replace('"', '').replace("Title:", "").strip()
            return title if title else user_prompt[:30]

    except requests.exceptions.ConnectionError:
        print("Title Gen: Ollama is not running")
    except Exception as e:
        print(f"Title Gen Error: {e}")

    return (user_prompt[:30] + '..') if len(user_prompt) > 30 else user_prompt

def get_session_context(session_id):
    """
    Retrieves history and determines the correct system prompt (Session specific > Global)
    """
    history = db.get_messages(session_id)
    
    # 1. Check if session has a specific prompt
    sys_prompt = db.get_session_system_prompt(session_id)
    
    # 2. If not, use global
    if not sys_prompt:
        sys_prompt = db.get_system_prompt()
        
    return history, sys_prompt
