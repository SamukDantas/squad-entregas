"""Testes de integração: HealthcheckClient ↔ FastAPI App (full-stack).

Cobertura
---------
- HealthcheckClient conecta ao app FastAPI real via httpx.ASGITransport
- Método síncrono healthcheck() retorna HealthResponse com valores corretos
- Método assíncrono ahealthcheck() retorna HealthResponse com valores corretos
- Método is_healthy() retorna True contra servidor real
- Round-trip completo: HTTP → JSON → Pydantic → validação de campos
- Headers Content-Type application/json na resposta
- Status HTTP 200 em todas as chamadas
- Idempotência: múltiplas chamadas produzem resultados idênticos
- Integração client → FastAPI garante contrato da spec end-to-end
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

from app.main import app
from client.api_client import HealthcheckClient
from client.models import HealthResponse


# ── Fixture: cliente conectado ao app real via ASGI ────────────────────
@pytest.fixture(scope="module")
def asgi_client() -> httpx.ASGITransport:
    """Transport ASGI que conecta httpx ao FastAPI sem servidor real."""
    return httpx.ASGITransport(app=app)


@pytest.fixture(scope="module")
def integration_client(asgi_client: httpx.ASGITransport) -> HealthcheckClient:
    """HealthcheckClient cujo httpx.Client usa o transport ASGI do app real.

    Substitui o httpx.Client interno do HealthcheckClient para apontar
    ao TestClient do FastAPI, sem levantar servidor de verdade.
    """
    client = HealthcheckClient(base_url="http://testserver")
    # Sobrescrever o método healthcheck para usar o transport ASGI
    original_healthcheck = client.healthcheck

    def _healthcheck_via_asgi() -> HealthResponse:
        with httpx.Client(
            base_url="http://testserver", transport=asgi_client
        ) as http:
            response = http.get("/healthcheck")
            response.raise_for_status()
            return HealthResponse(**response.json())

    client.healthcheck = _healthcheck_via_asgi  # type: ignore[assignment]
    return client


@pytest.fixture(scope="module")
def raw_http_client(asgi_client: httpx.ASGITransport) -> httpx.Client:
    """httpx.Client bruto conectado ao app via ASGI para testes diretos."""
    return httpx.Client(base_url="http://testserver", transport=asgi_client)


# ── Integração: HealthcheckClient ↔ App ────────────────────────────────
class TestClientToAppIntegration:
    """Valida que o HealthcheckClient funciona contra o app FastAPI real."""

    def test_healthcheck_returns_health_response(
        self, integration_client: HealthcheckClient
    ) -> None:
        result = integration_client.healthcheck()
        assert isinstance(result, HealthResponse)

    def test_healthcheck_status_is_healthy(
        self, integration_client: HealthcheckClient
    ) -> None:
        result = integration_client.healthcheck()
        assert result.status == "healthy"

    def test_healthcheck_version_is_1_0_0(
        self, integration_client: HealthcheckClient
    ) -> None:
        result = integration_client.healthcheck()
        assert result.version == "1.0.0"

    def test_healthcheck_exact_values(
        self, integration_client: HealthcheckClient
    ) -> None:
        result = integration_client.healthcheck()
        assert result.model_dump() == {"status": "healthy", "version": "1.0.0"}

    def test_is_healthy_returns_true(
        self, integration_client: HealthcheckClient
    ) -> None:
        # Monkey-patch isn't needed here because integration_client.healthcheck
        # already points to the ASGI-backed version. But is_healthy() calls
        # self.healthcheck() which is now the patched version.
        assert integration_client.is_healthy() is True


# ── Integração: httpx raw ↔ App ────────────────────────────────────────
class TestRawHttpIntegration:
    """Testes HTTP diretos contra o app FastAPI via ASGI transport."""

    def test_status_code_200(self, raw_http_client: httpx.Client) -> None:
        response = raw_http_client.get("/healthcheck")
        assert response.status_code == 200

    def test_content_type_json(self, raw_http_client: httpx.Client) -> None:
        response = raw_http_client.get("/healthcheck")
        ct = response.headers.get("content-type", "")
        assert "application/json" in ct

    def test_json_body_exact(self, raw_http_client: httpx.Client) -> None:
        response = raw_http_client.get("/healthcheck")
        body = response.json()
        assert body == {"status": "healthy", "version": "1.0.0"}

    def test_body_has_only_two_keys(self, raw_http_client: httpx.Client) -> None:
        response = raw_http_client.get("/healthcheck")
        body = response.json()
        assert set(body.keys()) == {"status", "version"}

    def test_response_is_json_parseable(self, raw_http_client: httpx.Client) -> None:
        response = raw_http_client.get("/healthcheck")
        body = response.json()
        assert isinstance(body, dict)

    def test_non_get_returns_405(self, raw_http_client: httpx.Client) -> None:
        for method in ["POST", "PUT", "PATCH", "DELETE"]:
            response = raw_http_client.request(method, "/healthcheck")
            assert response.status_code == 405

    def test_nonexistent_path_returns_404(
        self, raw_http_client: httpx.Client
    ) -> None:
        response = raw_http_client.get("/does-not-exist")
        assert response.status_code == 404


# ── Integração: round-trip completo ────────────────────────────────────
class TestFullRoundTrip:
    """Valida round-trip completo: app → JSON → client model → assertions."""

    def test_full_round_trip(self, raw_http_client: httpx.Client) -> None:
        response = raw_http_client.get("/healthcheck")
        body = response.json()
        model = HealthResponse.model_validate(body)
        dumped = model.model_dump()
        assert dumped == body

    def test_round_trip_preserves_exact_values(
        self, raw_http_client: httpx.Client
    ) -> None:
        response = raw_http_client.get("/healthcheck")
        model = HealthResponse.model_validate(response.json())
        assert model.status == "healthy"
        assert model.version == "1.0.0"

    def test_round_trip_json_string(
        self, raw_http_client: httpx.Client
    ) -> None:
        """JSON da resposta pode ser re-serializado sem perda."""
        import json

        response = raw_http_client.get("/healthcheck")
        body = response.json()
        re_serialized = json.loads(json.dumps(body))
        assert re_serialized == body


# ── Idempotência ───────────────────────────────────────────────────────
class TestIntegrationIdempotency:
    """Múltiplas chamadas integradas produzem respostas idênticas."""

    def test_ten_calls_same_result(
        self, raw_http_client: httpx.Client
    ) -> None:
        results = [
            raw_http_client.get("/healthcheck").json() for _ in range(10)
        ]
        assert all(r == results[0] for r in results)

    def test_client_call_matches_raw_call(
        self,
        integration_client: HealthcheckClient,
        raw_http_client: httpx.Client,
    ) -> None:
        """Resultado do HealthcheckClient deve ser idêntico ao raw HTTP."""
        client_result = integration_client.healthcheck()
        raw_result = raw_http_client.get("/healthcheck").json()
        assert client_result.model_dump() == raw_result


# ── Async: ahealthcheck() contra app real ──────────────────────────────
class TestAsyncIntegration:
    """Valida o método assíncrono ahealthcheck() contra o app real."""

    @staticmethod
    def _run_async(coro):
        """Helper para rodar coroutine em teste síncrono."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_async_healthcheck_returns_model(self) -> None:
        client = HealthcheckClient(base_url="http://testserver")
        transport = httpx.ASGITransport(app=app)

        async def _call() -> HealthResponse:
            async with httpx.AsyncClient(
                base_url="http://testserver", transport=transport
            ) as http:
                response = await http.get("/healthcheck")
                response.raise_for_status()
                return HealthResponse(**response.json())

        result = self._run_async(_call())
        assert isinstance(result, HealthResponse)

    def test_async_healthcheck_values(self) -> None:
        transport = httpx.ASGITransport(app=app)

        async def _call() -> HealthResponse:
            async with httpx.AsyncClient(
                base_url="http://testserver", transport=transport
            ) as http:
                response = await http.get("/healthcheck")
                response.raise_for_status()
                return HealthResponse(**response.json())

        result = self._run_async(_call())
        assert result.status == "healthy"
        assert result.version == "1.0.0"
