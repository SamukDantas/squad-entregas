from datetime import datetime

import pytest
from fastapi.testclient import TestClient

import db
from app import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _is_iso8601_utc(value: str) -> bool:
    parsed = datetime.fromisoformat(value)
    return parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0


def _post_task(
    client,
    title="Estudar FastAPI",
    description="Ler documentação",
    status="pending",
):
    payload = {"title": title}
    if description is not None:
        payload["description"] = description
    if status is not None:
        payload["status"] = status
    return client.post("/tasks", json=payload)


# ---------------------------------------------------------------------------
# GET /tasks
# ---------------------------------------------------------------------------


def test_list_tasks_returns_empty_page_by_default(client):
    response = client.get("/tasks")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "page": 1,
        "page_size": 10,
        "total": 0,
        "total_pages": 0,
    }


def test_list_tasks_filters_by_status(client):
    _post_task(client, title="Pending 1", status="pending")
    _post_task(client, title="Done 1", status="done")
    _post_task(client, title="In progress 1", status="in_progress")

    response = client.get("/tasks", params={"status": "pending"})

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Pending 1"
    assert all(item["status"] == "pending" for item in data["items"])


def test_list_tasks_rejects_invalid_status(client):
    response = client.get("/tasks", params={"status": "invalid"})

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


def test_list_tasks_paginates(client):
    for i in range(1, 13):
        _post_task(client, title=f"Tarefa {i}", status="pending")

    response = client.get("/tasks", params={"page": 2, "page_size": 10})

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["page_size"] == 10
    assert data["total"] == 12
    assert data["total_pages"] == 2
    assert len(data["items"]) == 2
    assert [item["id"] for item in data["items"]] == [11, 12]


def test_list_tasks_page_beyond_total_returns_empty_items(client):
    _post_task(client, title="Única", status="pending")

    response = client.get("/tasks", params={"page": 2, "page_size": 10})

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 1
    assert data["total_pages"] == 1


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page": -1},
        {"page_size": 0},
        {"page_size": -1},
        {"page_size": 101},
        {"page": "abc"},
        {"page_size": "abc"},
    ],
)
def test_list_tasks_rejects_invalid_pagination_params(client, params):
    response = client.get("/tasks", params=params)

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


# ---------------------------------------------------------------------------
# GET /tasks/{task_id}
# ---------------------------------------------------------------------------


def test_get_task_by_id(client):
    created = _post_task(client).json()

    response = client.get(f"/tasks/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_task_not_found(client):
    response = client.get("/tasks/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_get_task_invalid_id(client):
    response = client.get("/tasks/abc")

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


# ---------------------------------------------------------------------------
# POST /tasks
# ---------------------------------------------------------------------------


def test_create_task_with_all_fields(client):
    response = _post_task(client)

    assert response.status_code == 201
    task = response.json()
    assert task["title"] == "Estudar FastAPI"
    assert task["description"] == "Ler documentação"
    assert task["status"] == "pending"
    assert isinstance(task["id"], int)
    assert _is_iso8601_utc(task["created_at"])
    assert _is_iso8601_utc(task["updated_at"])


def test_create_task_defaults_status_to_pending(client):
    response = client.post("/tasks", json={"title": "Sem status"})

    assert response.status_code == 201
    task = response.json()
    assert task["status"] == "pending"
    assert task["description"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": ""},
        {"title": "a" * 101},
        {"title": None},
        {"title": "ok", "description": "a" * 1001},
        {"title": "ok", "status": "invalid"},
    ],
)
def test_create_task_rejects_invalid_payloads(client, payload):
    response = client.post("/tasks", json=payload)

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


# ---------------------------------------------------------------------------
# PUT /tasks/{task_id}
# ---------------------------------------------------------------------------


def test_update_task_replaces_fields(client):
    created = _post_task(client).json()

    response = client.put(
        f"/tasks/{created['id']}",
        json={"title": "Atualizada", "description": "Nova descrição", "status": "done"},
    )

    assert response.status_code == 200
    task = response.json()
    assert task["id"] == created["id"]
    assert task["title"] == "Atualizada"
    assert task["description"] == "Nova descrição"
    assert task["status"] == "done"
    assert task["created_at"] == created["created_at"]
    assert _is_iso8601_utc(task["updated_at"])


def test_update_task_updates_updated_at(client, monkeypatch):
    created = _post_task(client).json()
    fixed_now = "2025-01-02T12:34:56+00:00"

    monkeypatch.setattr(db, "_now", lambda: fixed_now)

    response = client.put(
        f"/tasks/{created['id']}",
        json={"title": "Atualizada", "status": "done"},
    )

    assert response.status_code == 200
    task = response.json()
    assert task["updated_at"] == fixed_now
    assert task["created_at"] == created["created_at"]


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "Sem status"},
        {"status": "pending"},
        {},
        {"title": "", "status": "pending"},
        {"title": "ok", "status": "invalid"},
    ],
)
def test_update_task_rejects_invalid_payloads(client, payload):
    created = _post_task(client).json()

    response = client.put(f"/tasks/{created['id']}", json=payload)

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


def test_update_task_not_found(client):
    response = client.put("/tasks/999", json={"title": "X", "status": "pending"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_update_task_invalid_id(client):
    response = client.put("/tasks/abc", json={"title": "X", "status": "pending"})

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


# ---------------------------------------------------------------------------
# DELETE /tasks/{task_id}
# ---------------------------------------------------------------------------


def test_delete_task_returns_no_content_and_removes(client):
    created = _post_task(client).json()

    response = client.delete(f"/tasks/{created['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/tasks/{created['id']}").status_code == 404


def test_delete_task_not_found(client):
    response = client.delete("/tasks/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_delete_task_invalid_id(client):
    response = client.delete("/tasks/abc")

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
