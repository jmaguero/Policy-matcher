# Policy Matcher

A compliance automation tool that uses LLMs (Anthropic, OpenAI, or local Ollama models) to:
1.  **Analyze** a client's policy PDF against a control framework (XLSX).
2.  **Rewrite** policy improvement suggestions into actionable tasks.
3.  **Generate** a final Word report (`.docx`).

## Prerequisites

- **Documents**: You must have a `documents/` folder in the project root containing a `template_report.docx` file. This is required for report generation.
- **Docker**: [Docker](https://docs.docker.com/get-docker/) + [Docker Compose](https://docs.docker.com/compose/) (Recommended)
- **API Keys**:
    - Anthropic API Key (if using Claude models)
    - OpenAI API Key (if using GPT models)
    - Local Ollama instance (if using local models like Llama 3, Mistral, DeepSeek, etc.)

## Configuration

1. Copy the example env file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your keys and configuration:
   | Variable | Description |
   |---|---|
   | `ANTHROPIC_API_KEY` | Your Anthropic API key |
   | `OPENAI_API_KEY` | Your OpenAI API key |
   | `OLLAMA_HOST` | URL of your Ollama instance. **Docker Users:** Use `http://host.docker.internal:11434` or your LAN IP. Do *not* use `localhost`. |

---

## Usage

### Option 1: Docker (Recommended)

Run the application with a single command. The frontend and backend are automatically networked.

**Start** (rebuilds image to apply code changes):
```bash
docker compose up --build
```

**Access**:
- **App**: [http://localhost](http://localhost) (Port 80)
- **Backend API Docs**: [http://localhost:8002/docs](http://localhost:8002/docs)

**Stop**:
```bash
docker compose down
```

> [!NOTE]
> Since the source code is copied into the image at build time, you must run `docker compose up --build` whenever you modify the code to see your changes.

### Option 2: Local Development (Manual)

Run the backend locally. It will also serve the frontend static files, so you don't need a separate frontend server.

1.  **Install Dependencies** (Python 3.10+ required):
    ```bash
    cd backend
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

2.  **Run the Server**:
    ```bash
    # You must run from inside the backend/ directory so Python finds the modules
    cd backend
    uvicorn main:app --reload --port 8000
    ```

**Access**:
- **App**: [http://localhost:8000](http://localhost:8000)
- **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
