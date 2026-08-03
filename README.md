# Healthcheck App

## Estrutura

```
app.py            - Aplicacao principal FastAPI
healthcheck.py    - Modulo isolado com logica de healthcheck
README.md
```

## Execucao

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Teste

```bash
curl http://localhost:8000/healthcheck
```

## Endpoints

### GET /healthcheck

Retorna o status do sistema.

**200 OK:**
```json
{ "status": "ok", "version": "1.0.0", "timestamp": "2024-01-15T10:30:00Z" }
```

**503 Service Unavailable:**
```json
{ "status": "error", "version": "1.0.0", "timestamp": "2024-01-15T10:30:00Z" }
```

## Decisoes de Implementacao

### Formato do Timestamp
A spec sugere `datetime.utcnow().isoformat() + "Z"` como exemplo, porem a implementacao
utiliza `datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")`. Esta abordagem
e preferivel pois usa objetos datetime timezone-aware, evitando ambiguidades de fuso horario
e seguindo as recomendacoes do Python (utcnow() e obsoleto desde Python 3.12).
