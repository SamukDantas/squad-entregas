from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Modelo de resposta do endpoint de healthcheck."""

    status: str = "healthy"
    version: str = "1.0.0"
