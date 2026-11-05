# App: FastAPI + React

One process serves everything: `backend/serve.py` (platform glue) serves the
built React app from `frontend/dist` and hands `/api/*` to your FastAPI app in
`backend/main.py`. The platform runs it and gives it an address.

```
backend/main.py          FastAPI app — add routes under /api/… (yours)
backend/serve.py         serving glue: dist/ + /api/health + /api/openapi.json + /api/docs — leave it alone
backend/apidocs.py       the API reference page /api/docs shows (built from the schema) — leave it alone
backend/xgen_llm.py      XGEN LLM package (written by the platform) — leave it alone
backend/requirements.txt Python deps (pinned to what the sandbox already has)
frontend/src/App.jsx     React UI — calls the API with relative paths ('api/…')
frontend/src/api.js      calls the API and returns the parsed body
```

Lifecycle (the platform runs these in this folder):

- install : pip install -r backend/requirements.txt && npm --prefix frontend ci
- build   : npm --prefix frontend run build         (every publish)
- command : uvicorn backend.serve:app --host 0.0.0.0 --port $PORT

Rules that matter:

- The app is mounted under a path prefix, never at `/`. The platform strips
  the prefix before requests reach FastAPI, so keep every URL in the frontend
  relative (`api/items`, `./logo.png`) and never set root_path. `XGEN_BASE_PATH`
  holds the absolute prefix if you ever need to print a link.
- Listen on 0.0.0.0 and `$PORT` (both already wired in `command`).
- Keep `app = FastAPI()` in backend/main.py (serve.py imports it) and keep every
  route under /api/. `/api/health`, `/api/openapi.json` and `/api/docs` are reserved for the
  platform (the second one is your app's OpenAPI schema, used when the app is
  deployed as an API).
- `api('api/items')` already performs the request and returns the parsed body.
  Never write `fetch(api(...))` — that fetches the string "[object Promise]".
- An unknown path returns index.html for a page navigation (client-side routing)
  and a JSON 404 for a fetch, so a wrong URL reads as 404 instead of HTML.
- Need a model inside the app? `from backend import xgen_llm`, then
  `await xgen_llm.ask(prompt)` in a backend route (the page calls that route).
  It uses the LLMs registered in XGEN — this agent's model unless you pass
  `provider=` and `model=` — and the keys stay in XGEN, never in the app.
  One call writes at most max_tokens; split big work into parts (AppGuide('llm')).
- Adding a Python package: append to backend/requirements.txt.
  Adding an npm package: `npm --prefix frontend install <pkg>` (needs network).
