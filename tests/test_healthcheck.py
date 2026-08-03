"""Testes do endpoint GET /healthcheck — contrato da API.

Cobertura
---------
- Status HTTP 200
- Corpo JSON com campos status e version
- Content-Type application/json
- Método HTTP: apenas GET é permitido (POST, PUT, PATCH, DELETE devem retornar 405)
- Headers de resposta não contêm dados sensíveis
- Resposta é idêntica em chamadas consecutivas (determinismo)
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Status Code ────────────────────────────────────────────────────────
class TestStatusCode:
    """Valida que o endpoint retorna HTTP 200."""

    def test_returns_200(self) -> None:
        response = client.get("/healthcheck")
        assert response.status_code == 200

    def test_returns_200_multiple_calls(self) -> None:
        """Determinismo: múltiplas chamadas sempre retornam 200."""
        for _ in range(5):
            assert client.get("/healthcheck").status_code == 200


# ── Corpo JSON ─────────────────────────────────────────────────────────
class TestResponseBody:
    """Valida o contrato exato do corpo de resposta."""

    EXPECTED_BODY = {"status": "healthy", "version": "1.0.0"}

    def test_exact_json_body(self) -> None:
        response = client.get("/healthcheck")
        assert response.json() == self.EXPECTED_BODY

    def test_body_has_status_key(self) -> None:
        body = client.get("/healthcheck").json()
        assert "status" in body

    def test_body_has_version_key(self) -> None:
        body = client.get("/healthcheck").json()
        assert "version" in body

    def test_body_has_exactly_two_keys(self) -> None:
        """Nenhum campo extra deve ser exposto."""
        body = client.get("/healthcheck").json()
        assert set(body.keys()) == {"status", "version"}

    def test_status_value_is_healthy(self) -> None:
        body = client.get("/healthcheck").json()
        assert body["status"] == "healthy"

    def test_version_value_is_1_0_0(self) -> None:
        body = client.get("/healthcheck").json()
        assert body["version"] == "1.0.0"

    def test_version_format_is_semver(self) -> None:
        """Versão deve seguir o padrão X.Y.Z."""
        body = client.get("/healthcheck").json()
        parts = body["version"].split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)


# ── Content-Type ───────────────────────────────────────────────────────
class TestContentType:
    """Valida header Content-Type."""

    def test_content_type_is_json(self) -> None:
        response = client.get("/healthcheck")
        assert "application/json" in response.headers["content-type"]

    def test_content_type_header_exists(self) -> None:
        response = client.get("/healthcheck")
        assert "content-type" in response.headers


# ── Métodos HTTP ───────────────────────────────────────────────────────
class TestHTTPMethods:
    """O endpoint aceita apenas GET. Demais métodos devem retornar 405."""

    @pytest.mark.parametrize(
        "method",
        ["post", "put", "patch", "delete"],
    )
    def test_non_get_methods_return_405(self, method: str) -> None:
        response = client.request(method, "/healthcheck")
        assert response.status_code == 405


# ── Determinismo ───────────────────────────────────────────────────────
class TestDeterminism:
    """Duas chamadas consecutivas produzem respostas idênticas."""

    def test_responses_are_identical(self) -> None:
        body1 = client.get("/healthcheck").json()
        body2 = client.get("/healthcheck").json()
        assert body1 == body2

    def test_status_always_healthy(self) -> None:
        for _ in range(3):
            assert client.get("/healthcheck").json()["status"] == "healthy"

    def test_version_always_1_0_0(self) -> None:
        for _ in range(3):
            assert client.get("/healthcheck").json()["version"] == "1.0.0"
