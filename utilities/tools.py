import datetime
import json
import os
from config import Config

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information. Returns snippets and URLs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "current_time",
            "description": "Get the current date and time.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the local filesystem. Only readable text files up to 100KB.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to the file"}
                },
                "required": ["path"]
            }
        }
    }
]


def execute_tool(tool_call):
    name = tool_call["function"]["name"]
    try:
        args = json.loads(tool_call["function"]["arguments"])
    except (json.JSONDecodeError, KeyError):
        args = {}

    if name == "current_time":
        return json.dumps({"result": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

    if name == "web_search":
        query = args.get("query", "")
        if not query:
            return json.dumps({"error": "No query provided"})
        try:
            from utilities.web_search import search_duckduckgo
            results = search_duckduckgo(query)
            return json.dumps({"results": results[:5]})
        except Exception as e:
            return json.dumps({"error": str(e)})

    if name == "read_file":
        path = args.get("path", "")
        if not path:
            return json.dumps({"error": "No path provided"})
        real = os.path.realpath(path)
        if not any(real.startswith(d) for d in Config.ALLOWED_FILE_DIRS):
            return json.dumps({"error": "Access denied: path not in allowed directories"})
        try:
            if not os.path.isfile(path):
                return json.dumps({"error": "File not found"})
            if os.path.getsize(path) > 100 * 1024:
                return json.dumps({"error": "File too large (max 100KB)"})
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(100000)
            return json.dumps({"filename": os.path.basename(path), "content": content[:50000]})
        except Exception as e:
            return json.dumps({"error": str(e)})

    return json.dumps({"error": f"Unknown tool: {name}"})
