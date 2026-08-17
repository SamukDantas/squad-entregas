# API REST de Gerenciamento de Tarefas

API REST para CRUD completo de tarefas, com persistência em SQLite, validação de
entrada (Pydantic), filtro por status e paginação na listagem.

## Estrutura

```
app.py        # Inicialização do FastAPI e inclusão das rotas
db.py         # Conexão SQLite, criação do schema e funções de acesso a dados
schemas.py    # Modelos Pydantic (validação e contratos de resposta)
routes.py     # Endpoints REST
tasks.db      # Banco SQLite (gerado automaticamente na primeira execução)
```

## Requisitos

- Python 3.12+
- Bibliotecas: `fastapi`, `pydantic` (já instaladas no ambiente)

## Como executar

```bash
uvicorn app:app --reload
# ou
python -m uvicorn app:app --reload
```

A documentação interativa (OpenAPI/Swagger) fica disponível em
`http://127.0.0.1:8000/docs`.

O banco SQLite é criado automaticamente em `tasks.db` (mesmo diretório do
projeto). Para usar outro caminho, defina a variável de ambiente `TASKS_DB_PATH`.

## Endpoints

| Método | Rota                  | Descrição                                  |
|--------|-----------------------|--------------------------------------------|
| GET    | `/tasks`              | Lista tarefas (filtro por status + paginação) |
| GET    | `/tasks/{task_id}`    | Obtém uma tarefa por ID                     |
| POST   | `/tasks`              | Cria uma nova tarefa                        |
| PUT    | `/tasks/{task_id}`    | Substitui uma tarefa por completo           |
| DELETE | `/tasks/{task_id}`    | Exclui uma tarefa                           |

### Listagem (`GET /tasks`)

Query params:

- `status` (opcional): `pending`, `in_progress` ou `done`.
- `page` (opcional, default `1`): inteiro >= 1.
- `page_size` (opcional, default `10`, máx. `100`): inteiro >= 1.

### Criar/atualizar (`POST` / `PUT`)

Campos do corpo:

- `title` (obrigatório): string de 1 a 100 caracteres.
- `description` (opcional): string de até 1000 caracteres.
- `status` (opcional no `POST`, default `pending`; obrigatório no `PUT`):
  `pending`, `in_progress` ou `done`.

## Modelo de dados

Tabela `tasks`:

| Coluna       | Tipo    | Restrições                                              |
|--------------|---------|---------------------------------------------------------|
| `id`         | INTEGER | PK autoincremento                                       |
| `title`      | TEXT    | NOT NULL, 1–100 caracteres                              |
| `description`| TEXT    | opcional, máx. 1000 caracteres                          |
| `status`     | TEXT    | NOT NULL, `pending` / `in_progress` / `done`            |
| `created_at` | TEXT    | NOT NULL, ISO-8601 em UTC                               |
| `updated_at` | TEXT    | NOT NULL, ISO-8601 em UTC                               |

## Testes

A suíte de testes é executada pelo pipeline de qualidade; não há scripts de
teste neste repositório.
