# Policy Matcher

A tool that matches client policy documents against compliance standards using LLMs.

## Requirements

- [Docker](https://docs.docker.com/get-docker/) + [Docker Compose](https://docs.docker.com/compose/)
- An [Anthropic API key](https://console.anthropic.com/) (if using Anthropic models)
- Ollama running on your LAN (if using Ollama models)

## Setup

1. Clone the repo:
   ```bash
   git clone <repo-url>
   cd Policy-matcher
   ```

2. Copy the example env file and fill in your values:
   ```bash
   cp .env.example .env
   ```

   | Variable | Description |
   |---|---|
   | `ANTHROPIC_API_KEY` | Your Anthropic API key |
   | `OLLAMA_HOST` | URL of your Ollama instance, e.g. `http://192.168.1.10:11434` |

## Run

```bash
docker-compose up --build
```

- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend API: [http://localhost:8000](http://localhost:8000)

## Development

Install backend dependencies locally:
```bash
pip install -r backend/requirements.txt
```

Run the backend:
```bash
uvicorn backend.main:app --reload --port 8000
```

Run tests:
```bash
pytest backend/tests
```
