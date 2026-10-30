import os
import tempfile

_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_db.name}"
os.environ["LLM_MODE"] = "mock"
os.environ["GROK_API_KEY"] = ""
os.environ["APP_SECRET"] = "test-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def login(client, name="Tester"):
    r = client.post("/api/auth/guest", json={"display_name": name})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}
