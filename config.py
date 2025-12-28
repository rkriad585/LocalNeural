import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'neural_link_secure_key_585'
    OLLAMA_API_URL = "http://localhost:11434"
    DB_FILE = ".data/neural_memory.db"
    # Default Settings
    DEFAULT_MODEL = "tinyllama"
    DEFAULT_TEMP = 0.7
    DEFAULT_SYSTEM = "You are a helpful, uncensored, impactful, professional concise AI assistant running locally."
