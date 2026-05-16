import os
import json
import requests
from config import Config

ENV_KEY_MAP = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "groq": "GROQ_API_KEY",
}

BASE_URL_MAP = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
    "openrouter": "https://openrouter.ai/api/v1",
    "groq": "https://api.groq.com/openai/v1",
}

COMPAT_PROVIDERS = {"openai", "openrouter", "groq"}


def _get_api_key(provider, api_key=None):
    if api_key:
        return api_key
    env_key = ENV_KEY_MAP.get(provider)
    if env_key:
        return os.environ.get(env_key)
    return None


def _convert_tools_to_anthropic(tools):
    converted = []
    for tool in tools:
        func = tool.get("function", tool)
        converted.append({
            "name": func["name"],
            "description": func.get("description", ""),
            "input_schema": func.get("parameters", {}),
        })
    return converted


def _convert_tools_to_gemini(tools):
    converted = []
    for tool in tools:
        func = tool.get("function", tool)
        converted.append({
            "name": func["name"],
            "description": func.get("description", ""),
            "parameters": func.get("parameters", {}),
        })
    return [{"function_declarations": converted}]


def _convert_messages_to_gemini(messages):
    contents = []
    system_instruction = None
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            system_instruction = {"parts": [{"text": content}]}
        else:
            gemini_role = "model" if role in ("assistant", "model") else "user"
            contents.append({"role": gemini_role, "parts": [{"text": content}]})
    return contents, system_instruction


def _ollama_stream(model, messages, options):
    url = f"{Config.OLLAMA_API_URL}/api/chat"
    payload = {"model": model, "messages": messages, "stream": True}
    if options:
        opt_copy = {k: v for k, v in options.items() if k != "tools"}
        if opt_copy:
            payload["options"] = opt_copy
        if "tools" in options:
            payload["tools"] = options["tools"]
    try:
        response = requests.post(url, json=payload, stream=True)
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            try:
                data = json.loads(line)
                msg = data.get("message", {})
                if msg.get("content"):
                    yield {"content": msg["content"]}
                if data.get("done"):
                    break
            except json.JSONDecodeError:
                continue
    except requests.exceptions.ConnectionError:
        yield {"error": "Ollama is not running. Start it with 'ollama serve'."}
    except requests.exceptions.HTTPError as e:
        yield {"error": f"Ollama HTTP error: {e}"}
    except Exception as e:
        yield {"error": f"Ollama error: {e}"}


def _openai_compat_stream(provider, model, messages, options, api_key):
    url = f"{BASE_URL_MAP[provider]}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = "http://localhost:5000"
        headers["X-Title"] = "LocalNeural"
    payload = {"model": model, "messages": messages, "stream": True}
    if options:
        for key in ("temperature", "max_tokens", "top_p", "frequency_penalty", "presence_penalty", "stop", "tools", "tool_choice"):
            if key in options:
                payload[key] = options[key]
    try:
        response = requests.post(url, headers=headers, json=payload, stream=True)
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8").strip()
            if not decoded.startswith("data: "):
                continue
            data_str = decoded[6:]
            if data_str == "[DONE]":
                break
            try:
                data = json.loads(data_str)
                choices = data.get("choices", [])
                for choice in choices:
                    delta = choice.get("delta", {})
                    if delta.get("content"):
                        yield {"content": delta["content"]}
                    if delta.get("tool_calls"):
                        yield {"tool_calls": delta["tool_calls"]}
                    finish = choice.get("finish_reason")
                    if finish == "tool_calls":
                        yield {"finish_reason": "tool_calls"}
            except json.JSONDecodeError:
                continue
    except requests.exceptions.HTTPError as e:
        yield {"error": f"{provider.capitalize()} HTTP error: {e}"}
    except Exception as e:
        yield {"error": f"{provider.capitalize()} error: {e}"}


def _openai_compat_non_stream(provider, model, messages, options, api_key):
    url = f"{BASE_URL_MAP[provider]}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = "http://localhost:5000"
        headers["X-Title"] = "LocalNeural"
    payload = {"model": model, "messages": messages, "stream": False}
    if options:
        for key in ("temperature", "max_tokens", "top_p", "frequency_penalty", "presence_penalty", "stop", "tools", "tool_choice"):
            if key in options:
                payload[key] = options[key]
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        choice = data["choices"][0]
        msg = choice.get("message", {})
        if msg.get("tool_calls"):
            return msg["tool_calls"]
        return msg.get("content", "")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"{provider.capitalize()} HTTP error: {e}")
    except Exception as e:
        raise RuntimeError(f"{provider.capitalize()} error: {e}")


def _anthropic_stream(model, messages, options, api_key):
    url = f"{BASE_URL_MAP['anthropic']}/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    system_msg = None
    anthro_messages = []
    for msg in messages:
        if msg.get("role") == "system":
            system_msg = msg["content"]
        else:
            anthro_messages.append({"role": msg["role"], "content": msg["content"]})
    payload = {"model": model, "messages": anthro_messages, "stream": True}
    if system_msg:
        payload["system"] = system_msg
    if options:
        if "temperature" in options:
            payload["temperature"] = options["temperature"]
        if "max_tokens" in options:
            payload["max_tokens"] = options["max_tokens"]
        if "tools" in options:
            payload["tools"] = _convert_tools_to_anthropic(options["tools"])
    try:
        response = requests.post(url, headers=headers, json=payload, stream=True)
        response.raise_for_status()
        current_event = None
        for line in response.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8").strip()
            if decoded.startswith("event: "):
                current_event = decoded[7:]
            elif decoded.startswith("data: "):
                data_str = decoded[6:]
                try:
                    data = json.loads(data_str)
                    if current_event == "content_block_delta":
                        delta = data.get("delta", {})
                        if delta.get("type") == "text_delta" and delta.get("text"):
                            yield {"content": delta["text"]}
                    elif current_event == "content_block_start":
                        block = data.get("content_block", {})
                        if block.get("type") == "tool_use":
                            yield {
                                "tool_call_start": {
                                    "id": block["id"],
                                    "name": block["name"],
                                }
                            }
                    elif current_event == "content_block_stop" and data.get("index") is not None:
                        pass
                    elif current_event == "message_stop":
                        break
                except json.JSONDecodeError:
                    continue
    except requests.exceptions.HTTPError as e:
        yield {"error": f"Anthropic HTTP error: {e}"}
    except Exception as e:
        yield {"error": f"Anthropic error: {e}"}


def _anthropic_non_stream(model, messages, options, api_key):
    url = f"{BASE_URL_MAP['anthropic']}/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    system_msg = None
    anthro_messages = []
    for msg in messages:
        if msg.get("role") == "system":
            system_msg = msg["content"]
        else:
            anthro_messages.append({"role": msg["role"], "content": msg["content"]})
    payload = {"model": model, "messages": anthro_messages, "stream": False}
    if system_msg:
        payload["system"] = system_msg
    if options:
        if "temperature" in options:
            payload["temperature"] = options["temperature"]
        if "max_tokens" in options:
            payload["max_tokens"] = options["max_tokens"]
        if "tools" in options:
            payload["tools"] = _convert_tools_to_anthropic(options["tools"])
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        content_blocks = data.get("content", [])
        text_parts = [b["text"] for b in content_blocks if b.get("type") == "text" and b.get("text")]
        tool_blocks = [b for b in content_blocks if b.get("type") == "tool_use"]
        if tool_blocks:
            return [
                {
                    "id": b["id"],
                    "type": "function",
                    "function": {
                        "name": b["name"],
                        "arguments": json.dumps(b.get("input", {})),
                    },
                }
                for b in tool_blocks
            ]
        return "".join(text_parts)
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Anthropic HTTP error: {e}")
    except Exception as e:
        raise RuntimeError(f"Anthropic error: {e}")


def _gemini_stream(model, messages, options, api_key):
    url = f"{BASE_URL_MAP['gemini']}/models/{model}:streamGenerateContent?key={api_key}"
    contents, system_instruction = _convert_messages_to_gemini(messages)
    payload = {"contents": contents}
    if system_instruction:
        payload["system_instruction"] = system_instruction
    if options:
        gc = {}
        if "temperature" in options:
            gc["temperature"] = options["temperature"]
        if "max_tokens" in options:
            gc["maxOutputTokens"] = options["max_tokens"]
        if "top_p" in options:
            gc["topP"] = options["top_p"]
        if "stop" in options:
            gc["stopSequences"] = [options["stop"]] if isinstance(options["stop"], str) else options["stop"]
        if gc:
            payload["generationConfig"] = gc
        if "tools" in options:
            payload["tools"] = _convert_tools_to_gemini(options["tools"])
    try:
        response = requests.post(url, json=payload, stream=True)
        response.raise_for_status()
        buffer = ""
        for chunk in response.iter_content(chunk_size=None):
            if not chunk:
                continue
            buffer += chunk.decode("utf-8")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                if line.startswith("data: "):
                    line = line[6:]
                if line == "[DONE]":
                    return
                try:
                    data = json.loads(line)
                    candidates = data.get("candidates", [])
                    for candidate in candidates:
                        parts = candidate.get("content", {}).get("parts", [])
                        for part in parts:
                            if part.get("text"):
                                yield {"content": part["text"]}
                        finish = candidate.get("finishReason")
                        if finish:
                            yield {"finish_reason": finish}
                except json.JSONDecodeError:
                    continue
    except requests.exceptions.HTTPError as e:
        yield {"error": f"Gemini HTTP error: {e}"}
    except Exception as e:
        yield {"error": f"Gemini error: {e}"}


def _gemini_non_stream(model, messages, options, api_key):
    url = f"{BASE_URL_MAP['gemini']}/models/{model}:generateContent?key={api_key}"
    contents, system_instruction = _convert_messages_to_gemini(messages)
    payload = {"contents": contents}
    if system_instruction:
        payload["system_instruction"] = system_instruction
    if options:
        gc = {}
        if "temperature" in options:
            gc["temperature"] = options["temperature"]
        if "max_tokens" in options:
            gc["maxOutputTokens"] = options["max_tokens"]
        if "top_p" in options:
            gc["topP"] = options["top_p"]
        if "stop" in options:
            gc["stopSequences"] = [options["stop"]] if isinstance(options["stop"], str) else options["stop"]
        if gc:
            payload["generationConfig"] = gc
        if "tools" in options:
            payload["tools"] = _convert_tools_to_gemini(options["tools"])
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        text_parts = [p["text"] for p in parts if p.get("text")]
        return "".join(text_parts)
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Gemini HTTP error: {e}")
    except Exception as e:
        raise RuntimeError(f"Gemini error: {e}")


def _ollama_non_stream(model, messages, options):
    url = f"{Config.OLLAMA_API_URL}/api/chat"
    payload = {"model": model, "messages": messages, "stream": False}
    if options:
        opt_copy = {k: v for k, v in options.items() if k != "tools"}
        if opt_copy:
            payload["options"] = opt_copy
        if "tools" in options:
            payload["tools"] = options["tools"]
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        msg = data.get("message", {})
        return msg.get("content", "")
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Ollama is not running. Start it with 'ollama serve'.")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Ollama HTTP error: {e}")
    except Exception as e:
        raise RuntimeError(f"Ollama error: {e}")


def stream_response(provider, model, messages, options=None, api_key=None):
    options = options or {}
    api_key = _get_api_key(provider, api_key)
    provider = provider.lower()

    if provider == "ollama":
        yield from _ollama_stream(model, messages, options)
    elif provider in COMPAT_PROVIDERS:
        if not api_key:
            yield {"error": f"{provider.capitalize()} requires an API key."}
            return
        yield from _openai_compat_stream(provider, model, messages, options, api_key)
    elif provider == "anthropic":
        if not api_key:
            yield {"error": "Anthropic requires an API key."}
            return
        yield from _anthropic_stream(model, messages, options, api_key)
    elif provider == "gemini":
        if not api_key:
            yield {"error": "Gemini requires an API key."}
            return
        yield from _gemini_stream(model, messages, options, api_key)
    else:
        yield {"error": f"Unknown provider: {provider}"}


def chat_completion(provider, model, messages, options=None, api_key=None, stream=True):
    options = options or {}
    api_key = _get_api_key(provider, api_key)
    provider = provider.lower()

    if stream:
        return stream_response(provider, model, messages, options, api_key)

    if provider == "ollama":
        return _ollama_non_stream(model, messages, options)
    elif provider in COMPAT_PROVIDERS:
        if not api_key:
            raise RuntimeError(f"{provider.capitalize()} requires an API key.")
        return _openai_compat_non_stream(provider, model, messages, options, api_key)
    elif provider == "anthropic":
        if not api_key:
            raise RuntimeError("Anthropic requires an API key.")
        return _anthropic_non_stream(model, messages, options, api_key)
    elif provider == "gemini":
        if not api_key:
            raise RuntimeError("Gemini requires an API key.")
        return _gemini_non_stream(model, messages, options, api_key)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def get_available_models(provider, api_key=None):
    provider = provider.lower()
    api_key = _get_api_key(provider, api_key)

    if provider == "ollama":
        try:
            resp = requests.get(f"{Config.OLLAMA_API_URL}/api/tags", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    elif provider in COMPAT_PROVIDERS:
        if not api_key:
            return []
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            if provider == "openrouter":
                headers["HTTP-Referer"] = "http://localhost:5000"
                headers["X-Title"] = "LocalNeural"
            resp = requests.get(
                f"{BASE_URL_MAP[provider]}/models",
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []

    elif provider == "anthropic":
        if not api_key:
            return []
        return [
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]

    elif provider == "gemini":
        if not api_key:
            return []
        try:
            resp = requests.get(
                f"{BASE_URL_MAP['gemini']}/models?key={api_key}",
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            models = []
            for m in data.get("models", []):
                name = m.get("name", "")
                if "generateContent" in m.get("supportedGenerationMethods", []):
                    models.append(name.replace("models/", ""))
            return sorted(models)
        except Exception:
            return [
                "gemini-2.0-flash",
                "gemini-2.0-flash-lite",
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-1.5-flash-8b",
            ]

    else:
        return []
