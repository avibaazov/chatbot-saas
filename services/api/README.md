# API service (FastAPI)

Backend for the chatbot SaaS. See root `AGENTS.md` for target architecture and build order.

## Run locally

```bash
cd services/api
python -m venv venv
venv\Scripts\activate        # Windows
pip install -e ".[dev]"
copy .env.example .env       # then fill in MONGODB_URI etc.
uvicorn app.main:app --reload --port 8000
```

Health check: `GET http://127.0.0.1:8000/health`

## Test

```bash
pytest
```

## Layout

```
app/
├── main.py           FastAPI app, CORS, router registration
├── core/
│   ├── config.py      pydantic-settings — the only place env vars are read
│   └── db.py          Mongo (motor) client, lazy singleton
└── routes/
    └── health.py       liveness check
tests/
```
