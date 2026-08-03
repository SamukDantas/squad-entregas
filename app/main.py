from fastapi import FastAPI

from app.models import HealthResponse

app = FastAPI(title="Healthcheck API", version="1.0.0")


@app.get("/healthcheck", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    """Verifica saúde da API retornando status e versão fixos."""
    return HealthResponse()
