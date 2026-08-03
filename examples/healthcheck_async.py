#!/usr/bin/env python3
"""Exemplo de uso do HealthcheckClient (modo assíncrono).

Pré-requisitos
--------------
1. Instalar dependências:  ``pip install fastapi uvicorn httpx``
2. Iniciar o servidor:     ``uvicorn app.main:app --reload``
3. Executar este script:   ``python examples/healthcheck_async.py``

Saída esperada
--------------
  [OK] API saudável (async) — status=healthy, version=1.0.0
"""

import asyncio

from client import HealthcheckClient


async def main() -> None:
    # ------------------------------------------------------------------
    # 1. Criar o cliente assíncrono
    # ------------------------------------------------------------------
    client = HealthcheckClient(base_url="http://localhost:8000")

    # ------------------------------------------------------------------
    # 2. Chamar o endpoint de healthcheck de forma assíncrona
    # ------------------------------------------------------------------
    response = await client.ahealthcheck()

    # ------------------------------------------------------------------
    # 3. Tratar a resposta
    # ------------------------------------------------------------------
    print(f"[OK] API saudável (async) — status={response.status}, version={response.version}")


if __name__ == "__main__":
    asyncio.run(main())
