"""
Testes de Critérios de Aceite — mapeamento 1:1 com a Spec Técnica.

Cada classe testa um critério de aceite EXATO da spec.
Casos de borda adicionais não cobertos pelos demais arquivos:

  - Rota /health NÃO deve existir (spec diz "ou", implementação usa /healthcheck)
  - HEAD e OPTIONS requests
  - Query params e path params extras devem ser ignorados ou rejeitados
  - App não expõe /docs, /redoc, /openapi.json (docs_url=None)
  - Resposta é idêntica independentemente do Accept header
  - Performance: resposta em < 500ms
  - Versão do módulo é importável e constante em runtime
  - healthcheck.py não contém prints ou logging (limpo para produção)
  - Response body contém EXATAMENTE 3 campos — nem mais nem menos
"""

import json
import re
import time
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import app
from healthcheck import VERSION, build_healthcheck_response, get_health_status

client = TestClient(app)

# ─── Helpers ──────────────────────────────────────────────────────────

ISO8601_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$"
)
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$")


# ═══════════════════════════════════════════════════════════════════════
# CRITÉRIO 1: "Criar endpoint que retorna status do sistema"
# ═══════════════════════════════════════════════════════════════════════


class TestCriterionEndpointExists:
    """O endpoint deve existir e retornar status do sistema."""

    def test_healthcheck_endpoint_responds(self):
        """GET /healthcheck deve existir e responder."""
        r = client.get("/healthcheck")
        assert r.status_code in (200, 503)

    def test_response_body_is_dict(self):
        """Resposta deve ser um dicionário (JSON object)."""
        body = client.get("/healthcheck").json()
        assert isinstance(body, dict)

    def test_status_field_exists(self):
        """Campo 'status' deve estar presente."""
        body = client.get("/healthcheck").json()
        assert "status" in body

    def test_status_value_is_meaningful(self):
        """Status deve ser 'ok' ou 'error' — valores semânticos."""
        body = client.get("/healthcheck").json()
        assert body["status"] in ("ok", "error")


# ═══════════════════════════════════════════════════════════════════════
# CRITÉRIO 2: "Deve ser acessível via HTTP GET"
# ═══════════════════════════════════════════════════════════════════════


class TestCriterionHttpGet:
    """Endpoint deve ser acessível exclusivamente via GET."""

    def test_get_returns_success(self):
        r = client.get("/healthcheck")
        assert r.status_code in (200, 503)

    def test_post_not_allowed(self):
        r = client.post("/healthcheck")
        assert r.status_code in (405, 404)

    def test_put_not_allowed(self):
        r = client.put("/healthcheck")
        assert r.status_code in (405, 404)

    def test_patch_not_allowed(self):
        r = client.patch("/healthcheck")
        assert r.status_code in (405, 404)

    def test_delete_not_allowed(self):
        r = client.delete("/healthcheck")
        assert r.status_code in (405, 404)

    def test_head_not_allowed_or_not_implemented(self):
        """HEAD não está explicitamente na spec; deve ser rejeitado ou retornar sem body."""
        r = client.head("/healthcheck")
        # FastAPI suporta HEAD implicitamente para rotas GET, retornando 200/503
        # ou rejeita com 405 — ambos são aceitáveis
        assert r.status_code in (200, 405, 503)

    def test_options_not_allowed_or_cors(self):
        """OPTIONS pode retornar 200 (CORS) ou 405 — ambos aceitáveis."""
        r = client.options("/healthcheck")
        assert r.status_code in (200, 405, 404)


# ═══════════════════════════════════════════════════════════════════════
# CRITÉRIO 3: "Deve retornar código 200 quando o sistema estiver operacional"
# ═══════════════════════════════════════════════════════════════════════


class TestCriterion200WhenOperational:
    """Status HTTP 200 deve ser retornado quando o sistema está operacional."""

    def test_200_when_healthy(self):
        with patch("healthcheck.get_health_status", return_value=True):
            r = client.get("/healthcheck")
            assert r.status_code == 200

    def test_200_default_behavior(self):
        """Sem mock, implementação padrão retorna 200."""
        r = client.get("/healthcheck")
        assert r.status_code == 200

    def test_200_body_has_status_ok(self):
        with patch("healthcheck.get_health_status", return_value=True):
            body = client.get("/healthcheck").json()
            assert body["status"] == "ok"

    def test_body_matches_spec_example_format(self):
        """Body deve seguir o formato do exemplo da spec."""
        body = client.get("/healthcheck").json()
        # Spec exemplo: {"status": "ok", "version": "1.0.0", "timestamp": "..."}
        assert body["status"] == "ok"
        assert body["version"] == "1.0.0"
        assert ISO8601_UTC_RE.match(body["timestamp"])


# ═══════════════════════════════════════════════════════════════════════
# CRITÉRIO 4: "Deve retornar informação básica sobre a versão do sistema"
# ═══════════════════════════════════════════════════════════════════════


class TestCriterionVersionInfo:
    """Resposta deve conter informação de versão do sistema."""

    def test_version_field_present(self):
        body = client.get("/healthcheck").json()
        assert "version" in body

    def test_version_is_string(self):
        body = client.get("/healthcheck").json()
        assert isinstance(body["version"], str)

    def test_version_follows_semver(self):
        """Versão deve seguir formato x.y.z (semântico)."""
        body = client.get("/healthcheck").json()
        assert SEMVER_RE.match(body["version"]), (
            f"Versão '{body['version']}' não é semântica"
        )

    def test_version_not_empty(self):
        body = client.get("/healthcheck").json()
        assert len(body["version"].strip()) > 0

    def test_version_not_none(self):
        body = client.get("/healthcheck").json()
        assert body["version"] is not None

    def test_version_accessible_from_module(self):
        """Constante VERSION deve existir no módulo healthcheck."""
        assert hasattr(__import__("healthcheck"), "VERSION")
        assert VERSION == "1.0.0"

    def test_version_unchanged_across_multiple_requests(self):
        """Versão não deve mudar entre chamadas."""
        versions = set()
        for _ in range(10):
            body = client.get("/healthcheck").json()
            versions.add(body["version"])
        assert versions == {"1.0.0"}, f"Versão instável: {versions}"

    def test_version_in_503_also(self):
        """Versão deve estar presente mesmo no 503."""
        with patch("healthcheck.get_health_status", return_value=False):
            body = client.get("/healthcheck").json()
            assert body["version"] == "1.0.0"


# ═══════════════════════════════════════════════════════════════════════
# CRITÉRIO 5: "Não deve expor informações sensíveis (senhas, chaves, etc.)"
# ═══════════════════════════════════════════════════════════════════════


class TestCriterionNoSensitiveData:
    """Nenhuma informação sensível deve ser exposta."""

    SENSITIVE_PATTERNS = [
        "password", "passwd", "secret", "token", "api_key",
        "apikey", "access_token", "private_key", "db_password",
        "credentials", "DATABASE_URL", "AWS_SECRET", "AWS_KEY",
        "REDIS_PASSWORD", "SMTP_PASSWORD", "SSH_KEY",
    ]

    def test_no_sensitive_keys_in_ok_response(self):
        body = client.get("/healthcheck").json()
        for key in body:
            for pattern in self.SENSITIVE_PATTERNS:
                assert pattern.lower() not in key.lower(), (
                    f"Chave sensível '{key}' na resposta 200"
                )

    def test_no_sensitive_keys_in_503_response(self):
        with patch("healthcheck.get_health_status", return_value=False):
            body = client.get("/healthcheck").json()
            for key in body:
                for pattern in self.SENSITIVE_PATTERNS:
                    assert pattern.lower() not in key.lower(), (
                        f"Chave sensível '{key}' na resposta 503"
                    )

    def test_no_sensitive_values_in_ok_response(self):
        body = client.get("/healthcheck").json()
        for key, val in body.items():
            val_str = str(val).lower()
            for pattern in self.SENSITIVE_PATTERNS:
                assert pattern.lower() not in val_str, (
                    f"Valor sensível em campo '{key}'"
                )

    def test_no_env_var_leakage(self):
        """Resposta não deve conter referências a variáveis de ambiente."""
        body_str = json.dumps(client.get("/healthcheck").json())
        assert "environ" not in body_str.lower()
        assert "os.environ" not in body_str.lower()

    def test_no_traceback_or_debug_info(self):
        """Resposta não deve conter stack traces."""
        body_str = json.dumps(client.get("/healthcheck").json())
        assert "traceback" not in body_str.lower()
        assert "stack trace" not in body_str.lower()

    def test_no_internal_ip_or_hostname(self):
        """Resposta não deve conter IPs internos ou nomes de host."""
        body = client.get("/healthcheck").json()
        for val in body.values():
            val_str = str(val)
            # Não deve conter IPs no formato x.x.x.x
            assert not re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", val_str), (
                f"IP encontrado no valor: {val_str}"
            )

    def test_response_exactly_3_fields_no_leaks(self):
        """Spec define exatamente 3 campos — qualquer campo extra é suspeito."""
        body = client.get("/healthcheck").json()
        assert len(body) == 3, (
            f"Esperado 3 campos, encontrado {len(body)}: {list(body.keys())}"
        )
        assert set(body.keys()) == {"status", "version", "timestamp"}


# ═══════════════════════════════════════════════════════════════════════
# CRITÉRIO EXTRA: Rota /health NÃO deve existir
# ═══════════════════════════════════════════════════════════════════════


class TestNoHealthRoute:
    """Spec diz '/healthcheck ou /health' — implementação usa apenas /healthcheck.
    Não deve haver rota /health (evitar duplicação)."""

    def test_slash_health_not_found(self):
        r = client.get("/health")
        assert r.status_code in (404, 405), (
            f"Rota /health não deveria existir, retornou {r.status_code}"
        )

    def test_slash_health_no_redirect(self):
        """GET /health não deve redirecionar para /healthcheck."""
        r = client.get("/health", allow_redirects=False)
        assert r.status_code in (404, 405)


# ═══════════════════════════════════════════════════════════════════════
# CASOS DE BORDA: Query params e path params extras
# ═══════════════════════════════════════════════════════════════════════


class TestEdgeCaseQueryParams:
    """Query params extras não devem quebrar o endpoint."""

    def test_with_query_param(self):
        r = client.get("/healthcheck?foo=bar")
        assert r.status_code in (200, 503)

    def test_with_multiple_query_params(self):
        r = client.get("/healthcheck?foo=bar&debug=true")
        assert r.status_code in (200, 503)

    def test_with_empty_query_param(self):
        r = client.get("/healthcheck?")
        assert r.status_code in (200, 503)

    def test_query_params_dont_affect_body(self):
        """Body não deve ser alterado por query params."""
        body_clean = client.get("/healthcheck").json()
        body_params = client.get("/healthcheck?verbose=true&format=json").json()
        assert set(body_clean.keys()) == set(body_params.keys())
        assert body_clean["status"] == body_params["status"]
        assert body_clean["version"] == body_params["version"]


# ═══════════════════════════════════════════════════════════════════════
# CASOS DE BORDA: Accept headers variados
# ═══════════════════════════════════════════════════════════════════════


class TestEdgeCaseAcceptHeaders:
    """Resposta deve ser JSON independente do Accept header."""

    def test_accept_json(self):
        r = client.get("/healthcheck", headers={"Accept": "application/json"})
        assert r.status_code == 200

    def test_accept_text(self):
        r = client.get("/healthcheck", headers={"Accept": "text/plain"})
        # Deve retornar JSON mesmo com Accept text/plain
        assert r.status_code == 200

    def test_accept_wildcard(self):
        r = client.get("/healthcheck", headers={"Accept": "*/*"})
        assert r.status_code == 200

    def test_no_accept_header(self):
        r = client.get("/healthcheck", headers={})
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════
# CASOS DE BORDA: App não expõe docs
# ═══════════════════════════════════════════════════════════════════════


class TestAppNoExposedDocs:
    """App deve estar configurado com docs desabilitados (docs_url=None)."""

    def test_docs_not_accessible(self):
        r = client.get("/docs")
        assert r.status_code == 404

    def test_redoc_not_accessible(self):
        r = client.get("/redoc")
        assert r.status_code == 404

    def test_openapi_json_not_accessible(self):
        r = client.get("/openapi.json")
        assert r.status_code == 404


# ═══════════════════════════════════════════════════════════════════════
# CASOS DE BORDA: Performance
# ═══════════════════════════════════════════════════════════════════════


class TestEdgeCasePerformance:
    """Healthcheck deve ser rápido — não deve executar operações pesadas."""

    def test_response_time_under_500ms(self):
        """Healthcheck deve responder em menos de 500ms."""
        start = time.perf_counter()
        r = client.get("/healthcheck")
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, (
            f"Healthcheck levou {elapsed:.3f}s — máximo aceitável: 0.5s"
        )

    def test_100_requests_under_5s(self):
        """100 chamadas devem completar em menos de 5s."""
        start = time.perf_counter()
        for _ in range(100):
            r = client.get("/healthcheck")
            assert r.status_code in (200, 503)
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, (
            f"100 chamadas levaram {elapsed:.1f}s"
        )


# ═══════════════════════════════════════════════════════════════════════
# CASOS DE BORDA: Módulo healthcheck isolado
# ═══════════════════════════════════════════════════════════════════════


class TestEdgeCaseModuleIsolation:
    """healthcheck.py deve ser um módulo puro, sem side effects."""

    def test_no_print_statements(self):
        """Módulo não deve ter prints (poluição de stdout)."""
        import healthcheck as hc
        source = open(hc.__file__).read()
        # Permite print dentro de if __name__ == "__main__" apenas
        lines = [
            l for l in source.split("\n")
            if l.strip().startswith("print(")
            and "main" not in source[max(0, source.find(l) - 200):source.find(l)]
        ]
        assert not lines, f"Print statements encontrados: {lines}"

    def test_no_sys_exit(self):
        """Módulo não deve chamar sys.exit()."""
        import healthcheck as hc
        source = open(hc.__file__).read()
        assert "sys.exit" not in source

    def test_no_os_import(self):
        """Módulo não deve importar os (poderia vazar info do sistema)."""
        import healthcheck as hc
        source = open(hc.__file__).read()
        assert "\nimport os" not in source
        assert "\nfrom os " not in source

    def test_module_file_is_small(self):
        """Módulo de healthcheck deve ser leve (< 2KB)."""
        import healthcheck as hc
        import os
        size = os.path.getsize(hc.__file__)
        assert size < 2048, (
            f"Módulo healthcheck.py tem {size} bytes — máximo 2048"
        )

    def test_version_is_immutável(self):
        """VERSION não deve mudar após múltiplas leituras."""
        values = set()
        for _ in range(10):
            from importlib import reload
            import healthcheck as hc
            reload(hc)
            values.add(hc.VERSION)
        assert values == {"1.0.0"}


# ═══════════════════════════════════════════════════════════════════════
# CASOS DE BORDA: Resposta JSON é sempre válida
# ═══════════════════════════════════════════════════════════════════════


class TestEdgeCaseJsonValidity:
    """Resposta deve ser JSON válido e parseável em qualquer cenário."""

    def test_json_parseable_ok(self):
        r = client.get("/healthcheck")
        body = r.json()
        assert isinstance(body, dict)

    def test_json_parseable_503(self):
        with patch("healthcheck.get_health_status", return_value=False):
            r = client.get("/healthcheck")
            body = r.json()
            assert isinstance(body, dict)

    def test_raw_content_is_valid_json(self):
        """Conteúdo bruto deve ser JSON válido."""
        r = client.get("/healthcheck")
        parsed = json.loads(r.content.decode("utf-8"))
        assert isinstance(parsed, dict)

    def test_no_html_in_response(self):
        """Resposta não deve conter HTML."""
        r = client.get("/healthcheck")
        content = r.content.decode("utf-8")
        assert "<html" not in content.lower()
        assert "<!DOCTYPE" not in content.lower()

    def test_no_bom_marker(self):
        """Body não deve ter BOM UTF-8."""
        r = client.get("/healthcheck")
        assert not r.content.startswith(b"\xef\xbb\xbf")


# ═══════════════════════════════════════════════════════════════════════
# CASOS DE BORDA: Transição de estados
# ═══════════════════════════════════════════════════════════════════════


class TestEdgeCaseStateTransitions:
    """Transições entre estados devem ser limpas e consistentes."""

    def test_ok_to_error_to_ok(self):
        """Ciclo completo: ok → error → ok."""
        # OK
        with patch("healthcheck.get_health_status", return_value=True):
            r1 = client.get("/healthcheck")
            assert r1.status_code == 200
            assert r1.json()["status"] == "ok"

        # ERROR
        with patch("healthcheck.get_health_status", return_value=False):
            r2 = client.get("/healthcheck")
            assert r2.status_code == 503
            assert r2.json()["status"] == "error"

        # OK novamente
        with patch("healthcheck.get_health_status", return_value=True):
            r3 = client.get("/healthcheck")
            assert r3.status_code == 200
            assert r3.json()["status"] == "ok"

    def test_rapid_toggle_between_states(self):
        """10 alternâncias rápidas entre ok e error."""
        for i in range(10):
            healthy = (i % 2 == 0)
            with patch("healthcheck.get_health_status", return_value=healthy):
                r = client.get("/healthcheck")
                expected_code = 200 if healthy else 503
                expected_status = "ok" if healthy else "error"
                assert r.status_code == expected_code
                assert r.json()["status"] == expected_status

    def test_structure_consistent_across_all_states(self):
        """Estrutura (3 campos, mesmos nomes) é idêntica em todos os estados."""
        expected_fields = {"status", "version", "timestamp"}

        with patch("healthcheck.get_health_status", return_value=True):
            ok_fields = set(client.get("/healthcheck").json().keys())

        with patch("healthcheck.get_health_status", return_value=False):
            err_fields = set(client.get("/healthcheck").json().keys())

        assert ok_fields == expected_fields
        assert err_fields == expected_fields
        assert ok_fields == err_fields
