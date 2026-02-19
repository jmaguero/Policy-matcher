import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Stub endpoints
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", [
    "/process/button1",
    "/process/button2",
    "/process/button3",
])
def test_stub_endpoints_return_not_implemented(path):
    r = client.post(path)
    assert r.status_code == 200
    assert r.json() == {"status": "not implemented"}


@pytest.mark.parametrize("path", [
    "/process/button1",
    "/process/button2",
    "/process/button3",
])
def test_stub_endpoints_reject_get(path):
    r = client.get(path)
    assert r.status_code == 405


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

def test_cors_header_present_on_cross_origin_request():
    r = client.post(
        "/process/button1",
        headers={"Origin": "http://localhost:3000"},
    )
    assert r.headers.get("access-control-allow-origin") == "*"


def test_cors_preflight_returns_200():
    r = client.options(
        "/process/button1",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert r.status_code == 200
