"""Serving glue owned by the platform. Leave this file alone.

One process, one port, no screen. Everything under /api/ (and every WebSocket)
goes to your FastAPI app in backend/main.py, untouched. Put your routes there.

  /api/health          answered here (the platform's liveness probe)
  /api/openapi.json    answered here: your app's OpenAPI schema (the platform
                       reads it when the app is deployed as an API)
  /                    answered here: the API reference for a browser (every
                       endpoint with its description, parameters, request and
                       response JSON examples and a curl line — backend/apidocs.py),
                       JSON (the endpoint list) for anything else
  /api/docs            the same reference page, always HTML
  /api/**              backend.main:app

The platform mounts the whole thing under a path prefix and strips it before
requests arrive, so nothing here knows the prefix. Never set root_path.
"""

from starlette.responses import HTMLResponse, JSONResponse

from backend import apidocs
from backend.main import app as api

_HEALTH = JSONResponse({"ok": True})
_NOT_FOUND = JSONResponse({"error": "not found: every route of this API is under /api/"}, status_code=404)


def _schema():
    """The schema of backend/main.py's app, whatever its own openapi_url says.

    main.py turns its docs routes off (openapi_url=None) so the app does not
    serve them at its root, but the platform still needs the schema to list the
    endpoints of a deployed API. app.openapi() builds it regardless.
    """
    return api.openapi()


def _openapi():
    try:
        return JSONResponse(_schema())
    except Exception as exc:  # noqa: BLE001 - a broken schema must not take the app down
        return JSONResponse({"error": f"openapi schema unavailable: {exc}"}, status_code=500)


def _wants_document(scope) -> bool:
    headers = {k.lower(): v for k, v in (scope.get("headers") or [])}
    dest = headers.get(b"sec-fetch-dest", b"").decode("latin-1")
    if dest:
        # "iframe": the platform's app tab shows the app inside a frame — that is a person looking, too.
        return dest in ("document", "iframe", "frame")
    return "text/html" in headers.get(b"accept", b"").decode("latin-1")


def _docs():
    """The API reference page — what a person reads to call this API."""
    try:
        return HTMLResponse(apidocs.render(_schema()))
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": f"openapi schema unavailable: {exc}"}, status_code=500)


def _index(scope):
    """What opens at the app's address: the reference page for a person, the endpoint list for a program."""
    if _wants_document(scope):
        return _docs()
    try:
        schema = _schema()
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": f"openapi schema unavailable: {exc}"}, status_code=500)
    title = str((schema.get("info") or {}).get("title") or "api")
    return JSONResponse({"title": title, "endpoints": apidocs.summary(schema)})


async def app(scope, receive, send):
    if scope["type"] == "http":
        path = scope.get("path") or "/"
        method = scope.get("method")
        if path == "/api/health":
            await _HEALTH(scope, receive, send)
            return
        if path == "/api/openapi.json" and method in ("GET", "HEAD"):
            await _openapi()(scope, receive, send)
            return
        if path == "/api/docs" and method in ("GET", "HEAD"):
            await _docs()(scope, receive, send)
            return
        if path == "/" and method in ("GET", "HEAD"):
            await _index(scope)(scope, receive, send)
            return
        if not path.startswith("/api/"):
            await _NOT_FOUND(scope, receive, send)
            return
    await api(scope, receive, send)
