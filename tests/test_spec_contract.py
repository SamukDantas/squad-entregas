"""
Testes de contrato da spec — validam os critérios de aceite EXATOS
da especificação técnica contra a implementação real.

Cobertura:
  - Resposta 200 com body exato (status=ok, version, timestamp)
  - Resposta 503 com body exato (status=error, version, timestamp)
  - Ausência de campos extras além dos 3 especificados
  - Status é enum restrito ("ok" ou "error")
  - Timestamp é ISO 8601 com Z e está fresco (janela de 5s)
  - Versão segue semântica x.y.z
  - Método HTTP restrito a GET
  - Nenhuma informação sensível (senhas, chaves, env vars)
  - Módulo healthcheck.py é independente de framework
"""

import re
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import app
from healthcheck import (
    VERSION,
    build_healthcheck_response,
    get_health_status,
)

client = TestClient(app)

# ─── Helpers ──────────────────────────────────────────────────────────

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$")
ISO8601_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$"
)
VALID_STATUSES = {"ok", "error"}

# ─── Spec Criterion: GET /healthcheck retorna 200 OK ─────────────────


class TestSpec200OK:
    """A spec define: 'Deve retornar código 200 quando o sistema estiver operacional'."""

    def test_200_status_code(self):
        r = client.get("/healthcheck")
        assert r.status_code == 200

    def test_response_is_json(self):
        r = client.get("/healthcheck")
        assert "application/json" in r.headers["content-type"]

    def test_body_has_exactly_three_fields(self):
        """Spec só define status, version, timestamp — nenhum campo extra."""
        body = client.get("/healthcheck").json()
        assert set(body.keys()) == {"status", "version", "timestamp"}, (
            f"Campos extras ou faltantes: {set(body.keys())} "
            f"vs esperado {{'status', 'version', 'timestamp'}}"
        )

    def test_status_value_is_ok(self):
        body = client.get("/healthcheck").json()
        assert body["status"] == "ok"

    def test_version_matches_spec_example(self):
        """Spec mostra version '1.0.0' no exemplo de resposta."""
        body = client.get("/healthcheck").json()
        assert body["version"] == "1.0.0"

    def test_timestamp_is_iso8601_utc_with_z(self):
        """Spec define timestamp com sufixo Z (UTC)."""
        body = client.get("/healthcheck").json()
        assert ISO8601_UTC_RE.match(body["timestamp"]), (
            f"Timestamp '{body['timestamp']}' não segue ISO 8601 com Z"
        )

    def test_timestamp_is_fresh(self):
        """Timestamp deve estar dentro de 5 segundos do momento atual."""
        body = client.get("/healthcheck").json()
        ts_str = body["timestamp"].replace("Z", "+00:00")
        ts = datetime.fromisoformat(ts_str)
        now = datetime.now(timezone.utc)
        diff = abs((now - ts).total_seconds())
        assert diff < 5, (
            f"Timestamp distante demais do agora: {diff:.1f}s"
        )


# ─── Spec Criterion: Resposta 503 quando indisponível ─────────────────


class TestSpec503Unavailable:
    """A spec define: 'Resposta 503 Service Unavailable quando sistema indisponível'."""

    def test_503_status_code_when_unhealthy(self):
        with patch("healthcheck.get_health_status", return_value=False):
            r = client.get("/healthcheck")
            assert r.status_code == 503

    def test_503_body_has_status_error(self):
        with patch("healthcheck.get_health_status", return_value=False):
            body = client.get("/healthcheck").json()
            assert body["status"] == "error"

    def test_503_body_has_exactly_three_fields(self):
        """Mesmo no 503, só os 3 campos da spec."""
        with patch("healthcheck.get_health_status", return_value=False):
            body = client.get("/healthcheck").json()
            assert set(body.keys()) == {"status", "version", "timestamp"}

    def test_503_version_still_present(self):
        with patch("healthcheck.get_health_status", return_value=False):
            body = client.get("/healthcheck").json()
            assert body["version"] == "1.0.0"

    def test_503_timestamp_still_valid(self):
        with patch("healthcheck.get_health_status", return_value=False):
            body = client.get("/healthcheck").json()
            assert ISO8601_UTC_RE.match(body["timestamp"])


# ─── Spec Criterion: Versão do sistema ────────────────────────────────


class TestSpecVersion:
    """A spec define: 'Deve retornar informação básica sobre a versão do sistema'."""

    def test_version_is_semver_string(self):
        body = client.get("/healthcheck").json()
        assert SEMVER_RE.match(body["version"]), (
            f"Versão '{body['version']}' não é semântica (x.y.z)"
        )

    def test_version_constant_is_1_0_0(self):
        assert VERSION == "1.0.0"

    def test_version_constant_is_string(self):
        assert isinstance(VERSION, str)


# ─── Spec Criterion: Não expor informações sensíveis ──────────────────


class TestSpecNoSensitiveData:
    """A spec define: 'Não deve expor informações sensíveis (senhas, chaves, etc.)'."""

    FORBIDDEN_PATTERNS = [
        "password", "passwd", "secret", "token", "api_key",
        "apikey", "access_token", "private_key", "db_password",
        "credentials", "DATABASE_URL", "AWS_SECRET",
    ]

    def test_no_forbidden_keys_in_body(self):
        body = client.get("/healthcheck").json()
        for key in body:
            for pattern in self.FORBIDDEN_PATTERNS:
                assert pattern.lower() not in key.lower(), (
                    f"Chave sensível '{key}' encontrada no body"
                )

    def test_no_forbidden_values_in_body(self):
        body = client.get("/healthcheck").json()
        for key, val in body.items():
            val_str = str(val).lower()
            for pattern in self.FORBIDDEN_PATTERNS:
                assert pattern.lower() not in val_str, (
                    f"Valor sensível '{pattern}' encontrado em '{key}'"
                )

    def test_no_hidden_fields(self):
        """Body não deve ter campos ocultos além dos 3 da spec."""
        body = client.get("/healthcheck").json()
        allowed = {"status", "version", "timestamp"}
        extra = set(body.keys()) - allowed
        assert not extra, f"Campos não especificados encontrados: {extra}"


# ─── Spec Criterion: Acessível via HTTP GET ───────────────────────────


class TestSpecHTTPMethods:
    """A spec define: 'Deve ser acessível via HTTP GET'."""

    def test_get_works(self):
        r = client.get("/healthcheck")
        assert r.status_code in (200, 503)

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    def test_non_get_methods_rejected(self, method):
        """Métodos que não são GET devem ser rejeitados."""
        fn = getattr(client, method)
        r = fn("/healthcheck")
        assert r.status_code in (405, 404), (
            f"Method {method.upper()} deveria ser rejeitado, "
            f"retornou {r.status_code}"
        )


# ─── Spec Criterion: Módulo isolado ──────────────────────────────────


class TestHealthcheckModuleIsolation:
    """healthcheck.py deve ser um módulo isolado, sem dependência de framework."""

    def test_module_has_no_fastapi_import(self):
        """Módulo não deve importar FastAPI (responsabilidade do app.py)."""
        import healthcheck as hc_mod
        source = open(hc_mod.__file__).read()
        assert "fastapi" not in source.lower(), (
            "healthcheck.py importa FastAPI — deveria ser independente"
        )

    def test_module_has_no_flask_import(self):
        import healthcheck as hc_mod
        source = open(hc_mod.__file__).read()
        assert "flask" not in source.lower()

    def test_build_response_works_without_app(self):
        """build_healthcheck_response() funciona sem criar FastAPI app."""
        result = build_healthcheck_response()
        assert isinstance(result, dict)
        assert set(result.keys()) == {"status", "version", "timestamp"}


# ─── Spec Criterion: Status enum ─────────────────────────────────────


class TestSpecStatusEnum:
    """Status deve ser exatamente 'ok' ou 'error' — nada mais."""

    def test_ok_status_restricted(self):
        body = client.get("/healthcheck").json()
        assert body["status"] in VALID_STATUSES

    def test_ok_status_is_string(self):
        body = client.get("/healthcheck").json()
        assert isinstance(body["status"], str)

    def test_ok_status_lowercase(self):
        body = client.get("/healthcheck").json()
        assert body["status"] == body["status"].lower()

    def test_error_status_via_mock(self):
        with patch("healthcheck.get_health_status", return_value=False):
            body = client.get("/healthcheck").json()
            assert body["status"] == "error"
            assert body["status"] in VALID_STATUSES


# ─── Spec Criterion: Timestamp monotonicidade ────────────────────────


class TestSpecTimestampBehavior:
    """Timestamps de chamadas consecutivas devem ser coerentes."""

    def test_later_call_has_later_or_equal_timestamp(self):
        """Segunda chamada deve ter timestamp >= primeira."""
        body1 = client.get("/healthcheck").json()
        body2 = client.get("/healthcheck").json()

        ts1 = body1["timestamp"].replace("Z", "+00:00")
        ts2 = body2["timestamp"].replace("Z", "+00:00")

        dt1 = datetime.fromisoformat(ts1)
        dt2 = datetime.fromisoformat(ts2)
        assert dt2 >= dt1, (
            f"Timestamp retrocedeu: {ts1} -> {ts2}"
        )

    def test_timestamp_precision_at_least_seconds(self):
        """Timestamp deve ter precisão de pelo menos segundos."""
        body = client.get("/healthcheck").json()
        ts = body["timestamp"]
        # Deve ter pelo menos HH:MM:SS
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", ts)


# ─── Spec Criterion: Resposta 200 → status ok; 503 → status error ────


class TestSpecStatusCodeMapping:
    """Mapeamento entre HTTP status code e campo status do body."""

    def test_200_maps_to_ok(self):
        with patch("healthcheck.get_health_status", return_value=True):
            r = client.get("/healthcheck")
            assert r.status_code == 200
            assert r.json()["status"] == "ok"

    def test_503_maps_to_error(self):
        with patch("healthcheck.get_health_status", return_value=False):
            r = client.get("/healthcheck")
            assert r.status_code == 503
            assert r.json()["status"] == "error"

    def test_both_200_and_503_have_same_fields(self):
        """Independentemente do status, a estrutura é a mesma."""
        fields = {"status", "version", "timestamp"}

        with patch("healthcheck.get_health_status", return_value=True):
            ok_fields = set(client.get("/healthcheck").json().keys())

        with patch("healthcheck.get_health_status", return_value=False):
            err_fields = set(client.get("/healthcheck").json().keys())

        assert ok_fields == fields
        assert err_fields == fields


# ─── Spec Criterion: Chama build_healthcheck_response do módulo ───────


class TestSpecDelegation:
    """app.py delega a construção da resposta ao módulo healthcheck."""

    def test_app_uses_module_function(self):
        """A resposta da API deve ter os mesmos dados que o módulo."""
        api_body = client.get("/healthcheck").json()
        module_body = build_healthcheck_response()

        assert api_body["status"] == module_body["status"]
        assert api_body["version"] == module_body["version"]
        # Timestamp pode diferir por milissegundos, mas versão e status idênticos
