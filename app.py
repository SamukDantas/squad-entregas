from fastapi import FastAPI
from fastapi.responses import JSONResponse

from healthcheck import build_healthcheck_response

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/healthcheck")
def healthcheck():
    data = build_healthcheck_response()
    status_code = 200 if data["status"] == "ok" else 503
    return JSONResponse(content=data, status_code=status_code)
