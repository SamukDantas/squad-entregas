"""
Testes de integração do endpoint GET /healthcheck via FastAPI TestClient.
Cobertura: status code 200/503, corpo JSON, campos obrigatórios,
formato de timestamp, ausência de dados sensíveis e mock de falha.
"""

import re
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


# ─── Contrato HTTP ───────────────────────────────────────────────────


class TestHealthcheckHTTP:
    """Valida o contrato HTTP do endpoint /healthcheck."""

    def test_get_returns_200(self):
        resposta = client.get("/healthcheck")
        assert resposta.status_code == 200, (
            f"Esperado 200, recebido {resposta.status_code}"
        )

    def test_returns_json_content_type(self):
        resposta = client.get("/healthcheck")
        assert "application/json" in resposta.headers["content-type"]

    def test_response_is_valid_json(self):
        resposta = client.get("/healthcheck")
        body = resposta.json()
        assert isinstance(body, dict)


# ─── Corpo da Resposta (200 OK) ──────────────────────────────────────


class TestHealthcheckBodyOK:
    """Valida o corpo da resposta quando o sistema está operacional."""

    def setUp(self):
        self.resposta = client.get("/healthcheck")
        self.body = self.resposta.json()

    def test_has_status_field(self):
        body = client.get("/healthcheck").json()
        assert "status" in body

    def test_status_ok(self):
        body = client.get("/healthcheck").json()
        assert body["status"] == "ok"

    def test_has_version_field(self):
        body = client.get("/healthcheck").json()
        assert "version" in body

    def test_version_is_string(self):
        body = client.get("/healthcheck").json()
        assert isinstance(body["version"], str)

    def test_version_not_empty(self):
        body = client.get("/healthcheck").json()
        assert len(body["version"]) > 0, "Versão não pode ser string vazia"

    def test_has_timestamp_field(self):
        body = client.get("/healthcheck").json()
        assert "timestamp" in body

    ISO_8601_UTC_RE = re.compile(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$"
    )

    def test_timestamp_format(self):
        body = client.get("/healthcheck").json()
        assert self.ISO_8601_UTC_RE.match(body["timestamp"]), (
            f"Timestamp '{body['timestamp']}' não é ISO 8601 UTC válido"
        )


# ─── Resposta 503 (Sistema Indisponível) ─────────────────────────────


class TestHealthcheckUnavailable:
    """Valida retorno 503 quando o sistema reporta falha."""

    def test_returns_503_when_unhealthy(self):
        with patch("healthcheck.get_health_status", return_value=False):
            resposta = client.get("/healthcheck")
            assert resposta.status_code == 503

    def test_body_status_error_when_unhealthy(self):
        with patch("healthcheck.get_health_status", return_value=False):
            body = client.get("/healthcheck").json()
            assert body["status"] == "error"

    def test_version_present_even_when_unhealthy(self):
        with patch("healthcheck.get_health_status", return_value=False):
            body = client.get("/healthcheck").json()
            assert "version" in body
            assert body["version"] == "1.0.0"

    def test_timestamp_present_when_unhealthy(self):
        with patch("healthcheck.get_health_status", return_value=False):
            body = client.get("/healthcheck").json()
            assert "timestamp" in body


# ─── Segurança ───────────────────────────────────────────────────────


class TestEndpointSecurity:
    """Garante que o endpoint não expõe informações sensíveis."""

    SENSITIVE_KEYS = {"password", "passwd", "secret", "token", "api_key",
                      "apikey", "access_token", "private_key", "db_password",
                      "credentials"}

    def test_no_sensitive_keys_in_response(self):
        body = client.get("/healthcheck").json()
        chaves_lower = {k.lower() for k in body.keys()}
        vazamento = chaves_lower & self.SENSITIVE_KEYS
        assert not vazamento, (
            f"Chaves sensíveis expostas: {vazamento}"
        )

    def test_no_env_vars_leaked(self):
        """Nenhuma variável de ambiente deve vazar no corpo da resposta."""
        body_str = str(client.get("/healthcheck").json()).lower()
        env_leaks = ["environ", "os.environ", "getenv"]
        for leak in env_leaks:
            assert leak not in body_str, (
                f"Possível vazamento de variável de ambiente: '{leak}'"
            )

    def test_method_not_allowed_for_post(self):
        """Apenas GET deve ser aceito — POST não deve funcionar."""
        resposta = client.post("/healthcheck")
        assert resposta.status_code in (405, 404), (
            f"POST deveria ser rejeitado, mas retornou {resposta.status_code}"
        )


# ─── Casos de Borda ──────────────────────────────────────────────────


class TestEdgeCases:
    """Testes de borda para cobrir cenários pouco comuns."""

    def test_multiple_calls_return_consistent_structure(self):
        """Chamadas consecutivas devem manter a mesma estrutura."""
        for _ in range(5):
            body = client.get("/healthcheck").json()
            assert set(body.keys()) == {"status", "version", "timestamp"}
            assert body["status"] == "ok"
            assert body["version"] == "1.0.0"

    def test_no_trailing_slash_variation(self):
        """Verifica comportamento com trailing slash."""
        # FastAPI pode ou não redirecionar — apenas valida que não quebra
        resposta = client.get("/healthcheck/")
        assert resposta.status_code in (200, 307, 404)
