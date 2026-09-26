"""LiveKit CLI entrypoint (run from the repository root)."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
from livekit.agents import WorkerOptions, cli
from worker.agent import entrypoint

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name=os.getenv("LIVEKIT_AGENT_NAME", "rushh-bench"),
        )
    )
