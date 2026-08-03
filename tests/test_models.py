"""Testes do modelo Pydantic HealthResponse.

Cobertura
---------
- Instanciação com valores padrão
- Serialização para dict / JSON
- Validação de tipos
- Imutabilidade dos campos (defaults são strings)
- Re-export em client.models aponta para a mesma classe
- Validação com valores customizados (via construtor)
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.models import HealthResponse
from client.models import HealthResponse as ClientHealthResponse


# ── Instanciação com Defaults ──────────────────────────────────────────
class TestDefaults:
    """HealthResponse deve criar instâncias com valores fixos por padrão."""

    def test_default_status(self) -> None:
        hr = HealthResponse()
        assert hr.status == "healthy"

    def test_default_version(self) -> None:
        hr = HealthResponse()
        assert hr.version == "1.0.0"

    def test_no_arguments_needed(self) -> None:
        hr = HealthResponse()
        assert hr is not None


# ── Serialização ───────────────────────────────────────────────────────
class TestSerialization:
    """Valida serialização para dict e JSON."""

    def test_to_dict(self) -> None:
        hr = HealthResponse()
        assert hr.model_dump() == {"status": "healthy", "version": "1.0.0"}

    def test_to_json_string(self) -> None:
        hr = HealthResponse()
        dumped = json.loads(hr.model_dump_json())
        assert dumped == {"status": "healthy", "version": "1.0.0"}

    def test_json_string_matches_expected(self) -> None:
        hr = HealthResponse()
        raw = hr.model_dump_json()
        assert '"status":"healthy"' in raw
        assert '"version":"1.0.0"' in raw

    def test_dict_has_exactly_two_keys(self) -> None:
        hr = HealthResponse()
        assert set(hr.model_dump().keys()) == {"status", "version"}


# ── Validação de Tipos ────────────────────────────────────────────────
class TestTypeValidation:
    """Campos devem ser strings — outros tipos devem falhar."""

    def test_status_must_be_string(self) -> None:
        with pytest.raises(ValidationError):
            HealthResponse(status=123)  # type: ignore[arg-type]

    def test_version_must_be_string(self) -> None:
        with pytest.raises(ValidationError):
            HealthResponse(version=2.0)  # type: ignore[arg-type]

    def test_status_none_fails(self) -> None:
        with pytest.raises(ValidationError):
            HealthResponse(status=None)  # type: ignore[arg-type]


# ── Construtor com valores customizados ────────────────────────────────
class TestCustomValues:
    """O modelo aceita valores customizados quando fornecidos."""

    def test_custom_status(self) -> None:
        hr = HealthResponse(status="unhealthy")
        assert hr.status == "unhealthy"

    def test_custom_version(self) -> None:
        hr = HealthResponse(version="2.0.0")
        assert hr.version == "2.0.0"

    def test_custom_both(self) -> None:
        hr = HealthResponse(status="degraded", version="0.1.0")
        assert hr.status == "degraded"
        assert hr.version == "0.1.0"


# ── Re-export (client.models) ──────────────────────────────────────────
class TestClientModelReExport:
    """client.models.HealthResponse deve ser a mesma classe de app.models."""

    def test_same_class(self) -> None:
        assert ClientHealthResponse is HealthResponse

    def test_client_model_works(self) -> None:
        hr = ClientHealthResponse()
        assert hr.status == "healthy"
        assert hr.version == "1.0.0"


# ── Igualdade ──────────────────────────────────────────────────────────
class TestEquality:
    """Duas instâncias com os mesmos valores devem ser iguais."""

    def test_equal_instances(self) -> None:
        hr1 = HealthResponse()
        hr2 = HealthResponse()
        assert hr1 == hr2

    def test_different_status_not_equal(self) -> None:
        hr1 = HealthResponse(status="healthy")
        hr2 = HealthResponse(status="unhealthy")
        assert hr1 != hr2
