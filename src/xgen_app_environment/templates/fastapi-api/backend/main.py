"""FastAPI backend: your API. Every route under /api/ is a function other systems call.

backend/serve.py (platform glue, leave it alone) answers /api/health and
/api/openapi.json and shows the API reference (every endpoint with its
description, parameters and request/response JSON examples) at the app's
address and at /api/docs;
everything else under /api/ comes here unchanged. The whole app is mounted under
a path prefix the platform strips, so routes are written as if the app lived at
"/". Never set root_path.

Give every route a summary= and a description= (or a docstring) and pydantic
models with Field(description=...) for what it takes and returns. The reference
page is built from them, so what you write there is what the API's callers read.
"""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="api", docs_url=None, redoc_url=None, openapi_url=None)


class AddIn(BaseModel):
    a: float
    b: float


class AddOut(BaseModel):
    result: float


@app.post("/api/add", summary="Add two numbers", response_model=AddOut)
def add(body: AddIn) -> AddOut:
    return AddOut(result=body.a + body.b)
