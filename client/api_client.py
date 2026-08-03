"""Cliente HTTP para consumo da Healthcheck API.

Usa httpx (mesma lib transitiva do TestClient do FastAPI) para
realizar chamadas HTTP ao backend.
"""

from __future__ import annotations

import httpx

from client.models import HealthResponse


class HealthcheckClient:
    """Cliente de integração para o endpoint de healthcheck.

    Parâmetros
    ----------
    base_url : str
        URL base do servidor FastAPI (ex.: ``http://localhost:8000``).
    timeout : float
        Timeout em segundos para cada requisição HTTP.
    """

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Método síncrono
    # ------------------------------------------------------------------
    def healthcheck(self) -> HealthResponse:
        """Chama ``GET /healthcheck`` e retorna um ``HealthResponse``.

        Levanta
        -------
        httpx.HTTPStatusError
            Se o servidor retornar um status HTTP de erro.
        httpx.ConnectError
            Se não for possível conectar ao servidor.
        """
        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
            response = client.get("/healthcheck")
            response.raise_for_status()
            return HealthResponse(**response.json())

    # ------------------------------------------------------------------
    # Método assíncrono
    # ------------------------------------------------------------------
    async def ahealthcheck(self) -> HealthResponse:
        """Versão assíncrona de :meth:`healthcheck`.

        Útil para integração com frameworks async (asyncio, etc.).
        """
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            response = await client.get("/healthcheck")
            response.raise_for_status()
            return HealthResponse(**response.json())

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def is_healthy(self) -> bool:
        """Retorna ``True`` se a API estiver saudável, ``False`` caso contrário."""
        try:
            result = self.healthcheck()
            return result.status == "healthy"
        except Exception:
            return False
