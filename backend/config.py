import os

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODELS = ["claude-haiku-4-5", "claude-sonnet-4-5"]

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODELS = ["gpt-5.2","gpt-4.1"]

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODELS = ["gemma3:4b", "deepseek-r1:1.5b"]