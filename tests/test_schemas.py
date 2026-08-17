import pytest
from pydantic import ValidationError

from schemas import TaskCreate, TaskUpdate


def test_task_create_requires_title():
    with pytest.raises(ValidationError):
        TaskCreate()


def test_task_create_defaults_status_and_description():
    task = TaskCreate(title="Nova tarefa")

    assert task.status == "pending"
    assert task.description is None


def test_task_create_accepts_valid_fields():
    task = TaskCreate(title="Nova tarefa", description="Detalhes", status="done")

    assert task.title == "Nova tarefa"
    assert task.description == "Detalhes"
    assert task.status == "done"


@pytest.mark.parametrize("title", ["", "a" * 101])
def test_task_create_title_length_is_validated(title):
    with pytest.raises(ValidationError):
        TaskCreate(title=title)


def test_task_create_description_length_is_validated():
    with pytest.raises(ValidationError):
        TaskCreate(title="ok", description="a" * 1001)


def test_task_create_status_enum_is_validated():
    with pytest.raises(ValidationError):
        TaskCreate(title="ok", status="invalid")


def test_task_update_requires_title_and_status():
    with pytest.raises(ValidationError):
        TaskUpdate(title="ok")

    with pytest.raises(ValidationError):
        TaskUpdate(status="pending")

    with pytest.raises(ValidationError):
        TaskUpdate()


def test_task_update_accepts_valid_payload():
    task = TaskUpdate(title="Atualizada", description=None, status="done")

    assert task.status == "done"
    assert task.description is None
