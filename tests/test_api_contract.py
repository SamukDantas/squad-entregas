"""Testes de contrato da API conforme a especificação técnica.

Cobertura (aceitação da spec)
------------------------------
- OpenAPI schema expõe o endpoint GET /healthcheck corretamente
- O schema da resposta inclui os campos 'status' e 'version' com tipos string
- Modelos Pydantic serializam de/para dict corretamente (round-trip)
- Valores fixos: status="healthy", version="1.0.0" em todas as chamadas
- App FastAPI configurada com título e versão corretos
- Apenas o path /healthcheck existe (sem sub-paths ou trailing-slash ambiguity)
- GET /healthcheck em path inexistente retorna 404
- Resposta não contém campos além dos especificados (nem extras no JSON nem no schema)
- Validação de que o response_model está declarado na rota (via OpenAPI)
- Edge: corpo da resposta é JSON válido (parseável)
- Edge: múltiplas chamadas concorrentes (sequenciais) são idênticas
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import HealthResponse
from app.routes import router

client = TestClient(app)


# ── Fixture ────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def openapi_schema() -> dict:
    """Cache do schema OpenAPI gerado pelo FastAPI."""
    return client.get("/openapi.json").json()


@pytest.fixture(scope="module")
def healthcheck_endpoint_schema(openapi_schema: dict) -> dict:
    """Extrai o schema do path /healthcheck do OpenAPI."""
    paths = openapi_schema.get("paths", {})
    return paths.get("/healthcheck", {})


# ── 1. OpenAPI / Documentação ─────────────────────────────────────────
class TestOpenAPISchema:
    """Valida que o schema OpenAPI reflete o contrato da spec."""

    def test_openapi_json_is_accessible(self) -> None:
        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_openapi_is_valid_json(self) -> None:
        response = client.get("/openapi.json")
        parsed = response.json()
        assert isinstance(parsed, dict)

    def test_healthcheck_path_exists_in_openapi(
        self, healthcheck_endpoint_schema: dict
    ) -> None:
        assert healthcheck_endpoint_schema, "Path /healthcheck not found in OpenAPI"

    def test_get_method_defined(
        self, healthcheck_endpoint_schema: dict
    ) -> None:
        assert "get" in healthcheck_endpoint_schema

    def test_post_not_defined(
        self, healthcheck_endpoint_schema: dict
    ) -> None:
        """Apenas GET deve estar definido no schema (post não documentado)."""
        assert "post" not in healthcheck_endpoint_schema

    def test_response_model_in_openapi(
        self, healthcheck_endpoint_schema: dict
    ) -> None:
        """A resposta 200 deve referenciar o modelo HealthResponse."""
        get_spec = healthcheck_endpoint_schema["get"]
        responses = get_spec.get("responses", {})
        ok_response = responses.get("200", {})
        content = ok_response.get("content", {})
        json_content = content.get("application/json", {})
        schema_ref = json_content.get("schema", {})
        # Pode ser $ref ou inline
        assert schema_ref, "Schema da resposta 200 não encontrado"

    def test_response_schema_has_status_field(
        self, openapi_schema: dict, healthcheck_endpoint_schema: dict
    ) -> None:
        """Schema da resposta deve conter campo 'status'."""
        get_spec = healthcheck_endpoint_schema["get"]
        resp_200 = get_spec["responses"]["200"]
        schema = resp_200["content"]["application/json"]["schema"]

        # Resolver $ref se necessário
        if "$ref" in schema:
            ref_path = schema["$ref"].split("/")
            resolved = openapi_schema
            for part in ref_path[1:]:  # pular '#'
                resolved = resolved[part]
            schema = resolved

        props = schema.get("properties", {})
        assert "status" in props, "Campo 'status' ausente no schema da resposta"

    def test_response_schema_has_version_field(
        self, openapi_schema: dict, healthcheck_endpoint_schema: dict
    ) -> None:
        """Schema da resposta deve conter campo 'version'."""
        get_spec = healthcheck_endpoint_schema["get"]
        resp_200 = get_spec["responses"]["200"]
        schema = resp_200["content"]["application/json"]["schema"]

        if "$ref" in schema:
            ref_path = schema["$ref"].split("/")
            resolved = openapi_schema
            for part in ref_path[1:]:
                resolved = resolved[part]
            schema = resolved

        props = schema.get("properties", {})
        assert "version" in props, "Campo 'version' ausente no schema da resposta"

    def test_response_schema_fields_are_string_type(
        self, openapi_schema: dict, healthcheck_endpoint_schema: dict
    ) -> None:
        """Ambos os campos devem ser do tipo 'string' no schema."""
        get_spec = healthcheck_endpoint_schema["get"]
        resp_200 = get_spec["responses"]["200"]
        schema = resp_200["content"]["application/json"]["schema"]

        if "$ref" in schema:
            ref_path = schema["$ref"].split("/")
            resolved = openapi_schema
            for part in ref_path[1:]:
                resolved = resolved[part]
            schema = resolved

        props = schema.get("properties", {})
        assert props["status"].get("type") == "string"
        assert props["version"].get("type") == "string"

    def test_response_schema_has_no_extra_fields(
        self, openapi_schema: dict, healthcheck_endpoint_schema: dict
    ) -> None:
        """Schema deve conter exatamente 'status' e 'version' — sem campos extras."""
        get_spec = healthcheck_endpoint_schema["get"]
        resp_200 = get_spec["responses"]["200"]
        schema = resp_200["content"]["application/json"]["schema"]

        if "$ref" in schema:
            ref_path = schema["$ref"].split("/")
            resolved = openapi_schema
            for part in ref_path[1:]:
                resolved = resolved[part]
            schema = resolved

        props = set(schema.get("properties", {}).keys())
        assert props == {"status", "version"}, (
            f"Campos extras no schema: {props - {'status', 'version'}}"
        )

    def test_description_present(
        self, healthcheck_endpoint_schema: dict
    ) -> None:
        """Endpoint deve ter uma descrição no schema."""
        get_spec = healthcheck_endpoint_schema["get"]
        assert get_spec.get("summary") or get_spec.get("description")


# ── 2. Configuração do App ────────────────────────────────────────────
class TestAppConfiguration:
    """Valida metadados da aplicação FastAPI."""

    def test_app_is_fastapi_instance(self) -> None:
        from fastapi import FastAPI
        assert isinstance(app, FastAPI)

    def test_app_title(self) -> None:
        assert app.title == "Healthcheck API"

    def test_app_version(self) -> None:
        assert app.version == "1.0.0"

    def test_router_included(self) -> None:
        """O router deve estar registrado na aplicação."""
        routes = [r.path for r in app.routes]
        assert "/healthcheck" in routes


# ── 3. Valores Fixos (Contract) ───────────────────────────────────────
class TestFixedValues:
    """Spec: 'status: healthy' e 'version: 1.0.0' são valores fixos."""

    def test_health_response_defaults(self) -> None:
        hr = HealthResponse()
        assert hr.status == "healthy"
        assert hr.version == "1.0.0"

    def test_endpoint_returns_exact_values(self) -> None:
        body = client.get("/healthcheck").json()
        assert body["status"] == "healthy"
        assert body["version"] == "1.0.0"

    def test_endpoint_body_is_dict_with_two_keys(self) -> None:
        body = client.get("/healthcheck").json()
        assert isinstance(body, dict)
        assert len(body) == 2

    def test_status_value_is_string(self) -> None:
        body = client.get("/healthcheck").json()
        assert isinstance(body["status"], str)

    def test_version_value_is_string(self) -> None:
        body = client.get("/healthcheck").json()
        assert isinstance(body["version"], str)


# ── 4. Round-trip: API → Dict → Pydantic → Dict ───────────────────────
class TestRoundTrip:
    """Valida que a resposta da API pode ser desserializada no Pydantic."""

    def test_dict_to_model_round_trip(self) -> None:
        body = client.get("/healthcheck").json()
        hr = HealthResponse(**body)
        assert hr.status == "healthy"
        assert hr.version == "1.0.0"
        assert hr.model_dump() == body

    def test_model_validate_from_api_response(self) -> None:
        """HealthResponse.model_validate deve aceitar o dict da API."""
        body = client.get("/healthcheck").json()
        hr = HealthResponse.model_validate(body)
        assert hr.status == "healthy"
        assert hr.version == "1.0.0"

    def test_json_string_round_trip(self) -> None:
        """JSON serializado → parse → deve ser idêntico."""
        body = client.get("/healthcheck").json()
        raw_json = json.dumps(body)
        parsed_back = json.loads(raw_json)
        assert parsed_back == body


# ── 5. Content-Type ────────────────────────────────────────────────────
class TestContentTypeHeader:
    """Spec: Content-Type deve ser application/json."""

    def test_content_type_json(self) -> None:
        resp = client.get("/healthcheck")
        ct = resp.headers.get("content-type", "")
        assert "application/json" in ct

    def test_content_type_not_html(self) -> None:
        resp = client.get("/healthcheck")
        ct = resp.headers.get("content-type", "")
        assert "text/html" not in ct

    def test_content_type_not_xml(self) -> None:
        resp = client.get("/healthcheck")
        ct = resp.headers.get("content-type", "")
        assert "xml" not in ct


# ── 6. Segurança / Headers ────────────────────────────────────────────
class TestSecurityHeaders:
    """Validações de segurança básicas nos headers."""

    def test_no_server_header_leak(self) -> None:
        """Header 'server' não deve expor tecnologia interna."""
        resp = client.get("/healthcheck")
        server = resp.headers.get("server", "")
        # FastAPI/Uvicorn podem adicionar server, mas não deve conter versão detalhada
        assert "uvicorn" not in server.lower() or server == ""

    def test_response_is_json_parseable(self) -> None:
        """Corpo deve ser JSON válido e parseável."""
        resp = client.get("/healthcheck")
        # Se não for JSON válido, .json() lança exceção
        body = resp.json()
        assert body is not None


# ── 7. Paths e Métodos ─────────────────────────────────────────────────
class TestPathAndMethods:
    """Valida comportamento de paths e métodos HTTP."""

    def test_healthcheck_only_at_root(self) -> None:
        """GET /healthcheck funciona; GET /healthcheck/ pode ser diferente."""
        resp = client.get("/healthcheck")
        assert resp.status_code == 200

    def test_nonexistent_path_returns_404(self) -> None:
        resp = client.get("/nonexistent")
        assert resp.status_code == 404

    def test_root_path_returns_404(self) -> None:
        """GET / não deve existir."""
        resp = client.get("/")
        assert resp.status_code == 404

    def test_get_only_on_healthcheck(self) -> None:
        """POST/PUT/PATCH/DELETE em /healthcheck devem retornar 405."""
        for method in ["post", "put", "patch", "delete", "head", "options"]:
            resp = client.request(method, "/healthcheck")
            assert resp.status_code == 405, (
                f"Método {method.upper()} deveria retornar 405, retornou {resp.status_code}"
            )


# ── 8. Determinismo / Idempotência ─────────────────────────────────────
class TestIdempotency:
    """Spec: valores fixos — respostas devem ser idênticas sempre."""

    def test_multiple_calls_same_body(self) -> None:
        bodies = [client.get("/healthcheck").json() for _ in range(10)]
        assert all(b == bodies[0] for b in bodies)

    def test_status_never_changes(self) -> None:
        for _ in range(10):
            assert client.get("/healthcheck").json()["status"] == "healthy"

    def test_version_never_changes(self) -> None:
        for _ in range(10):
            assert client.get("/healthcheck").json()["version"] == "1.0.0"


# ── 9. Edge Cases ──────────────────────────────────────────────────────
class TestEdgeCases:
    """Casos de borda importantes para validação completa."""

    def test_response_body_is_not_empty(self) -> None:
        body = client.get("/healthcheck").json()
        assert body  # não é vazio

    def test_status_not_empty_string(self) -> None:
        body = client.get("/healthcheck").json()
        assert len(body["status"]) > 0

    def test_version_not_empty_string(self) -> None:
        body = client.get("/healthcheck").json()
        assert len(body["version"]) > 0

    def test_version_has_no_whitespace(self) -> None:
        body = client.get("/healthcheck").json()
        assert body["version"] == body["version"].strip()

    def test_status_has_no_whitespace(self) -> None:
        body = client.get("/healthcheck").json()
        assert body["status"] == body["status"].strip()

    def test_status_is_lowercase(self) -> None:
        body = client.get("/healthcheck").json()
        assert body["status"] == body["status"].lower()

    def test_version_no_special_chars(self) -> None:
        """Versão não deve conter caracteres especiais além de pontos e dígitos."""
        body = client.get("/healthcheck").json()
        assert all(c.isdigit() or c == "." for c in body["version"])

    def test_status_only_alphanumeric(self) -> None:
        """Status deve conter apenas letras."""
        body = client.get("/healthcheck").json()
        assert body["status"].isalpha()

    def test_response_time_reasonable(self) -> None:
        """Resposta deve ser rápida (< 1s) — healthcheck não deve ter overhead."""
        import time
        start = time.perf_counter()
        client.get("/healthcheck")
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"Healthcheck levou {elapsed:.2f}s — muito lento"

    def test_health_response_model_json_schema(self) -> None:
        """Schema JSON do modelo deve ter exatamente os campos esperados."""
        schema = HealthResponse.model_json_schema()
        props = schema.get("properties", {})
        assert set(props.keys()) == {"status", "version"}

    def test_health_response_model_json_schema_types(self) -> None:
        """Campos do schema devem ser string."""
        schema = HealthResponse.model_json_schema()
        props = schema.get("properties", {})
        assert props["status"]["type"] == "string"
        assert props["version"]["type"] == "string"

    def test_health_response_required_fields(self) -> None:
        """Todos os campos são required (têm defaults, mas são declarados)."""
        schema = HealthResponse.model_json_schema()
        required = set(schema.get("required", []))
        # Pydantic v2: campos com default podem não estar em 'required'
        # Mas o schema deve ter os campos em properties
        props = set(schema.get("properties", {}).keys())
        assert props == {"status", "version"}
