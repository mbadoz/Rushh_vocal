import os, tempfile
from cryptography.fernet import Fernet

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(
    prefix="rushh-test-", suffix=".db"
)
os.environ["BENCH_PASSWORD"] = "test-password"
os.environ["SESSION_SECRET"] = "session-test-only"
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["WORKER_SECRET"] = "worker-test-only"
os.environ["CARTESIA_API_KEY"] = "env-cartesia-test"
os.environ["GROQ_API_KEY"] = "env-groq-test"
os.environ["LIVEKIT_API_KEY"] = "test-lk"
os.environ["LIVEKIT_API_SECRET"] = "test-secret-long-enough-for-signature"
os.environ["LIVEKIT_URL"] = "wss://test.livekit.cloud"
import pytest
from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        c.post("/api/login", json={"password": "test-password"})
        yield c
