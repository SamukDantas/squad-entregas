"""Modelos de dados para a camada de integração.

Re-exporta os modelos Pydantic definidos no backend para que
consumidores externos não dependam diretamente do pacote `app`.
"""

from app.models import HealthResponse

__all__ = ["HealthResponse"]
