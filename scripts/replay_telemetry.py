"""Retry uploads saved during an API outage. No provider calls."""

from pathlib import Path
import os, json, httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
with httpx.Client(
    base_url=os.environ["BENCH_API_URL"],
    headers={"Authorization": "Bearer " + os.environ["WORKER_SECRET"]},
    timeout=30,
) as client:
    for path in Path("data/pending").glob("*.json"):
        client.put(
            "/internal/runs/" + path.stem, json=json.loads(path.read_text())
        ).raise_for_status()
        path.unlink()
        print("Envoyé :", path.stem)
