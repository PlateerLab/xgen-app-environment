# API: FastAPI only

An app without a screen. Its routes are functions other systems call.
`backend/serve.py` (platform glue) hands `/api/*` to your FastAPI app in
`backend/main.py`. The platform runs it and gives it an address; opening that
address shows the API reference: every endpoint with its description,
parameters, request and response JSON examples and a curl line (also at
`/api/docs`).

```
backend/main.py          FastAPI app: add routes under /api/... (yours)
backend/serve.py         serving glue: /api/health, /api/openapi.json, the
                         reference page at / and /api/docs (leave it alone)
backend/apidocs.py       builds the reference page from the schema (leave it alone)
backend/xgen_llm.py      XGEN LLM package (written by the platform), leave it alone
backend/requirements.txt Python deps (pinned to what the sandbox already has)
```

Lifecycle (the platform runs these in this folder):

- install : pip install -r backend/requirements.txt
- command : uvicorn backend.serve:app --host 0.0.0.0 --port $PORT

There is no frontend and no build step.

Rules that matter:

- Keep `app = FastAPI()` in backend/main.py (serve.py imports it) and keep every
  route under /api/. `/api/health` and `/api/openapi.json` are reserved for the
  platform.
- Give every route a `summary=` and pydantic models for its input and output.
  The OpenAPI schema built from them is what the API's callers see when the
  user deploys the app as an API.
- The app is mounted under a path prefix, never at `/`. The platform strips the
  prefix before requests reach FastAPI; never set root_path. `XGEN_BASE_PATH`
  holds the absolute prefix if you ever need to print a link.
- Listen on 0.0.0.0 and `$PORT` (both already wired in `command`).
- Need a model inside the API? `from backend import xgen_llm`, then
  `await xgen_llm.ask(prompt)` in a route. It uses the LLMs registered in XGEN
  (this agent's model unless you pass `provider=` and `model=`); the keys stay
  in XGEN, never in the app.
- Adding a Python package: append to backend/requirements.txt.
