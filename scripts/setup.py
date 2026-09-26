"""Create local secrets without echoing them or replacing an existing .env."""

from pathlib import Path
import secrets
from cryptography.fernet import Fernet

root = Path(__file__).resolve().parents[1]
path = root / ".env"
if path.exists():
    raise SystemExit(".env existe déjà : aucun changement.")
text = (root / ".env.example").read_text()
values = {
    "BENCH_PASSWORD": secrets.token_urlsafe(18),
    "SESSION_SECRET": secrets.token_urlsafe(48),
    "WORKER_SECRET": secrets.token_urlsafe(48),
    "ENCRYPTION_KEY": Fernet.generate_key().decode(),
}
for name, value in values.items():
    text = "\n".join(
        name + "=" + value if line.startswith(name + "=") else line
        for line in text.split("\n")
    )
path.write_text(text)
path.chmod(0o600)
print(
    "Secrets locaux créés dans .env. Choisissez votre BENCH_PASSWORD puis renseignez LiveKit."
)
