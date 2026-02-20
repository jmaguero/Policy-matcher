# Retrospective: Post-Assessment Fixes and Improvements

## Overview

This document describes what was not working at the end of the assessment day, the root causes, and the fixes applied afterwards. It also lists what still needs improvement.

This is left as a pull request — not merged into `main` — for review.

***

## Assessment Context

All API keys (Anthropic and OpenAI) were provided during the assessment, and Ollama was running on a separate machine accessible via the local network. During development and testing at home, the container could not reach Ollama at `localhost` because inside Docker that resolves to the container itself, not the host. This introduced an environment-specific assumption in the configuration that was likely the same class of issue that caused problems on the day.

After the assessment, with no API keys available at home, tests for the Anthropic and OpenAI providers use known-format mock responses. These validate the integration logic — call structure, JSON parsing, retry behaviour — without hitting the real APIs.

***

## What Was Wrong

### Broken end-to-end flow

**Step 3 (report generation) did not receive the required filename.**
The frontend was not passing `input_xlsx_filename` to the report endpoint, so the backend had no file to process. This caused a silent failure at the final step of the flow.

### Configuration and environment issues

**`.env` was not loaded reliably in local development.**
`backend/config.py` relied on `os.getenv()` alone. Without `python-dotenv`, the `.env` file at the project root was silently ignored during local runs, meaning `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, and `OLLAMA_HOST` could all be missing with no obvious error.

**`OLLAMA_HOST` had no validation or normalization.**
There was no check that the value was a valid URL, no automatic protocol prefix, no clear error message on connection failure. When the host was misconfigured — easy to do with the LAN/Docker distinction — errors were hard to trace back to the real cause.

### Code quality

**Backend modules and endpoints used placeholder names (`button1`, `button2`, `button3`).**
These carried over from early scaffolding. They made the code harder to read and the API harder to understand at a glance.

**README did not cover the Ollama networking requirement.**
The most likely point of failure for anyone running this — the correct `OLLAMA_HOST` value inside Docker — was not documented.

***

## What Was Fixed

### End-to-end flow

- **Frontend (`frontend/app.js`)**: Now correctly passes `input_xlsx_filename` to the report endpoint. A download button appears after report generation so the result is immediately accessible without leaving the app.
- **Backend (`backend/main.py`)**: Added a `GET /download/{filename}` endpoint with path traversal protection — resolves the requested path and rejects anything outside `outputs/`.
- **Nginx (`frontend/nginx.conf`)**: Added a `/download/` proxy rule so download requests reach the FastAPI backend in the Docker setup.

### Configuration and environment

- **`backend/config.py`**: Now uses `python-dotenv` to explicitly load `.env` from the project root. Added `python-dotenv` to `backend/requirements.txt`.
- **`backend/config.py`**: Added URL normalization for `OLLAMA_HOST` — automatically adds `http://` if missing and strips trailing slashes.
- **`backend/llm.py`**: Added an explicit guard when `OLLAMA_HOST` is empty. Added specific error handling for `InvalidURL`, `ConnectError`, and `HTTPStatusError`, each with a message pointing to the likely cause.
- **`.env.example`**: Updated with comments explaining the correct `OLLAMA_HOST` value for each scenario: Docker on Mac/Windows, Docker on Linux, and direct LAN access. Explicitly notes that `localhost` inside a container refers to the container, not the host.

### Code quality and naming

Renamed backend modules to reflect what they actually do:
- `button1.py` → `analysis.py` (public function: `analyze_policy`)
- `button2.py` → `rewrite.py` (public function: `rewrite_suggestions`)
- `button3.py` → `report.py` (public function: `generate_report`)

Renamed API endpoints to match:
- `/process/button1` → `/process/analyze`
- `/process/button2` → `/process/rewrite`
- `/process/button3` → `/process/report`

All references updated across `main.py`, the frontend, and the tests.

### Docker and README

- Changed backend port mapping to `8002:8000` in `docker-compose.yml` to avoid conflicts with the default port.
- Added a named Docker volume (`outputs_data`) so generated files persist across container restarts.
- Rewrote the README:
  - Describes what the tool does in three steps.
  - Separates Docker (recommended) and local development instructions.
  - Documents all environment variables.
  - Explains the Ollama networking requirement explicitly.

### Tests

- Updated `backend/tests/test_api.py` to use the new endpoint names.
- Added `backend/tests/test_download.py`:
  - Happy path: file is found and returned.
  - File not found: returns `404`.
  - Path traversal attempts: returns `400` or `404`, never the requested file.
- Also in this PR: additional tests in `backend/tests/test_llm.py` covering JSON parsing edge cases (text before or after the JSON block) and the shape of SDK calls to Anthropic and OpenAI.

***

## Known Remaining Issues

### Report output: content appends at the end of the document

The generated `.docx` currently adds all findings at the **end** of the template document rather than at the correct insertion point within the template body. The placement logic needs to target the right position inside the document structure.

### Frontend structure

`frontend/app.js` and `frontend/index.html` have grown too large and handle too many concerns in a single file. They should be split into smaller, focused modules. Left out of this PR to keep scope focused on the broken flow.

***

*PR branch — not merged into `main`.*

***