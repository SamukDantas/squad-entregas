#!/usr/bin/env python3
"""Exemplo de uso do HealthcheckClient (modo síncrono).

Pré-requisitos
--------------
1. Instalar dependências:  ``pip install fastapi uvicorn httpx``
2. Iniciar o servidor:     ``uvicorn app.main:app --reload``
3. Executar este script:   ``python examples/healthcheck_example.py``

Saída esperada
--------------
  [OK] API saudável — status=healthy, version=1.0.0
"""

from client import HealthcheckClient


def main() -> None:
    # ------------------------------------------------------------------
    # 1. Criar o cliente apontando para o servidor local
    # ------------------------------------------------------------------
    client = HealthcheckClient(base_url="http://localhost:8000")

    # ------------------------------------------------------------------
    # 2. Chamar o endpoint de healthcheck
    # ------------------------------------------------------------------
    response = client.healthcheck()

    # ------------------------------------------------------------------
    # 3. Tratar a resposta usando o modelo Pydantic
    # ------------------------------------------------------------------
    print(f"[OK] API saudável — status={response.status}, version={response.version}")

    # ------------------------------------------------------------------
    # 4. Usar o helper de conveniência
    # ------------------------------------------------------------------
    if client.is_healthy():
        print("[OK] O servidor está operacional.")
    else:
        print("[ERRO] O servidor NÃO está operacional.")


if __name__ == "__main__":
    main()
