import os
from dotenv import load_dotenv

# Load .env from project root (parent directory of backend/)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODELS = ["claude-haiku-4-5", "claude-sonnet-4-5"]

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODELS = ["gpt-5.2", "gpt-4.1"]

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "")
if OLLAMA_HOST and not OLLAMA_HOST.startswith(("http://", "https://")):
    OLLAMA_HOST = f"http://{OLLAMA_HOST}"
OLLAMA_HOST = OLLAMA_HOST.rstrip("/")
OLLAMA_MODELS = ["gemma3:4b", "deepseek-r1:1.5b"]
