"""Testes de casos de borda e cenários adversos.

Cobertura
---------
- FastAPI TestClient com headers personalizados
- Body vazio vs. com body ignorado em GET
- Query params ignoradas no healthcheck
- Request com Content-Type incompatível
- Múltiplos headers de aceitação
- JSON inválido no body de request (GET não deve se importar)
- HealthResponse com valores extremos (strings muito longas)
- HealthResponse model_validate com dados inválidos
- HealthResponse model_validate com dados extras (should ignore them)
- Serialização do HealthResponse preserva campos exatos
- Verificação de que nenhum campo extra vaza no JSON da resposta
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.models import HealthResponse

client = TestClient(app)


# ── Headers personalizados ─────────────────────────────────────────────
class TestCustomHeaders:
    """Valida comportamento com headers variados na requisição."""

    def test_with_accept_html(self) -> None:
        """Accept: text/html não deve quebrar o endpoint JSON."""
        resp = client.get("/healthcheck", headers={"Accept": "text/html"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_with_accept_xml(self) -> None:
        """Accept: application/xml — endpoint deve retornar JSON mesmo assim."""
        resp = client.get("/healthcheck", headers={"Accept": "application/xml"})
        assert resp.status_code == 200

    def test_with_authorization_header(self) -> None:
        """Endpoint sem auth deve ignorar header de autorização."""
        resp = client.get(
            "/healthcheck",
            headers={"Authorization": "Bearer fake-token-12345"},
        )
        assert resp.status_code == 200

    def test_with_custom_user_agent(self) -> None:
        resp = client.get(
            "/healthcheck",
            headers={"User-Agent": "CustomAgent/1.0"},
        )
        assert resp.status_code == 200

    def test_with_multiple_accept_values(self) -> None:
        resp = client.get(
            "/healthcheck",
            headers={"Accept": "application/json, text/plain, */*"},
        )
        assert resp.status_code == 200
        assert "application/json" in resp.headers.get("content-type", "")


# ── Query params e body ────────────────────────────────────────────────
class TestQueryParamsAndBody:
    """GET /healthcheck não deve se importar com query params ou body."""

    def test_ignores_query_params(self) -> None:
        resp = client.get("/healthcheck?foo=bar&baz=123")
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"status": "healthy", "version": "1.0.0"}

    def test_ignores_empty_query_string(self) -> None:
        resp = client.get("/healthcheck?")
        assert resp.status_code == 200

    def test_ignores_trailing_question_mark_only(self) -> None:
        resp = client.get("/healthcheck?=")
        # Pode retornar 200 ou 422 dependendo do FastAPI
        assert resp.status_code in (200, 422)

    def test_get_with_json_body_ignored(self) -> None:
        """GET com body deve funcionar — FastAPI ignora body em GET."""
        resp = client.request(
            "GET",
            "/healthcheck",
            content=json.dumps({"unexpected": "data"}),
            headers={"Content-Type": "application/json"},
        )
        # FastAPI pode retornar 422 (body não esperado) ou 200 (ignora)
        assert resp.status_code in (200, 422)


# ── Paths com variações ────────────────────────────────────────────────
class TestPathVariations:
    """Valida comportamento com variações de path."""

    def test_healthcheck_exact_path(self) -> None:
        resp = client.get("/healthcheck")
        assert resp.status_code == 200

    def test_healthcheck_uppercase_fails(self) -> None:
        resp = client.get("/Healthcheck")
        assert resp.status_code == 404

    def test_healthcheck_with_suffix_fails(self) -> None:
        resp = client.get("/healthcheck-extra")
        assert resp.status_code == 404

    def test_healthcheck_prefix_fails(self) -> None:
        resp = client.get("/api/healthcheck")
        assert resp.status_code == 404

    def test_double_slash_healthcheck(self) -> None:
        """//healthcheck pode ser normalizado pelo servidor."""
        resp = client.get("//healthcheck")
        # Pode retornar 200 (normalizado) ou 404
        assert resp.status_code in (200, 404)


# ── Pydantic HealthResponse — valores extremos ─────────────────────────
class TestHealthResponseEdgeValues:
    """Testa o modelo Pydantic com valores extremos."""

    def test_very_long_status_string(self) -> None:
        long_status = "x" * 10000
        hr = HealthResponse(status=long_status)
        assert hr.status == long_status

    def test_very_long_version_string(self) -> None:
        long_version = "1." + "0" * 10000
        hr = HealthResponse(version=long_version)
        assert hr.version == long_version

    def test_unicode_status(self) -> None:
        hr = HealthResponse(status=" saudável ")
        assert hr.status == " saudável "

    def test_empty_string_status(self) -> None:
        """String vazia é aceita pelo modelo (sem validação de formato)."""
        hr = HealthResponse(status="")
        assert hr.status == ""

    def test_empty_string_version(self) -> None:
        hr = HealthResponse(version="")
        assert hr.version == ""

    def test_special_chars_status(self) -> None:
        hr = HealthResponse(status="ok!@#$%^&*()")
        assert hr.status == "ok!@#$%^&*()"

    def test_numeric_string_version(self) -> None:
        hr = HealthResponse(version="999.888.777")
        assert hr.version == "999.888.777"


# ── Pydantic HealthResponse — validação com dados inválidos ────────────
class TestHealthResponseInvalidData:
    """Testa rejeição de tipos inválidos no modelo."""

    def test_int_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            HealthResponse(status=42)  # type: ignore[arg-type]

    def test_float_version_rejected(self) -> None:
        with pytest.raises(ValidationError):
            HealthResponse(version=1.0)  # type: ignore[arg-type]

    def test_bool_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            HealthResponse(status=True)  # type: ignore[arg-type]

    def test_list_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            HealthResponse(status=["healthy"])  # type: ignore[arg-type]

    def test_dict_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            HealthResponse(status={"key": "value"})  # type: ignore[arg-type]

    def test_none_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            HealthResponse(status=None)  # type: ignore[arg-type]

    def test_none_version_rejected(self) -> None:
        with pytest.raises(ValidationError):
            HealthResponse(version=None)  # type: ignore[arg-type]


# ── Pydantic model_validate — dados extras ─────────────────────────────
class TestModelValidateExtras:
    """Valida como o modelo lida com campos extras."""

    def test_extra_fields_ignored_by_default(self) -> None:
        """Pydantic v2 por padrão ignora campos extras em model_validate."""
        hr = HealthResponse.model_validate(
            {"status": "healthy", "version": "1.0.0", "extra": "ignored"}
        )
        assert hr.status == "healthy"
        assert hr.version == "1.0.0"
        assert not hasattr(hr, "extra")

    def test_missing_field_uses_default(self) -> None:
        """Se faltar um campo, o default deve ser usado."""
        hr = HealthResponse.model_validate({"status": "degraded"})
        assert hr.version == "1.0.0"  # default

    def test_empty_dict_uses_all_defaults(self) -> None:
        hr = HealthResponse.model_validate({})
        assert hr.status == "healthy"
        assert hr.version == "1.0.0"

    def test_from_dict_api_response(self) -> None:
        """Simula desserialização da resposta da API."""
        api_response = client.get("/healthcheck").json()
        hr = HealthResponse.model_validate(api_response)
        assert hr.status == "healthy"
        assert hr.version == "1.0.0"


# ── Serialização — precisão do output ──────────────────────────────────
class TestSerializationPrecision:
    """Garante que a serialização produz exatamente o esperado."""

    def test_model_dump_exact_output(self) -> None:
        hr = HealthResponse()
        assert hr.model_dump() == {"status": "healthy", "version": "1.0.0"}

    def test_model_dump_json_exact_output(self) -> None:
        hr = HealthResponse()
        raw = hr.model_dump_json()
        parsed = json.loads(raw)
        assert parsed == {"status": "healthy", "version": "1.0.0"}

    def test_model_dump_no_extra_keys(self) -> None:
        hr = HealthResponse()
        dumped = hr.model_dump()
        assert set(dumped.keys()) == {"status", "version"}

    def test_json_output_order(self) -> None:
        """Campos devem aparecer na ordem: status, version."""
        hr = HealthResponse()
        raw = hr.model_dump_json()
        # Pydantic preserva a ordem de declaração
        status_pos = raw.find('"status"')
        version_pos = raw.find('"version"')
        assert status_pos < version_pos

    def test_json_no_extra_content(self) -> None:
        """JSON serializado não deve conter campos além de status e version."""
        hr = HealthResponse()
        raw = hr.model_dump_json()
        parsed = json.loads(raw)
        assert list(parsed.keys()) == ["status", "version"]


# ── Método healthcheck na rota (reflexão) ──────────────────────────────
class TestRouteIntrospection:
    """Introspecção da rota registrada no FastAPI."""

    def test_route_exists(self) -> None:
        routes_by_path = {r.path: r for r in app.routes if hasattr(r, "path")}
        assert "/healthcheck" in routes_by_path

    def test_route_methods(self) -> None:
        routes_by_path = {r.path: r for r in app.routes if hasattr(r, "path")}
        route = routes_by_path["/healthcheck"]
        methods = getattr(route, "methods", set())
        assert "GET" in methods

    def test_route_response_model(self) -> None:
        """A rota deve ter response_model configurado."""
        routes_by_path = {r.path: r for r in app.routes if hasattr(r, "path")}
        route = routes_by_path["/healthcheck"]
        response_model = getattr(route, "response_model", None)
        assert response_model is HealthResponse

    def test_only_one_get_route(self) -> None:
        """Deve haver apenas uma rota GET para /healthcheck."""
        get_routes = [
            r
            for r in app.routes
            if hasattr(r, "path") and r.path == "/healthcheck" and "GET" in getattr(r, "methods", set())
        ]
        assert len(get_routes) == 1
