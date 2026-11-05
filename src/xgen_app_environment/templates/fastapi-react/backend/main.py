"""FastAPI backend — your API. Add routes here, all under /api/.

backend/serve.py (platform glue, leave it alone) serves the built React app and
answers /api/health and /api/openapi.json (your schema); everything else under
/api/ comes here unchanged. The whole
app is mounted under a path prefix the platform strips, so routes are written as
if the app lived at "/" and the frontend calls them with RELATIVE paths
("api/…"). Never set root_path. XGEN_BASE_PATH holds the absolute prefix if you
ever need to print a shareable link.
"""

from fastapi import FastAPI

app = FastAPI(title="app", docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/api/example")
def example():
    return {
        "message": "Hello from FastAPI",
        "items": [
            {"id": 1, "name": "first", "value": 12},
            {"id": 2, "name": "second", "value": 7},
        ],
    }
