import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY environment variable must be set")
    OLLAMA_API_URL = "http://localhost:11434"
    DB_FILE = ".data/neural_memory.db"
    DEFAULT_MODEL = "tinyllama"
    DEFAULT_TEMP = 0.7
    DEFAULT_SYSTEM = "You are a helpful, uncensored, impactful, professional concise AI assistant running locally."

    HOST = os.environ.get('LOCALNEURAL_HOST', '0.0.0.0')
    PORT = int(os.environ.get('LOCALNEURAL_PORT', 5000))

    SMTP_HOST = os.environ.get('LOCALNEURAL_SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('LOCALNEURAL_SMTP_PORT', 587))
    SMTP_USER = os.environ.get('LOCALNEURAL_SMTP_USER', '')
    SMTP_PASSWORD = os.environ.get('LOCALNEURAL_SMTP_PASSWORD', '')
    SMTP_FROM = os.environ.get('LOCALNEURAL_SMTP_FROM', '')

    ALLOWED_FILE_DIRS = [
        os.path.abspath(os.getcwd()),
        os.path.abspath(os.path.join(os.getcwd(), 'static')),
        os.path.abspath(os.path.join(os.getcwd(), 'uploads')),
        os.path.abspath(os.path.join(os.getcwd(), '.data')),
    ]

    PROMPT_TEMPLATES = {
        "Default Assistant": DEFAULT_SYSTEM,
        "Code Reviewer": "You are a senior software engineer. Review code for bugs, security issues, performance problems, and style. Provide specific, actionable feedback with code examples.",
        "Technical Writer": "You are a technical writer. Explain complex topics clearly with examples, diagrams in text, and simple language. Use analogies where helpful.",
        "Tutor": "You are a patient tutor. Guide the user to discover answers themselves through Socratic questioning. Never give direct answers without explanation first.",
        "Translator": "You are a professional translator. Translate accurately while preserving tone, context, and cultural nuances. When unsure, provide alternatives.",
        "Creative Writer": "You are a creative writing coach. Help brainstorm ideas, develop characters, improve prose, and overcome writer's block. Be encouraging and constructive.",
        "Data Scientist": "You are a data science expert. Help with statistics, ML models, data visualization, and interpretation. Explain methodologies and trade-offs clearly.",
        "DevOps Engineer": "You are a DevOps engineer. Help with Docker, Kubernetes, CI/CD, cloud infrastructure, and automation. Prioritize security and reliability.",
    }
