"""Build a small standalone API deployment directory (no ML dependencies)."""

from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
target = root / "data/api-deploy"
target.mkdir(parents=True, exist_ok=True)
shutil.copytree(
    root / "api",
    target / "api",
    dirs_exist_ok=True,
    ignore=shutil.ignore_patterns("__pycache__"),
)
for source, name in [
    ("requirements-api.txt", "requirements.txt"),
    ("app.py", "app.py"),
    ("deploy/api/vercel.json", "vercel.json"),
]:
    shutil.copyfile(root / source, target / name)
print("API prête dans data/api-deploy. Ajouter les variables avant le déploiement.")
