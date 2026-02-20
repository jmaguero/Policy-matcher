import os

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from analysis import MAX_PDF_BYTES, analyze_policy
from rewrite import rewrite_suggestions
from report import generate_report

from fastapi.responses import FileResponse
from pathlib import Path

OUTPUTS_DIR = Path(__file__).parent / "outputs"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# LLM10: global upload size cap (enforced before reading into memory)
MAX_XLSX_BYTES = 5 * 1024 * 1024  # 5 MB


async def _read_limited(upload: UploadFile, max_bytes: int, label: str) -> bytes:
    """Read an upload, rejecting it if it exceeds max_bytes."""
    data = await upload.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"{label} exceeds maximum allowed size ({max_bytes // 1024 // 1024} MB)",
        )
    return data


@app.post("/api/process/analyze")
async def analyze_endpoint(
    pdf_file: UploadFile = File(...),
    xlsx_file: UploadFile = File(...),
    client_name: str = Form(...),
    system_prompt1: str = Form(...),
    selected_provider1: str = Form(...),
    selected_llm1: str = Form(...),
):
    # Validate XLSX by extension (magic-byte check happens inside openpyxl)
    if not (xlsx_file.filename or "").endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="xlsx_file must be an .xlsx file")

    # LLM10: enforce upload size limits before reading fully into memory
    pdf_bytes = await _read_limited(pdf_file, MAX_PDF_BYTES, "PDF")
    xlsx_bytes = await _read_limited(xlsx_file, MAX_XLSX_BYTES, "XLSX")

    try:
        result = analyze_policy(
            pdf_bytes=pdf_bytes,
            xlsx_bytes=xlsx_bytes,
            xlsx_filename=xlsx_file.filename,
            client_name=client_name,
            system_prompt=system_prompt1,
            provider=selected_provider1,
            model=selected_llm1,
        )
    except (ValueError, FileNotFoundError, RuntimeError) as e:
        print(f"ERROR in analyze_endpoint: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    return result


@app.post("/api/process/rewrite")
async def rewrite_endpoint(
    input_xlsx_filename: str = Form(...),
    system_prompt2: str = Form(...),
    selected_provider2: str = Form(...),
    selected_llm2: str = Form(...),
):
    try:
        result = rewrite_suggestions(
            input_xlsx_filename=input_xlsx_filename,
            system_prompt=system_prompt2,
            provider=selected_provider2,
            model=selected_llm2,
        )
    except (ValueError, FileNotFoundError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@app.post("/api/process/report")
async def report_endpoint(
    input_xlsx_filename: str = Form(...),
):
    try:
        result = generate_report(input_xlsx_filename=input_xlsx_filename)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    # Security: Prevent path traversal
    safe_path = (OUTPUTS_DIR / filename).resolve()
    if not safe_path.is_relative_to(OUTPUTS_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not safe_path.exists() or not safe_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=safe_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


# Local dev only: serve the frontend from FastAPI so that the relative /api/
# calls in app.js resolve correctly without a separate proxy.
# Requires SERVE_FRONTEND=1 AND the frontend/ directory to actually exist,
# so this never activates inside Docker (where the dir is absent).
_frontend_path = Path(__file__).parent.parent / "frontend"
if os.getenv("SERVE_FRONTEND") and _frontend_path.exists():
    from fastapi.staticfiles import StaticFiles

    app.mount(
        "/", StaticFiles(directory=str(_frontend_path), html=True), name="frontend"
    )
