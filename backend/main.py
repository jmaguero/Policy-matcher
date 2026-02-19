from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from button1 import MAX_PDF_BYTES, run_button1
from button2 import run_button2
from button3 import run_button3

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


@app.post("/process/button1")
async def button1(
    pdf_file: UploadFile = File(...),
    xlsx_file: UploadFile = File(...),
    client_name: str = Form(...),
    system_prompt1: str = Form(...),
    selected_provider1: str = Form(...),
    selected_llm1: str = Form(...),
):
    # Validate XLSX by extension (magic-byte check happens inside button1 via openpyxl)
    if not (xlsx_file.filename or "").endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="xlsx_file must be an .xlsx file")

    # LLM10: enforce upload size limits before reading fully into memory
    pdf_bytes = await _read_limited(pdf_file, MAX_PDF_BYTES, "PDF")
    xlsx_bytes = await _read_limited(xlsx_file, MAX_XLSX_BYTES, "XLSX")

    try:
        result = run_button1(
            pdf_bytes=pdf_bytes,
            xlsx_bytes=xlsx_bytes,
            xlsx_filename=xlsx_file.filename,
            client_name=client_name,
            system_prompt=system_prompt1,
            provider=selected_provider1,
            model=selected_llm1,
        )
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@app.post("/process/button2")
async def button2(
    input_xlsx_filename: str = Form(...),
    system_prompt2: str = Form(...),
    selected_provider2: str = Form(...),
    selected_llm2: str = Form(...),
):
    try:
        result = run_button2(
            input_xlsx_filename=input_xlsx_filename,
            system_prompt=system_prompt2,
            provider=selected_provider2,
            model=selected_llm2,
        )
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@app.post("/process/button3")
async def button3(
    input_xlsx_filename: str = Form(...),
):
    try:
        result = run_button3(input_xlsx_filename=input_xlsx_filename)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result
