"""Serving glue owned by the platform — leave this file alone.

One process, one port. This ASGI app serves the built React frontend from
frontend/dist and hands everything under /api/ (and every WebSocket) to your
FastAPI app in backend/main.py, untouched. Put your routes there.

  /api/health          answered here (the platform's liveness probe)
  /api/openapi.json    answered here: your FastAPI app's OpenAPI schema (the
                       platform reads it when the app is deployed as an API)
  /api/docs            answered here: the API reference page a person reads
                       (every endpoint with description, parameters, request and
                       response JSON examples, a curl line — backend/apidocs.py)
  /api/**              backend.main:app
  /assets/**, /**      files from frontend/dist; index.html for page navigations
                       (client-side routing)

The platform mounts the whole thing under a path prefix and strips it before
requests arrive, so nothing here knows the prefix and the frontend uses
relative URLs. Never set root_path.
"""

from pathlib import Path

from starlette.responses import FileResponse, HTMLResponse, JSONResponse

from backend import apidocs
from backend.main import app as api

ROOT = Path(__file__).resolve().parent.parent
DIST = (ROOT / "frontend" / "dist").resolve()
INDEX = DIST / "index.html"

_HEALTH = JSONResponse({"ok": True})


def _openapi():
    """The schema of backend/main.py's app, whatever its own openapi_url says.

    main.py disables the docs routes (openapi_url=None) so the app does not serve
    them at its root, but the platform still needs the schema to list the endpoints
    of a deployed API. app.openapi() builds it regardless of the setting.
    """
    try:
        return JSONResponse(api.openapi())
    except Exception as exc:  # noqa: BLE001 — a broken schema must not take the app down
        return JSONResponse({"error": f"openapi schema unavailable: {exc}"}, status_code=500)


def _docs():
    """The API reference page — what a person reads to call this API."""
    try:
        return HTMLResponse(apidocs.render(api.openapi()))
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": f"openapi schema unavailable: {exc}"}, status_code=500)


_NOT_BUILT = JSONResponse(
    {"error": "frontend is not built yet — run: npm --prefix frontend run build"},
    status_code=503,
)
_NOT_FOUND = JSONResponse({"error": "not found"}, status_code=404)


def _dist_file(path: str):
    """The file inside dist/ this path names, or None."""
    rel = path.lstrip("/")
    if not rel:
        return None
    candidate = (DIST / rel).resolve()
    if candidate.is_file() and candidate.is_relative_to(DIST):
        return candidate
    return None


def _wants_document(scope) -> bool:
    """Is this a browser opening a page, rather than a fetch()?

    It decides what an unknown path gets back. A page navigation gets index.html
    so client-side routing works. A fetch gets a 404 it can read — returning the
    HTML shell instead turns a wrong URL into "Unexpected token '<', "<!doctype"
    is not valid JSON", which hides the actual mistake.
    """
    headers = {k.lower(): v for k, v in (scope.get("headers") or [])}
    dest = headers.get(b"sec-fetch-dest", b"").decode("latin-1")
    if dest:
        return dest == "document"
    return "text/html" in headers.get(b"accept", b"").decode("latin-1")


async def app(scope, receive, send):
    if scope["type"] == "http":
        path = scope.get("path") or "/"
        if path == "/api/health":
            await _HEALTH(scope, receive, send)
            return
        if path == "/api/openapi.json" and scope.get("method") in ("GET", "HEAD"):
            await _openapi()(scope, receive, send)
            return
        if path == "/api/docs" and scope.get("method") in ("GET", "HEAD"):
            await _docs()(scope, receive, send)
            return
        if not path.startswith("/api/") and scope.get("method") in ("GET", "HEAD"):
            target = _dist_file(path)
            if target is not None:
                await FileResponse(target)(scope, receive, send)
                return
            if not INDEX.is_file():
                await _NOT_BUILT(scope, receive, send)
                return
            if path != "/" and not _wants_document(scope):
                await _NOT_FOUND(scope, receive, send)
                return
            await FileResponse(INDEX)(scope, receive, send)
            return
    await api(scope, receive, send)
