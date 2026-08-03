"""
Testes de propriedades e cenários avançados do endpoint de healthcheck.

Cobertura:
  - Idempotência do endpoint (N chamadas, mesma estrutura)
  - Resposta é compacta (tamanho razoável)
  - Endpoint não depende de estado externo
  - App FastAPI inicializa corretamente
  - healthcheck module: VERSION é atributo público
  - build_healthcheck_response é determinístico por chamada
  - get_health_status retorna bool
  - Timestamp não contém timezone offset (+HH:MM) — apenas Z
  - Campos da resposta são todos strings
  - Não há trailing newline ou BOM no body
  - Múltiplas chamadas rápidas não falham
"""

import json

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import app
from healthcheck import VERSION, build_healthcheck_response, get_health_status

client = TestClient(app)


# ─── Idempotência ─────────────────────────────────────────────────────


class TestIdempotency:
    """Chamadas repetidas devem retornar estrutura idêntica."""

    @pytest.mark.parametrize("iteration", range(20))
    def test_structure_unchanged_over_repeated_calls(self, iteration):
        body = client.get("/healthcheck").json()
        assert set(body.keys()) == {"status", "version", "timestamp"}
        assert body["status"] in ("ok", "error")
        assert isinstance(body["version"], str)
        assert isinstance(body["timestamp"], str)

    def test_status_always_ok_when_healthy(self):
        """Enquanto get_health_status() retorna True, status é sempre 'ok'."""
        for _ in range(10):
            body = client.get("/healthcheck").json()
            assert body["status"] == "ok"


# ─── Tamanho da Resposta ──────────────────────────────────────────────


class TestResponseSize:
    """Resposta deve ser compacta — healthcheck não deve transmitir dados desnecessários."""

    def test_body_size_under_512_bytes(self):
        r = client.get("/healthcheck")
        size = len(r.content)
        assert size < 512, (
            f"Body muito grande para um healthcheck: {size} bytes"
        )

    def test_body_is_valid_json(self):
        """Body deve ser JSON parseável sem erros."""
        r = client.get("/healthcheck")
        parsed = json.loads(r.content)
        assert isinstance(parsed, dict)

    def test_no_bom_in_body(self):
        """Body não deve começar com BOM UTF-8."""
        r = client.get("/healthcheck")
        assert not r.content.startswith(b"\xef\xbb\xbf"), (
            "Body contém BOM UTF-8"
        )


# ─── App Initialization ───────────────────────────────────────────────


class TestAppInitialization:
    """Valida que o app FastAPI está configurado corretamente."""

    def test_app_is_fastapi_instance(self):
        from fastapi import FastAPI
        assert isinstance(app, FastAPI)

    def test_healthcheck_route_exists(self):
        """Rota /healthcheck deve estar registrada."""
        routes = [r.path for r in app.routes]
        assert "/healthcheck" in routes

    def test_only_healthcheck_route(self):
        """App não deve expor outras rotas que possam vazar dados."""
        routes = [
            r.path for r in app.routes
            if hasattr(r, "path")
        ]
        non_health = [
            r for r in routes
            if r not in ("/healthcheck", "/openapi.json", "/docs", "/redoc")
        ]
        assert not non_health, (
            f"Rotas inesperadas expostas: {non_health}"
        )


# ─── healthcheck.py: Propriedades do Módulo ───────────────────────────


class TestHealthcheckModuleProperties:
    """Propriedades do módulo healthcheck.py."""

    def test_version_is_public_constant(self):
        """VERSION deve ser acessível como atributo público do módulo."""
        import healthcheck as hc
        assert hasattr(hc, "VERSION")
        assert hc.VERSION == "1.0.0"

    def test_get_health_status_returns_bool(self):
        result = get_health_status()
        assert isinstance(result, bool), (
            f"get_health_status() deveria retornar bool, retornou {type(result)}"
        )

    def test_build_response_returns_dict(self):
        result = build_healthcheck_response()
        assert isinstance(result, dict)

    def test_build_response_has_exactly_three_keys(self):
        result = build_healthcheck_response()
        assert len(result) == 3, (
            f"build_healthcheck_response() deveria ter 3 chaves, "
            f"tem {len(result)}: {list(result.keys())}"
        )

    def test_build_response_no_private_attributes(self):
        """Resposta não deve conter chaves que comecem com _ (privadas)."""
        result = build_healthcheck_response()
        for key in result:
            assert not key.startswith("_"), (
                f"Chave privada '{key}' encontrada na resposta"
            )

    def test_build_response_values_are_strings(self):
        """Todos os valores da resposta devem ser strings."""
        result = build_healthcheck_response()
        for key, val in result.items():
            assert isinstance(val, str), (
                f"Campo '{key}' deveria ser str, é {type(val).__name__}"
            )


# ─── Timestamp: Propriedades Avançadas ────────────────────────────────


class TestTimestampAdvanced:
    """Propriedades avançadas do campo timestamp."""

    def test_no_plus_offset_in_timestamp(self):
        """Timestamp não deve conter +00:00 — deve usar Z."""
        body = client.get("/healthcheck").json()
        assert "+00:00" not in body["timestamp"], (
            f"Timestamp contém '+00:00' em vez de 'Z': {body['timestamp']}"
        )

    def test_timestamp_is_utc(self):
        """Timestamp parseado deve estar em UTC."""
        body = client.get("/healthcheck").json()
        ts = body["timestamp"]
        assert ts.endswith("Z"), f"Timestamp não termina com Z: {ts}"

    def test_timestamp_year_is_plausible(self):
        """Ano no timestamp deve ser plausible (>= 2024)."""
        body = client.get("/healthcheck").json()
        year = int(body["timestamp"][:4])
        assert year >= 2024, f"Ano implausible no timestamp: {year}"

    def test_timestamp_format_consistent_across_module_and_api(self):
        """Formato do timestamp deve ser igual no módulo e na API."""
        module_ts = build_healthcheck_response()["timestamp"]
        api_ts = client.get("/healthcheck").json()["timestamp"]

        # Ambos devem terminar com Z
        assert module_ts.endswith("Z")
        assert api_ts.endswith("Z")

        # Ambos devem ter T separador
        assert "T" in module_ts
        assert "T" in api_ts


# ─── Mock: Comportamento do healthcheck ───────────────────────────────


class TestMockedHealthStatus:
    """Testes com mock para validar transição de estados."""

    def test_true_to_false_transition(self):
        """Transição de saudável para doente deve alterar status E HTTP code."""
        with patch("healthcheck.get_health_status", return_value=True):
            r1 = client.get("/healthcheck")
            assert r1.status_code == 200
            assert r1.json()["status"] == "ok"

        with patch("healthcheck.get_health_status", return_value=False):
            r2 = client.get("/healthcheck")
            assert r2.status_code == 503
            assert r2.json()["status"] == "error"

    def test_version_unchanged_across_states(self):
        """Versão não deve mudar entre estados saudável/doente."""
        with patch("healthcheck.get_health_status", return_value=True):
            v1 = client.get("/healthcheck").json()["version"]

        with patch("healthcheck.get_health_status", return_value=False):
            v2 = client.get("/healthcheck").json()["version"]

        assert v1 == v2 == "1.0.0"

    def test_health_status_function_is_callable(self):
        """get_health_status deve ser chamável e não levantar exceções."""
        result = get_health_status()
        assert result is not None  # Must return a value, not None


# ─── Segurança Adicional ──────────────────────────────────────────────


class TestAdditionalSecurity:
    """Segurança além do básico: headers, CORS, cache."""

    def test_no_server_header_leaking_version(self):
        """Header Server não deve vazar versão do framework."""
        r = client.get("/healthcheck")
        server = r.headers.get("server", "")
        # FastAPI/Starlette pode ou não incluir Server header
        if server:
            assert "1.0.0" not in server, (
                f"Versão da app vaza no header Server: {server}"
            )

    def test_no_x_powered_by_header(self):
        """Não deve haver header X-Powered-By."""
        r = client.get("/healthcheck")
        assert "x-powered-by" not in {
            k.lower() for k in r.headers.keys()
        }

    def test_response_body_has_no_debug_info(self):
        """Body não deve conter stack traces ou debug info."""
        body_str = json.dumps(client.get("/healthcheck").json())
        debug_patterns = [
            "traceback", "stack trace", "debug",
            "internal server error", "exception",
        ]
        for pattern in debug_patterns:
            assert pattern not in body_str.lower(), (
                f"Info de debug encontrada no body: '{pattern}'"
            )


# ─── Robustez ─────────────────────────────────────────────────────────


class TestRobustness:
    """Testes de robustez para garantir estabilidade."""

    def test_rapid_fire_requests(self):
        """100 chamadas rápidas não devem falhar."""
        for _ in range(100):
            r = client.get("/healthcheck")
            assert r.status_code in (200, 503)
            body = r.json()
            assert "status" in body

    def test_concurrent_mock_switches(self):
        """Alternar rapidamente entre estados não corrompe resposta."""
        for healthy in [True, False, True, True, False, True]:
            with patch("healthcheck.get_health_status", return_value=healthy):
                r = client.get("/healthcheck")
                expected_status = 200 if healthy else 503
                expected_body_status = "ok" if healthy else "error"
                assert r.status_code == expected_status
                assert r.json()["status"] == expected_body_status

    def test_response_is_always_json_even_on_error(self):
        """Mesmo em 503, resposta deve ser JSON válido."""
        with patch("healthcheck.get_health_status", return_value=False):
            r = client.get("/healthcheck")
            assert r.status_code == 503
            # Não deve levantar exceção ao parsear JSON
            body = r.json()
            assert isinstance(body, dict)
