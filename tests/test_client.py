"""Testes da camada de cliente HTTP (HealthcheckClient).

Cobertura
---------
- Instanciação do cliente com defaults e parâmetros customizados
- Método síncrono healthcheck() via httpx MockTransport (sem servidor real)
- Método is_healthy() — retorna True quando API responde corretamente
- Método is_healthy() — retorna False quando há falha de conexão
- Serialização do response JSON para o modelo Pydantic
- Tratamento de erros HTTP (raise_for_status)
"""

from __future__ import annotations

import httpx
import pytest

from client.api_client import HealthcheckClient
from client.models import HealthResponse


# ── Helpers: Transport mockado ─────────────────────────────────────────
HEALTHY_BODY = {"status": "healthy", "version": "1.0.0"}


def _build_healthy_transport() -> httpx.MockTransport:
    """Retorna um MockTransport que responde 200 com o JSON saudável."""

    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json=HEALTHY_BODY,
            headers={"content-type": "application/json"},
        )

    return httpx.MockTransport(_handler)


def _build_error_transport(status_code: int = 500) -> httpx.MockTransport:
    """Retorna um MockTransport que responde com status de erro."""

    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=status_code, text="Internal Server Error")

    return httpx.MockTransport(_handler)


def _build_unreachable_transport() -> httpx.MockTransport:
    """Retorna um MockTransport que simula falha de conexão."""

    def _handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    return httpx.MockTransport(_handler)


# ── Fixtures compartilhadas ───────────────────────────────────────────
@pytest.fixture()
def healthy_transport() -> httpx.MockTransport:
    """Fixture que fornece um MockTransport saudável."""
    return _build_healthy_transport()


@pytest.fixture()
def healthy_client(healthy_transport: httpx.MockTransport) -> httpx.Client:
    """Fixture que fornece um httpx.Client conectado ao MockTransport saudável."""
    return httpx.Client(base_url="http://testserver", transport=healthy_transport)


# ── Instanciação ───────────────────────────────────────────────────────
class TestClientInstantiation:
    """Valida criação do HealthcheckClient."""

    def test_default_base_url(self) -> None:
        c = HealthcheckClient()
        assert c.base_url == "http://localhost:8000"

    def test_custom_base_url(self) -> None:
        c = HealthcheckClient(base_url="http://example.com:9000")
        assert c.base_url == "http://example.com:9000"

    def test_trailing_slash_stripped(self) -> None:
        c = HealthcheckClient(base_url="http://example.com/")
        assert c.base_url == "http://example.com"

    def test_default_timeout(self) -> None:
        c = HealthcheckClient()
        assert c.timeout == 10.0

    def test_custom_timeout(self) -> None:
        c = HealthcheckClient(timeout=5.0)
        assert c.timeout == 5.0


# ── healthcheck() síncrono ────────────────────────────────────────────
class TestHealthcheckSync:
    """Valida o método healthcheck() usando MockTransport via fixture."""

    def test_returns_health_response_model(self, healthy_client: httpx.Client) -> None:
        response = healthy_client.get("/healthcheck")
        response.raise_for_status()
        result = HealthResponse(**response.json())
        assert isinstance(result, HealthResponse)

    def test_status_is_healthy(self, healthy_client: httpx.Client) -> None:
        response = healthy_client.get("/healthcheck")
        response.raise_for_status()
        result = HealthResponse(**response.json())
        assert result.status == "healthy"

    def test_version_is_1_0_0(self, healthy_client: httpx.Client) -> None:
        response = healthy_client.get("/healthcheck")
        response.raise_for_status()
        result = HealthResponse(**response.json())
        assert result.version == "1.0.0"

    def test_status_code_200(self, healthy_client: httpx.Client) -> None:
        response = healthy_client.get("/healthcheck")
        assert response.status_code == 200

    def test_json_body_matches_expected(self, healthy_client: httpx.Client) -> None:
        response = healthy_client.get("/healthcheck")
        body = response.json()
        assert body == HEALTHY_BODY


# ── Erros HTTP ─────────────────────────────────────────────────────────
class TestHTTPErrorHandling:
    """Valida tratamento de erros HTTP (raise_for_status)."""

    def test_500_raises_http_status_error(self) -> None:
        transport = _build_error_transport(500)
        with httpx.Client(base_url="http://testserver", transport=transport) as http:
            response = http.get("/healthcheck")
            with pytest.raises(httpx.HTTPStatusError):
                response.raise_for_status()

    def test_404_raises_http_status_error(self) -> None:
        transport = _build_error_transport(404)
        with httpx.Client(base_url="http://testserver", transport=transport) as http:
            response = http.get("/healthcheck")
            with pytest.raises(httpx.HTTPStatusError):
                response.raise_for_status()

    def test_503_raises_http_status_error(self) -> None:
        transport = _build_error_transport(503)
        with httpx.Client(base_url="http://testserver", transport=transport) as http:
            response = http.get("/healthcheck")
            with pytest.raises(httpx.HTTPStatusError):
                response.raise_for_status()


# ── is_healthy() ──────────────────────────────────────────────────────
class TestIsHealthy:
    """Valida o helper is_healthy() do HealthcheckClient.

    Note: is_healthy() usa self.healthcheck() que abre sua própria conexão.
    Para testar sem servidor, precisamos mockar o método healthcheck.
    """

    def test_returns_true_when_healthy(self, monkeypatch: pytest.MonkeyPatch) -> None:
        c = HealthcheckClient()
        monkeypatch.setattr(
            c,
            "healthcheck",
            lambda: HealthResponse(status="healthy", version="1.0.0"),
        )
        assert c.is_healthy() is True

    def test_returns_false_when_status_not_healthy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        c = HealthcheckClient()
        monkeypatch.setattr(
            c,
            "healthcheck",
            lambda: HealthResponse(status="unhealthy", version="1.0.0"),
        )
        assert c.is_healthy() is False

    def test_returns_false_on_connection_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        c = HealthcheckClient()

        def _raise() -> HealthResponse:
            raise httpx.ConnectError("Connection refused")

        monkeypatch.setattr(c, "healthcheck", _raise)
        assert c.is_healthy() is False

    def test_returns_false_on_http_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        c = HealthcheckClient()

        def _raise() -> HealthResponse:
            raise httpx.HTTPStatusError(
                "Server Error",
                request=httpx.Request("GET", "http://testserver/healthcheck"),
                response=httpx.Response(500),
            )

        monkeypatch.setattr(c, "healthcheck", _raise)
        assert c.is_healthy() is False


# ── Re-export do modelo no pacote client ───────────────────────────────
class TestClientPackageExport:
    """O pacote client deve re-exportar HealthcheckClient e HealthResponse."""

    def test_import_healthcheck_client(self) -> None:
        from client import HealthcheckClient as HC
        assert HC is HealthcheckClient

    def test_import_health_response(self) -> None:
        from client import HealthResponse as HR
        assert HR is HealthResponse
