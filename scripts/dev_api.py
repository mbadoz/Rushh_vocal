"""Local UI verification with isolated data; no external provider credentials."""

import os
from cryptography.fernet import Fernet

os.environ.update(
    FRONTEND_ORIGIN="http://127.0.0.1:3000",
    BENCH_PASSWORD="test-password",
    SESSION_SECRET="local-ui-test-secret",
    ENCRYPTION_KEY=Fernet.generate_key().decode(),
    WORKER_SECRET="local-ui-worker-secret",
    DATABASE_URL="sqlite:////tmp/rushh-ui-check.db",
)
import uvicorn

uvicorn.run("api.main:app", host="127.0.0.1", port=8000)
