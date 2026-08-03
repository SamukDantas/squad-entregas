"""Camada de consumo da Healthcheck API.

Expondo o cliente e os modelos para uso externo.
"""

from client.api_client import HealthcheckClient
from client.models import HealthResponse

__all__ = ["HealthcheckClient", "HealthResponse"]
