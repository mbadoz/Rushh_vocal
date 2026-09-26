.PHONY: install setup api web worker test build
install:
	python3.11 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	cd web && npm ci
setup:
	.venv/bin/python scripts/setup.py
api:
	.venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
web:
	cd web && npm run dev
worker:
	.venv/bin/python agent.py dev
test:
	.venv/bin/python -m pytest -q
	cd web && npm run typecheck
build:
	cd web && npm run build
