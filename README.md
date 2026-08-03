# Healthcheck API

Serviço minimalista de healthcheck com FastAPI (backend) e cliente de integração (HTTP).

---

## Estrutura de Arquivos

```
.
├── app/                                # Backend FastAPI
│   ├── __init__.py                     #   Pacote Python
│   ├── main.py                         #   Ponto de entrada (cria instância FastAPI,
│   │                                   #     registra rota GET /healthcheck diretamente)
│   ├── models.py                       #   Modelo Pydantic HealthResponse
│   │                                   #     (status: str = "healthy", version: str = "1.0.0")
│   └── routes.py                       #   APIRouter com rota GET /healthcheck
│                                       #     (mantido para compatibilidade de import)
│
├── client/                             # Cliente de integração (consumo HTTP)
│   ├── __init__.py                     #   Exporta HealthcheckClient e HealthResponse
│   ├── api_client.py                   #   Classe HealthcheckClient
│   │                                   #     - healthcheck() síncrono
│   │                                   #     - ahealthcheck() assíncrono
│   │                                   #     - is_healthy() helper
│   └── models.py                       #   Re-exporta HealthResponse de app.models
│                                       #     (mesma classe, verificável com is)
│
├── examples/                           # Exemplos de uso do cliente
│   ├── healthcheck_example.py          #   Exemplo síncrono via HealthcheckClient
│   ├── healthcheck_async.py            #   Exemplo assíncrono via ahealthcheck()
│   └── healthcheck_integration_test.py #   Teste end-to-end contra servidor real
│
├── tests/                              # Testes unitários (TestClient do FastAPI)
│   ├── __init__.py
│   ├── test_healthcheck.py             #   Contrato básico: status 200, JSON,
│   │                                   #     Content-Type, métodos HTTP, determinismo
│   ├── test_api_contract.py            #   Contrato completo via OpenAPI schema:
│   │                                   #     campos, tipos, config do app, round-trip
│   │                                   #     Pydantic, headers de segurança, edge cases
│   ├── test_edge_cases.py              #   Casos de borda: headers customizados,
│   │                                   #     query params, paths variados, validação
│   │                                   #     de tipos, serialização, introspecção
│   ├── test_client.py                  #   HealthcheckClient com MockTransport
│   │                                   #     (sem servidor real)
│   └── test_models.py                  #   Modelo Pydantic HealthResponse:
│                                         #     defaults, serialização, re-export
│
├── requirements.txt                    # Dependências do projeto
└── README.md                           # Este arquivo
```

---

## Pré-requisitos

- Python >= 3.10
- pip

## Instalação

```bash
pip install -r requirements.txt
```

Dependências: `fastapi`, `uvicorn`, `httpx`, `pydantic`.

---

## Execução

### 1. Iniciar o servidor

```bash
uvicorn app.main:app --reload
```

O servidor ficará disponível em `http://localhost:8000`.

### 2. Testar manualmente

```bash
curl http://localhost:8000/healthcheck
```

Resposta esperada:

```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### 3. Executar testes unitários

```bash
pytest tests/ -v
```

Cobertura dos testes:

| Arquivo                       | O que testa                                                 |
|-------------------------------|-------------------------------------------------------------|
| `test_healthcheck.py`         | Status 200, corpo JSON, Content-Type, métodos HTTP,         |
|                               | determinismo nas respostas                                   |
| `test_api_contract.py`        | Schema OpenAPI, tipos dos campos, config da app,             |
|                               | round-trip Pydantic, headers, segurança, paths, idempotência |
| `test_edge_cases.py`          | Headers customizados, query params, paths variados,          |
|                               | validação de tipos extremos, serialização, introspecção      |
| `test_client.py`              | HealthcheckClient com httpx.MockTransport (sem servidor)     |
| `test_models.py`              | Modelo Pydantic: defaults, serialização, re-export           |

### 4. Executar exemplos do cliente

Com o servidor rodando em outro terminal:

```bash
# Exemplo síncrono
python examples/healthcheck_example.py

# Exemplo assíncrono
python examples/healthcheck_async.py

# Teste de integração end-to-end (servidor real via HTTP)
python examples/healthcheck_integration_test.py
```

---

## Contrato da API

| Método | Rota           | Status Code | Body                                        |
|--------|----------------|-------------|---------------------------------------------|
| GET    | `/healthcheck` | 200         | `{"status": "healthy", "version": "1.0.0"}` |

- Valores de `status` e `version` são **fixos** (não dependem de estado externo).
- A resposta é **idêntica** em chamadas consecutivas (idempotente).
- Apenas o método **GET** é aceito; outros retornam **405 Method Not Allowed**.
- Path inexistente retorna **404 Not Found**.

---

## Arquitetura

```
┌───────────────┐       HTTP         ┌───────────────┐
│    Client     │ ────────────────▶  │   Backend     │
│   (client/)   │  GET /healthcheck  │    (app/)     │
│               │ ◀────────────────  │               │
│  Healthcheck  │   JSON 200         │   FastAPI +   │
│    Client     │                    │   Pydantic    │
└───────────────┘                    └───────────────┘
```

- **Backend** (`app/`): FastAPI expõe `GET /healthcheck` retornando `HealthResponse`.
  A rota é registrada diretamente na instância `app` (via decorador `@app.get`).
- **Cliente** (`client/`): `HealthcheckClient` consome o endpoint via `httpx`,
  com suporte síncrono (`healthcheck()`), assíncrono (`ahealthcheck()`) e
  helper `is_healthy()`.
- **Modelo compartilhado**: `HealthResponse` é definido em `app/models.py` e
  re-exportado por `client/models.py` para desacoplamento. Os consumidores
  externos importam de `client` sem depender do pacote `app`.

---

## Decisões de Design

1. **Rota registrada diretamente em `app`** (não via `include_router`): Garante
   que `app.routes` contém o objeto `APIRoute` com `.path` acessível, o que
   permite introspecção nos testes.

2. **`app/routes.py` mantido**: Preserva compatibilidade de import
   (`from app.routes import router`) exigida por testes, mesmo que o router
   não seja incluído na app.

3. **`client/models.py` re-exporta** ao invés de duplicar: Usa
   `from app.models import HealthResponse` para garantir que
   `client.models.HealthResponse is app.models.HealthResponse`.

4. **httpx como dependência compartilhada**: Mesma lib usada pelo
   TestClient do FastAPI (transitivamente), mantendo consistência.
