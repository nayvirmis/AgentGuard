.PHONY: install dev backend frontend test lint format seed

install:
	python3 -m venv .venv
	.venv/bin/pip install -e "backend[dev]"
	npm --prefix frontend install

dev:
	docker compose up --build

backend:
	PYTHONPATH=. .venv/bin/uvicorn backend.app.main:app --reload --port 8000

frontend:
	npm --prefix frontend run dev

test:
	PYTHONPATH=. .venv/bin/pytest backend/tests
	npm --prefix frontend run test

lint:
	.venv/bin/ruff check backend mcp_server
	npm --prefix frontend run lint

format:
	.venv/bin/ruff format backend mcp_server
	npm --prefix frontend run format

seed:
	PYTHONPATH=. .venv/bin/python -m backend.app.seed

