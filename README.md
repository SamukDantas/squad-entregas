# Healthcheck API

Endpoint simples de healthcheck usando FastAPI.

## Estrutura

```
.
├── main.py       # Aplicação FastAPI com rota /healthcheck
└── README.md
```

## Execução

```bash
uvicorn main:app --reload
```

A API estará disponível em `http://127.0.0.1:8000`.

## Endpoint

### `GET /healthcheck`

Retorna o status de saúde da aplicação.

**Response 200:**
```json
{"status": "ok"}
```
