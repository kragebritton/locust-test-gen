# Locust Test Generator API

This FastAPI service generates Locust task skeletons from an OpenAPI specification. It produces a ready-to-edit `locustfile.py` that includes tasks for every discovered operation and placeholders for humans to wire together multi-step flows.

## Quickstart

1. Install dependencies with [uv](https://github.com/astral-sh/uv) (preferred) or your PEP 517 installer of choice:

   ```bash
   uv venv
   uv pip install .[dev]
   ```

2. Run the API:

   ```bash
   uv run uvicorn app.main:app --reload
   ```

3. Call the generator endpoint with a parsed OpenAPI document:

   ```bash
   curl -X POST http://localhost:8000/generate \
        -H "Content-Type: application/json" \
        -d @- <<'JSON'
   {
     "openapi": { "openapi": "3.0.0", "paths": {"/users": {"get": {"summary": "List users"}}}},
     "host": "https://api.example.com",
     "client_type": "fast_http",
     "user_class_name": "DemoUser",
     "task_weight": 2
   }
   JSON
   ```

The response contains a `locustfile` string you can save locally. Use the docstrings and TODO comments to thread together the payloads and responses needed for realistic scenarios.

## Design Notes

- **Jinja2 templating:** Locustfiles are rendered from templates to keep formatting consistent and make it easier to extend.
- **Client flexibility:** Generate users that inherit from `FastHttpUser` or `HttpUser` to match your preferred HTTP backend.
- **Operation coverage:** Every operation in the `paths` section becomes a task with sensible names derived from `operationId`, `summary`, or the HTTP verb and path.
- **Human-in-the-loop:** Payload generation and cross-task data sharing are left as commented placeholders so you can incorporate domain knowledge (e.g., passing IDs from create calls into subsequent reads).

## Health Check

A lightweight `GET /health` endpoint is included for readiness probes.
