#!/usr/bin/env python3
"""Teste de integração do HealthcheckClient contra o servidor real.

Este script NÃO usa TestClient do FastAPI — ele realmente se conecta
ao servidor via HTTP, validando a ponta a ponta.

Uso
---
1. Iniciar o servidor: ``uvicorn app.main:app --reload``
2. Executar:            ``python examples/healthcheck_integration_test.py``

Se tudo estiver OK, imprime "Todos os testes passaram!".
Caso contrário, levanta AssertionError.
"""

from client import HealthcheckClient


BASE_URL = "http://localhost:8000"


def test_healthcheck_returns_healthy_status() -> None:
    """Valida que o campo 'status' é 'healthy'."""
    client = HealthcheckClient(base_url=BASE_URL)
    response = client.healthcheck()
    assert response.status == "healthy", f"Esperado 'healthy', obtido '{response.status}'"
    print("  PASS  status == 'healthy'")


def test_healthcheck_returns_version() -> None:
    """Valida que o campo 'version' está presente e não é vazio."""
    client = HealthcheckClient(base_url=BASE_URL)
    response = client.healthcheck()
    assert response.version, "Versão não deve ser vazia"
    print(f"  PASS  version == '{response.version}'")


def test_is_healthy_helper() -> None:
    """Valida que o helper is_healthy retorna True quando a API está OK."""
    client = HealthcheckClient(base_url=BASE_URL)
    assert client.is_healthy() is True
    print("  PASS  is_healthy() == True")


def test_is_healthy_returns_false_when_server_down() -> None:
    """Valida que is_healthy retorna False quando o servidor está indisponível."""
    bad_client = HealthcheckClient(base_url="http://localhost:19999")
    assert bad_client.is_healthy() is False
    print("  PASS  is_healthy() == False (servidor indisponível)")


def main() -> None:
    print("Rodando testes de integração do HealthcheckClient...\n")

    test_healthcheck_returns_healthy_status()
    test_healthcheck_returns_version()
    test_is_healthy_helper()
    test_is_healthy_returns_false_when_server_down()

    print("\nTodos os testes passaram!")


if __name__ == "__main__":
    main()
