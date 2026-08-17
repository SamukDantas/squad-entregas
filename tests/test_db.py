import db


def test_create_and_get_task():
    task = db.create_task("Título", "Descrição", "pending")

    assert task["id"] == 1
    assert task["title"] == "Título"
    assert task["description"] == "Descrição"
    assert task["status"] == "pending"

    assert db.get_task(task["id"]) == task


def test_list_tasks_filter_and_pagination():
    for i in range(1, 6):
        status = "pending" if i % 2 == 1 else "done"
        db.create_task(f"Tarefa {i}", None, status)

    items, total = db.list_tasks(status="pending", page=2, page_size=2)

    assert total == 3
    assert len(items) == 1
    assert items[0]["title"] == "Tarefa 5"
    assert all(item["status"] == "pending" for item in items)


def test_update_task():
    task = db.create_task("Antes", None, "pending")

    updated = db.update_task(task["id"], "Depois", "Desc", "done")

    assert updated["title"] == "Depois"
    assert updated["description"] == "Desc"
    assert updated["status"] == "done"
    assert updated["created_at"] == task["created_at"]


def test_update_missing_task_returns_none():
    assert db.update_task(999, "X", None, "pending") is None


def test_delete_task():
    task = db.create_task("Remover", None, "pending")

    assert db.delete_task(task["id"]) is True
    assert db.get_task(task["id"]) is None


def test_delete_missing_task_returns_false():
    assert db.delete_task(999) is False
