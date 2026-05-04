"""Tests for the task due date feature."""

import uuid

import pytest
from httpx import AsyncClient

from app.models.project import Project
from app.models.task import Task


@pytest.mark.asyncio
async def test_create_task_with_due_date(client: AsyncClient, test_project: Project) -> None:
    """Users can assign a due date when creating a task."""
    payload = {
        "title": "Task with due date",
        "description": "A task that has a due date",
        "project_id": str(test_project.id),
        "due_date": "2025-12-31",
    }
    response = await client.post("/tasks", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert "due_date" in data
    assert data["due_date"] == "2025-12-31"


@pytest.mark.asyncio
async def test_create_task_without_due_date(
    client: AsyncClient, test_project: Project
) -> None:
    """Due date is optional when creating a task."""
    payload = {
        "title": "No due date task",
        "project_id": str(test_project.id),
    }
    response = await client.post("/tasks", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert "due_date" in data
    assert data["due_date"] is None


@pytest.mark.asyncio
async def test_get_task_returns_due_date(
    client: AsyncClient, test_project: Project
) -> None:
    """Users can view the due date on task details."""
    create_payload = {
        "title": "View due date",
        "project_id": str(test_project.id),
        "due_date": "2026-01-15",
    }
    create_resp = await client.post("/tasks", json=create_payload)
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    get_resp = await client.get(f"/tasks/{task_id}")
    assert get_resp.status_code == 200, get_resp.text
    data = get_resp.json()
    assert data["due_date"] == "2026-01-15"


@pytest.mark.asyncio
async def test_update_task_set_due_date(client: AsyncClient, test_task: Task) -> None:
    """Users can add a due date to an existing task."""
    response = await client.put(
        f"/tasks/{test_task.id}",
        json={"due_date": "2025-11-20"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["due_date"] == "2025-11-20"


@pytest.mark.asyncio
async def test_update_task_change_due_date(
    client: AsyncClient, test_project: Project
) -> None:
    """Users can modify the due date of a task."""
    create_resp = await client.post(
        "/tasks",
        json={
            "title": "Modify date",
            "project_id": str(test_project.id),
            "due_date": "2025-06-01",
        },
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/tasks/{task_id}",
        json={"due_date": "2025-07-15"},
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["due_date"] == "2025-07-15"

    get_resp = await client.get(f"/tasks/{task_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["due_date"] == "2025-07-15"


@pytest.mark.asyncio
async def test_update_task_remove_due_date(
    client: AsyncClient, test_project: Project
) -> None:
    """Users can remove the due date from a task by setting it to null."""
    create_resp = await client.post(
        "/tasks",
        json={
            "title": "Remove date",
            "project_id": str(test_project.id),
            "due_date": "2025-08-10",
        },
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]
    assert create_resp.json()["due_date"] == "2025-08-10"

    update_resp = await client.put(
        f"/tasks/{task_id}",
        json={"due_date": None},
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["due_date"] is None

    get_resp = await client.get(f"/tasks/{task_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["due_date"] is None


@pytest.mark.asyncio
async def test_list_tasks_includes_due_date(
    client: AsyncClient, test_project: Project
) -> None:
    """Listed tasks expose due_date."""
    await client.post(
        "/tasks",
        json={
            "title": "Listed task",
            "project_id": str(test_project.id),
            "due_date": "2025-09-09",
        },
    )
    resp = await client.get("/tasks")
    assert resp.status_code == 200
    tasks = resp.json()["tasks"]
    assert len(tasks) >= 1
    found = [t for t in tasks if t["title"] == "Listed task"]
    assert found, "created task missing from list"
    assert found[0]["due_date"] == "2025-09-09"


@pytest.mark.asyncio
async def test_due_date_is_date_only_not_datetime(
    client: AsyncClient, test_project: Project
) -> None:
    """Due date is stored/returned as a date (no time component)."""
    resp = await client.post(
        "/tasks",
        json={
            "title": "Date only",
            "project_id": str(test_project.id),
            "due_date": "2025-12-31",
        },
    )
    assert resp.status_code == 201, resp.text
    due = resp.json()["due_date"]
    # date_only: must be YYYY-MM-DD, no 'T' time portion
    assert due == "2025-12-31"
    assert "T" not in due
    assert len(due) == 10


@pytest.mark.asyncio
async def test_due_date_rejects_datetime_format(
    client: AsyncClient, test_project: Project
) -> None:
    """Sending a full datetime should not be accepted as a date-only field."""
    resp = await client.post(
        "/tasks",
        json={
            "title": "Bad format",
            "project_id": str(test_project.id),
            "due_date": "not-a-date",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_preserves_due_date_when_not_supplied(
    client: AsyncClient, test_project: Project
) -> None:
    """Updating other fields without specifying due_date must not clear it."""
    create_resp = await client.post(
        "/tasks",
        json={
            "title": "Keep due date",
            "project_id": str(test_project.id),
            "due_date": "2025-10-05",
        },
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/tasks/{task_id}",
        json={"title": "Renamed"},
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["title"] == "Renamed"
    assert update_resp.json()["due_date"] == "2025-10-05"
