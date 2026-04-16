"""Tests for task due_date field."""

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from app.models.project import Project
from app.models.task import Task
from app.models.user import User


@pytest.mark.asyncio
async def test_create_task_with_due_date_success(
    client: AsyncClient, test_project: Project
) -> None:
    """POST /tasks creates a task with a due_date and returns it in response."""
    due = (date.today() + timedelta(days=7)).isoformat()
    response = await client.post(
        "/tasks",
        json={
            "title": "Task with Due Date",
            "project_id": str(test_project.id),
            "due_date": due,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["due_date"] == due
    assert data["title"] == "Task with Due Date"


@pytest.mark.asyncio
async def test_create_task_without_due_date_defaults_to_null(
    client: AsyncClient, test_project: Project
) -> None:
    """POST /tasks without due_date returns null due_date."""
    response = await client.post(
        "/tasks",
        json={
            "title": "No Due Date",
            "project_id": str(test_project.id),
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["due_date"] is None


@pytest.mark.asyncio
async def test_create_task_with_explicit_null_due_date(
    client: AsyncClient, test_project: Project
) -> None:
    """POST /tasks with due_date=null returns null due_date."""
    response = await client.post(
        "/tasks",
        json={
            "title": "Explicit Null",
            "project_id": str(test_project.id),
            "due_date": None,
        },
    )
    assert response.status_code == 201
    assert response.json()["due_date"] is None


@pytest.mark.asyncio
async def test_create_task_with_past_due_date_success(
    client: AsyncClient, test_project: Project
) -> None:
    """POST /tasks accepts past due_date values."""
    past = (date.today() - timedelta(days=30)).isoformat()
    response = await client.post(
        "/tasks",
        json={
            "title": "Overdue Task",
            "project_id": str(test_project.id),
            "due_date": past,
        },
    )
    assert response.status_code == 201
    assert response.json()["due_date"] == past


@pytest.mark.asyncio
async def test_create_task_with_invalid_due_date_returns_422(
    client: AsyncClient, test_project: Project
) -> None:
    """POST /tasks with malformed due_date returns 422."""
    response = await client.post(
        "/tasks",
        json={
            "title": "Bad Date",
            "project_id": str(test_project.id),
            "due_date": "not-a-date",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_task_returns_due_date(
    client: AsyncClient, test_project: Project
) -> None:
    """GET /tasks/{id} includes due_date in response."""
    due = (date.today() + timedelta(days=3)).isoformat()
    create_response = await client.post(
        "/tasks",
        json={
            "title": "Fetch Me",
            "project_id": str(test_project.id),
            "due_date": due,
        },
    )
    task_id = create_response.json()["id"]
    response = await client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["due_date"] == due


@pytest.mark.asyncio
async def test_get_task_without_due_date_returns_null(
    client: AsyncClient, test_task: Task
) -> None:
    """GET /tasks/{id} returns null due_date when not set."""
    response = await client.get(f"/tasks/{test_task.id}")
    assert response.status_code == 200
    assert response.json()["due_date"] is None


@pytest.mark.asyncio
async def test_list_tasks_includes_due_date(
    client: AsyncClient, test_project: Project
) -> None:
    """GET /tasks returns due_date for each task."""
    due = (date.today() + timedelta(days=5)).isoformat()
    await client.post(
        "/tasks",
        json={
            "title": "Listed Task",
            "project_id": str(test_project.id),
            "due_date": due,
        },
    )
    response = await client.get("/tasks")
    assert response.status_code == 200
    tasks = response.json()["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["due_date"] == due


@pytest.mark.asyncio
async def test_update_task_set_due_date(
    client: AsyncClient, test_task: Task
) -> None:
    """PUT /tasks/{id} can set a due_date on an existing task."""
    due = (date.today() + timedelta(days=10)).isoformat()
    response = await client.put(
        f"/tasks/{test_task.id}",
        json={"due_date": due},
    )
    assert response.status_code == 200
    assert response.json()["due_date"] == due


@pytest.mark.asyncio
async def test_update_task_change_due_date(
    client: AsyncClient, test_project: Project
) -> None:
    """PUT /tasks/{id} can change an existing due_date."""
    initial = (date.today() + timedelta(days=1)).isoformat()
    updated = (date.today() + timedelta(days=14)).isoformat()
    create_response = await client.post(
        "/tasks",
        json={
            "title": "Reschedule",
            "project_id": str(test_project.id),
            "due_date": initial,
        },
    )
    task_id = create_response.json()["id"]
    response = await client.put(
        f"/tasks/{task_id}",
        json={"due_date": updated},
    )
    assert response.status_code == 200
    assert response.json()["due_date"] == updated


@pytest.mark.asyncio
async def test_update_task_clear_due_date(
    client: AsyncClient, test_project: Project
) -> None:
    """PUT /tasks/{id} can clear a due_date by setting it to null."""
    due = (date.today() + timedelta(days=2)).isoformat()
    create_response = await client.post(
        "/tasks",
        json={
            "title": "Clear Date",
            "project_id": str(test_project.id),
            "due_date": due,
        },
    )
    task_id = create_response.json()["id"]
    response = await client.put(
        f"/tasks/{task_id}",
        json={"due_date": None},
    )
    assert response.status_code == 200
    assert response.json()["due_date"] is None


@pytest.mark.asyncio
async def test_update_task_due_date_preserves_other_fields(
    client: AsyncClient, test_task: Task
) -> None:
    """PUT /tasks/{id} updating only due_date leaves other fields unchanged."""
    due = (date.today() + timedelta(days=4)).isoformat()
    response = await client.put(
        f"/tasks/{test_task.id}",
        json={"due_date": due},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["due_date"] == due
    assert data["title"] == test_task.title
    assert data["status"] == test_task.status
    assert data["priority"] == test_task.priority


@pytest.mark.asyncio
async def test_update_task_invalid_due_date_returns_422(
    client: AsyncClient, test_task: Task
) -> None:
    """PUT /tasks/{id} with malformed due_date returns 422."""
    response = await client.put(
        f"/tasks/{test_task.id}",
        json={"due_date": "2024/13/45"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_task_without_due_date_key_preserves_it(
    client: AsyncClient, test_project: Project
) -> None:
    """PUT /tasks/{id} without due_date key does not modify existing due_date."""
    due = (date.today() + timedelta(days=6)).isoformat()
    create_response = await client.post(
        "/tasks",
        json={
            "title": "Keep Date",
            "project_id": str(test_project.id),
            "due_date": due,
        },
    )
    task_id = create_response.json()["id"]
    response = await client.put(
        f"/tasks/{task_id}",
        json={"title": "Renamed"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Renamed"
    assert data["due_date"] == due


@pytest.mark.asyncio
async def test_project_tasks_include_due_date(
    client: AsyncClient, test_project: Project
) -> None:
    """GET /projects/{id}/tasks includes due_date field."""
    due = (date.today() + timedelta(days=8)).isoformat()
    await client.post(
        "/tasks",
        json={
            "title": "Project Task",
            "project_id": str(test_project.id),
            "due_date": due,
        },
    )
    response = await client.get(f"/projects/{test_project.id}/tasks")
    assert response.status_code == 200
    tasks = response.json()["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["due_date"] == due


@pytest.mark.asyncio
async def test_user_tasks_include_due_date(
    client: AsyncClient, test_project: Project, test_user: User
) -> None:
    """GET /users/{id}/tasks includes due_date field."""
    due = (date.today() + timedelta(days=9)).isoformat()
    await client.post(
        "/tasks",
        json={
            "title": "User Task",
            "project_id": str(test_project.id),
            "assignee_id": str(test_user.id),
            "due_date": due,
        },
    )
    response = await client.get(f"/users/{test_user.id}/tasks")
    assert response.status_code == 200
    tasks = response.json()["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["due_date"] == due
