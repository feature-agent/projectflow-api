"""Tests for the task due date feature.

Feature: Add due date to tasks.

Clarifications:
- Due dates are date_only (no time component).
- Due dates are fully_mutable (can be set, changed, or removed after creation).
- When a task's due date passes, the task's status auto-changes (auto_status_change).
"""

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.task import Task
from app.models.user import User


@pytest.mark.asyncio
async def test_create_task_with_due_date(
    client: AsyncClient, test_project: Project
) -> None:
    """A user can set a due date when creating a task."""
    due = (date.today() + timedelta(days=7)).isoformat()
    payload = {
        "title": "Task with due date",
        "description": "desc",
        "project_id": str(test_project.id),
        "due_date": due,
    }
    resp = await client.post("/tasks", json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "due_date" in body, "Response must include due_date field"
    assert body["due_date"] == due


@pytest.mark.asyncio
async def test_create_task_without_due_date_is_allowed(
    client: AsyncClient, test_project: Project
) -> None:
    """Due date is optional when creating a task."""
    payload = {
        "title": "Task without due date",
        "project_id": str(test_project.id),
    }
    resp = await client.post("/tasks", json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "due_date" in body
    assert body["due_date"] is None


@pytest.mark.asyncio
async def test_get_task_returns_due_date(
    client: AsyncClient, test_project: Project
) -> None:
    """A user can view the due date on a task."""
    due = (date.today() + timedelta(days=3)).isoformat()
    create_resp = await client.post(
        "/tasks",
        json={
            "title": "View due date",
            "project_id": str(test_project.id),
            "due_date": due,
        },
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    get_resp = await client.get(f"/tasks/{task_id}")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["due_date"] == due


@pytest.mark.asyncio
async def test_list_tasks_includes_due_date(
    client: AsyncClient, test_project: Project
) -> None:
    """Listed tasks include their due dates."""
    due = (date.today() + timedelta(days=10)).isoformat()
    await client.post(
        "/tasks",
        json={
            "title": "Listed task",
            "project_id": str(test_project.id),
            "due_date": due,
        },
    )
    resp = await client.get("/tasks")
    assert resp.status_code == 200
    tasks = resp.json()["tasks"]
    assert len(tasks) >= 1
    matching = [t for t in tasks if t["title"] == "Listed task"]
    assert len(matching) == 1
    assert matching[0]["due_date"] == due


@pytest.mark.asyncio
async def test_update_task_set_due_date(
    client: AsyncClient, test_project: Project
) -> None:
    """A due date can be set on a task that previously had none."""
    create_resp = await client.post(
        "/tasks",
        json={"title": "No due yet", "project_id": str(test_project.id)},
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]
    assert create_resp.json()["due_date"] is None

    new_due = (date.today() + timedelta(days=5)).isoformat()
    update_resp = await client.put(
        f"/tasks/{task_id}", json={"due_date": new_due}
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["due_date"] == new_due


@pytest.mark.asyncio
async def test_update_task_change_due_date(
    client: AsyncClient, test_project: Project
) -> None:
    """An existing due date can be changed."""
    original_due = (date.today() + timedelta(days=2)).isoformat()
    create_resp = await client.post(
        "/tasks",
        json={
            "title": "Change due",
            "project_id": str(test_project.id),
            "due_date": original_due,
        },
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    new_due = (date.today() + timedelta(days=20)).isoformat()
    update_resp = await client.put(
        f"/tasks/{task_id}", json={"due_date": new_due}
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["due_date"] == new_due
    assert update_resp.json()["due_date"] != original_due


@pytest.mark.asyncio
async def test_update_task_remove_due_date(
    client: AsyncClient, test_project: Project
) -> None:
    """A due date can be removed by setting it to null."""
    original_due = (date.today() + timedelta(days=2)).isoformat()
    create_resp = await client.post(
        "/tasks",
        json={
            "title": "Remove due",
            "project_id": str(test_project.id),
            "due_date": original_due,
        },
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]
    assert create_resp.json()["due_date"] == original_due

    update_resp = await client.put(
        f"/tasks/{task_id}", json={"due_date": None}
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["due_date"] is None

    # Confirm via GET
    get_resp = await client.get(f"/tasks/{task_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["due_date"] is None


@pytest.mark.asyncio
async def test_due_date_is_date_only_not_datetime(
    client: AsyncClient, test_project: Project
) -> None:
    """Due dates are date-only; sending a datetime should fail or be coerced to date-only.

    Per the clarification, due dates do not include a specific time.
    """
    payload_with_datetime = {
        "title": "Datetime due",
        "project_id": str(test_project.id),
        "due_date": "2030-06-15T13:45:00Z",
    }
    resp = await client.post("/tasks", json=payload_with_datetime)
    # Either rejected (422) or the time is stripped and only the date is stored.
    if resp.status_code == 201:
        body = resp.json()
        assert body["due_date"] == "2030-06-15", (
            f"Expected date-only value, got {body['due_date']!r}"
        )
    else:
        assert resp.status_code == 422

    # Pure date input must always work.
    good_payload = {
        "title": "Date due",
        "project_id": str(test_project.id),
        "due_date": "2030-06-15",
    }
    good_resp = await client.post("/tasks", json=good_payload)
    assert good_resp.status_code == 201, good_resp.text
    assert good_resp.json()["due_date"] == "2030-06-15"


@pytest.mark.asyncio
async def test_due_date_persisted_on_model(
    db_session: AsyncSession, test_project: Project
) -> None:
    """Due date is stored with task data on the ORM model."""
    due = date.today() + timedelta(days=14)
    task = Task(
        id=uuid.uuid4(),
        title="Persisted due",
        description="d",
        status="todo",
        priority="medium",
        project_id=test_project.id,
        due_date=due,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    assert hasattr(task, "due_date"), "Task model must have a due_date attribute"
    assert task.due_date == due
    # Ensure it's a date, not a datetime.
    assert isinstance(task.due_date, date)
    assert not isinstance(task.due_date, datetime)
