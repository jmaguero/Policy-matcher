from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Download Endpoint
# ---------------------------------------------------------------------------


def test_download_happy_path(tmp_path):
    # Mock OUTPUTS_DIR to point to a temporary directory
    filename = "test_report.docx"
    file_content = b"fake docx content"

    # Create the dummy file in tmp_path
    (tmp_path / filename).write_bytes(file_content)

    # We need to patch OUTPUTS_DIR in main.py.
    # Since main.py will import OUTPUTS_DIR from report.py (or similar),
    # we need to ensure we patch where it is *used* or *imported*.
    # Assuming main.py imports OUTPUTS_DIR from report.

    with patch("main.OUTPUTS_DIR", tmp_path):
        r = client.get(f"/download/{filename}")

    assert r.status_code == 200
    assert r.content == file_content
    # FastAPI FileResponse might set headers, we can check them if needed
    assert "attachment" in r.headers.get("content-disposition", "")
    assert filename in r.headers.get("content-disposition", "")


def test_download_file_not_found(tmp_path):
    with patch("main.OUTPUTS_DIR", tmp_path):
        r = client.get("/download/nonexistent.docx")
    assert r.status_code == 404


def test_download_directory_traversal_attempts(tmp_path):
    # Create a secret file outside of outputs
    secret_file = tmp_path.parent / "secret.txt"
    secret_file.write_text("secret")

    # OUTPUTS_DIR is tmp_path
    # Try to access ../secret.txt

    with patch("main.OUTPUTS_DIR", tmp_path):
        r = client.get("/download/../secret.txt")

    # Should be 404 or 400 depending on implementation, but definitely not 200 with secret content
    # Standard security practice is to just say Not Found or Bad Request
    assert r.status_code in [400, 404]
    assert r.content != b"secret"


def test_download_absolute_path(tmp_path):
    with patch("main.OUTPUTS_DIR", tmp_path):
        r = client.get("/download//etc/passwd")
    assert r.status_code in [400, 404]
