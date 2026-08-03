from fastapi import APIRouter

from app.models import HealthResponse

router = APIRouter()


@router.get("/healthcheck", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    """Verifica saúde da API retornando status e versão fixos."""
    return HealthResponse()
