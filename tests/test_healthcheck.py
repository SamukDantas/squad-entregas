"""
Testes do endpoint GET /healthcheck contra o código real em main.py.

Cobertura:
  - Status code 200
  - Body JSON {"status": "ok"}
  - Content-Type application/json
  - Método HTTP correto (GET); métodos errados recebem 405
  - Não aceita parâmetros de query (não altera resposta)
  - Contrato de API conforme spec
"""

import json

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ── Caso feliz ────────────────────────────────────────────────────────

class TestHealthcheckHappyPath:
    """Valida o contrato completo do endpoint no caminho feliz."""

    def test_returns_200(self):
        """GET /healthcheck deve retornar HTTP 200."""
        response = client.get("/healthcheck")
        assert response.status_code == 200

    def test_returns_json_content_type(self):
        """Response deve ter Content-Type application/json."""
        response = client.get("/healthcheck")
        assert response.headers["content-type"] == "application/json"

    def test_body_status_ok(self):
        """Body deve conter exatamente {"status": "ok"}."""
        response = client.get("/healthcheck")
        assert response.json() == {"status": "ok"}

    def test_body_is_valid_json(self):
        """Body deve ser JSON parseável."""
        response = client.get("/healthcheck")
        #response.text já é parseável pelo TestClient, mas validamos
        parsed = json.loads(response.text)
        assert isinstance(parsed, dict)

    def test_body_has_only_status_key(self):
        """Body não deve conter chaves além de 'status'."""
        response = client.get("/healthcheck")
        assert set(response.json().keys()) == {"status"}


# ── Métodos HTTP incorretos ───────────────────────────────────────────

class TestHealthcheckMethodNotAllowed:
    """Métodos que não são GET devem retornar 405."""

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    def test_non_get_methods_return_405(self, method):
        """POST/PUT/PATCH/DELETE em /healthcheck → 405."""
        response = client.request(method, "/healthcheck")
        assert response.status_code == 405


# ── Casos de borda ───────────────────────────────────────────────────

class TestHealthcheckEdgeCases:
    """Casos de borda: parâmetros extras, trailing slash, body."""

    def test_with_trailing_slash(self):
        """GET /healthcheck/ (com barra final) — FastAPI pode redirecionar."""
        response = client.get("/healthcheck/")
        # FastAPI por padrão redireciona 307 para a rota sem barra
        # ou serve diretamente, dependendo da config. Aceitamos 200 ou 307.
        assert response.status_code in (200, 307)

    def test_with_query_params_ignored(self):
        """Query params extras não devem quebrar o endpoint."""
        response = client.get("/healthcheck?foo=bar&baz=123")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_response_without_body(self):
        """GET não deve exigir body — simples GET funciona."""
        response = client.get("/healthcheck")
        assert response.status_code == 200

    def test_response_status_value_is_string(self):
        """O valor de 'status' deve ser uma string, não int ou bool."""
        response = client.get("/healthcheck")
        body = response.json()
        assert isinstance(body["status"], str)

    def test_status_value_is_literal_ok(self):
        """O valor de 'status' deve ser exatamente 'ok' (case-sensitive)."""
        response = client.get("/healthcheck")
        body = response.json()
        assert body["status"] == "ok"
        assert body["status"] != "OK"
        assert body["status"] != "Ok"
