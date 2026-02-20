import io
from unittest.mock import patch

import openpyxl
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_xlsx_bytes() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["id", "title", "control"])
    ws.append(["1", "Test Control", "Requirement"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


FAKE_PDF = b"%PDF-1.4 minimal fake"
FAKE_XLSX = _make_xlsx_bytes()

_ANALYZE_FORM = dict(
    client_name="Acme",
    system_prompt1="You are an assistant.",
    selected_provider1="anthropic",
    selected_llm1="claude-haiku-4-5",
)
_ANALYZE_FILES = dict(
    pdf_file=("policy.pdf", FAKE_PDF, "application/pdf"),
    xlsx_file=(
        "controls.xlsx",
        FAKE_XLSX,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ),
)

_REWRITE_FORM = dict(
    input_xlsx_filename="20240101_120000_Acme_SOC2.xlsx",
    system_prompt2="Rewrite suggestions.",
    selected_provider2="anthropic",
    selected_llm2="claude-haiku-4-5",
)

_REPORT_FORM = dict(input_xlsx_filename="20240101_120000_Acme_SOC2.xlsx")


_PROCESS_PATHS = [
    "/api/process/analyze",
    "/api/process/rewrite",
    "/api/process/report",
]

# ---------------------------------------------------------------------------
# GET → 405
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", _PROCESS_PATHS)
def test_endpoints_reject_get(path):
    r = client.get(path)
    assert r.status_code == 405


# ---------------------------------------------------------------------------
# Missing required fields → 422
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", _PROCESS_PATHS)
def test_missing_required_fields_returns_422(path):
    r = client.post(path)
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Analyze
# ---------------------------------------------------------------------------


def test_analyze_happy_path():
    expected = {"json_file": "out.json", "xlsx_file": "out.xlsx", "results": []}
    with patch("main.analyze_policy", return_value=expected):
        r = client.post(
            "/api/process/analyze", data=_ANALYZE_FORM, files=_ANALYZE_FILES
        )
    assert r.status_code == 200
    assert r.json() == expected


def test_analyze_rejects_non_xlsx_extension():
    files = dict(
        pdf_file=("policy.pdf", FAKE_PDF, "application/pdf"),
        xlsx_file=("controls.csv", b"a,b,c", "text/csv"),
    )
    r = client.post("/api/process/analyze", data=_ANALYZE_FORM, files=files)
    assert r.status_code == 400
    assert "xlsx" in r.json()["detail"].lower()


def test_analyze_rejects_oversized_pdf():
    big_pdf = b"%PDF" + b"x" * 20
    with patch("main.MAX_PDF_BYTES", 10):
        r = client.post(
            "/api/process/analyze",
            data=_ANALYZE_FORM,
            files=dict(
                pdf_file=("big.pdf", big_pdf, "application/pdf"),
                xlsx_file=(
                    "controls.xlsx",
                    FAKE_XLSX,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            ),
        )
    assert r.status_code == 413


def test_analyze_rejects_oversized_xlsx():
    big_xlsx = b"x" * 20
    with patch("main.MAX_XLSX_BYTES", 10):
        r = client.post(
            "/api/process/analyze",
            data=_ANALYZE_FORM,
            files=dict(
                pdf_file=("policy.pdf", FAKE_PDF, "application/pdf"),
                xlsx_file=(
                    "controls.xlsx",
                    big_xlsx,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
            ),
        )
    assert r.status_code == 413


def test_analyze_value_error_returns_400():
    with patch("main.analyze_policy", side_effect=ValueError("Invalid PDF")):
        r = client.post(
            "/api/process/analyze", data=_ANALYZE_FORM, files=_ANALYZE_FILES
        )
    assert r.status_code == 400
    assert "Invalid PDF" in r.json()["detail"]


def test_analyze_file_not_found_returns_400():
    with patch("main.analyze_policy", side_effect=FileNotFoundError("missing")):
        r = client.post(
            "/api/process/analyze", data=_ANALYZE_FORM, files=_ANALYZE_FILES
        )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Rewrite
# ---------------------------------------------------------------------------


def test_rewrite_happy_path():
    expected = {"json_file": "out.json", "xlsx_file": "out.xlsx", "results": []}
    with patch("main.rewrite_suggestions", return_value=expected):
        r = client.post("/api/process/rewrite", data=_REWRITE_FORM)
    assert r.status_code == 200
    assert r.json() == expected


def test_rewrite_value_error_returns_400():
    with patch("main.rewrite_suggestions", side_effect=ValueError("bad filename")):
        r = client.post("/api/process/rewrite", data=_REWRITE_FORM)
    assert r.status_code == 400
    assert "bad filename" in r.json()["detail"]


def test_rewrite_file_not_found_returns_400():
    with patch("main.rewrite_suggestions", side_effect=FileNotFoundError("not found")):
        r = client.post("/api/process/rewrite", data=_REWRITE_FORM)
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def test_report_happy_path():
    expected = {"docx_file": "report.docx", "rows_reported": True}
    with patch("main.generate_report", return_value=expected):
        r = client.post("/api/process/report", data=_REPORT_FORM)
    assert r.status_code == 200
    assert r.json() == expected


def test_report_value_error_returns_400():
    with patch("main.generate_report", side_effect=ValueError("template missing")):
        r = client.post("/api/process/report", data=_REPORT_FORM)
    assert r.status_code == 400
    assert "template missing" in r.json()["detail"]


def test_report_file_not_found_returns_400():
    with patch("main.generate_report", side_effect=FileNotFoundError("no file")):
        r = client.post("/api/process/report", data=_REPORT_FORM)
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


def test_cors_header_present_on_cross_origin_request():
    with patch(
        "main.generate_report",
        return_value={"docx_file": "r.docx", "rows_reported": False},
    ):
        r = client.post(
            "/api/process/report",
            data=_REPORT_FORM,
            headers={"Origin": "http://localhost:3000"},
        )
    assert r.headers.get("access-control-allow-origin") == "*"


def test_cors_preflight_returns_200():
    r = client.options(
        "/api/process/analyze",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert r.status_code == 200
