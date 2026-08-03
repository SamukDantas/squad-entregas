"""
Testes unitários do módulo healthcheck.py
Cobertura: validação da função build_healthcheck_response, constantes,
formato de timestamp, campos obrigatórios e ausência de dados sensíveis.
"""

import re
from unittest.mock import patch

from healthcheck import VERSION, build_healthcheck_response, get_health_status


# ─── get_health_status ───────────────────────────────────────────────


class TestGetHealthStatus:
    """Valida o comportamento da função de verificação de status."""

    def test_returns_boolean(self):
        resultado = get_health_status()
        assert isinstance(resultado, bool)

    def test_current_implementation_returns_true(self):
        """Na implementação atual, o sistema sempre retorna saudável."""
        assert get_health_status() is True


# ─── build_healthcheck_response ──────────────────────────────────────


class TestBuildHealthcheckResponse:
    """Valida a estrutura e contratos da resposta de healthcheck."""

    def test_returns_dict(self):
        resposta = build_healthcheck_response()
        assert isinstance(resposta, dict)

    def test_has_required_fields(self):
        resposta = build_healthcheck_response()
        campos_obrigatorios = {"status", "version", "timestamp"}
        assert campos_obrigatorios.issubset(resposta.keys()), (
            f"Faltam campos: {campos_obrigatorios - resposta.keys()}"
        )

    def test_status_ok_when_healthy(self):
        with patch("healthcheck.get_health_status", return_value=True):
            resposta = build_healthcheck_response()
            assert resposta["status"] == "ok"

    def test_status_error_when_unhealthy(self):
        with patch("healthcheck.get_health_status", return_value=False):
            resposta = build_healthcheck_response()
            assert resposta["status"] == "error"

    def test_version_matches_constant(self):
        resposta = build_healthcheck_response()
        assert resposta["version"] == VERSION

    def test_version_is_1_0_0(self):
        assert VERSION == "1.0.0"

    def test_version_is_string(self):
        resposta = build_healthcheck_response()
        assert isinstance(resposta["version"], str)


# ─── Timestamp ───────────────────────────────────────────────────────


class TestTimestamp:
    """Valida formato ISO 8601 com sufixo Z (UTC)."""

    # ISO 8601 com Z: 2024-01-15T10:30:00Z ou com milissegundos 2024-01-15T10:30:00.123456Z
    ISO_8601_UTC_RE = re.compile(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$"
    )

    def test_timestamp_ends_with_z(self):
        resposta = build_healthcheck_response()
        assert resposta["timestamp"].endswith("Z"), (
            "Timestamp deve terminar com 'Z' (UTC)"
        )

    def test_timestamp_matches_iso8601_utc(self):
        resposta = build_healthcheck_response()
        assert self.ISO_8601_UTC_RE.match(resposta["timestamp"]), (
            f"Timestamp '{resposta['timestamp']}' não é ISO 8601 UTC válido"
        )

    def test_timestamp_is_string(self):
        resposta = build_healthcheck_response()
        assert isinstance(resposta["timestamp"], str)


# ─── Segurança ───────────────────────────────────────────────────────


class TestSecurity:
    """Garante que não há exposição de informações sensíveis."""

    SENSITIVE_KEYS = {"password", "passwd", "secret", "token", "api_key",
                      "apikey", "access_token", "private_key", "db_password",
                      "credentials"}

    def test_no_sensitive_keys(self):
        resposta = build_healthcheck_response()
        chaves_lower = {k.lower() for k in resposta.keys()}
        vazamento = chaves_lower & self.SENSITIVE_KEYS
        assert not vazamento, (
            f"Chaves sensíveis expostas na resposta: {vazamento}"
        )

    def test_no_values_contain_password_pattern(self):
        resposta = build_healthcheck_response()
        for chave, valor in resposta.items():
            valor_str = str(valor).lower()
            assert "password" not in valor_str, (
                f"Campo '{chave}' contém referência a senha"
            )
            assert "secret" not in valor_str, (
                f"Campo '{chave}' contém referência a segredo"
            )
