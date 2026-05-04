"""Tests for task due date feature."""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from app.models.project import Project
from app.models.task import Task


@pytest.mark.asyncio
async def test_create_task_with_due_date(
    client: AsyncClient, test_project: Project
) -> None:
    """A task can be created with a due date (date-only)."""
    future = (date.today() + timedelta(days=7)).isoformat()
    response = await client.post(
        "/tasks",
        json={
            "title": "Task with due date",
            "project_id": str(test_project.id),
            "due_date": future,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert "due_date" in body
    assert body["due_date"] == future


@pytest.mark.asyncio
async def test_create_task_without_due_date_is_optional(
    client: AsyncClient, test_project: Project
) -> None:
    """Due date is optional on creation; field should be present and null."""
    response = await client.post(
        "/tasks",
        json={
            "title": "Task without due date",
            "project_id": str(test_project.id),
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert "due_date" in body
    assert body["due_date"] is None


@pytest.mark.asyncio
async def test_due_date_is_date_only_not_datetime(
    client: AsyncClient, test_project: Project
) -> None:
    """Due date should be a date (YYYY-MM-DD), not a datetime."""
    future = (date.today() + timedelta(days=3)).isoformat()
    response = await client.post(
        "/tasks",
        json={
            "title": "Date only task",
            "project_id": str(test_project.id),
            "due_date": future,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    # Must equal the simple date string with no time portion.
    assert body["due_date"] == future
    assert "T" not in body["due_date"]


@pytest.mark.asyncio
async def test_get_task_returns_due_date(
    client: AsyncClient, test_project: Project
) -> None:
    """Due dates can be viewed via GET."""
    future = (date.today() + timedelta(days=10)).isoformat()
    create_resp = await client.post(
        "/tasks",
        json={
            "title": "Viewable task",
            "project_id": str(test_project.id),
            "due_date": future,
        },
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    get_resp = await client.get(f"/tasks/{task_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["due_date"] == future


@pytest.mark.asyncio
async def test_list_tasks_includes_due_date(
    client: AsyncClient, test_project: Project
) -> None:
    """Due dates appear in list responses."""
    future = (date.today() + timedelta(days=5)).isoformat()
    await client.post(
        "/tasks",
        json={
            "title": "Listed task",
            "project_id": str(test_project.id),
            "due_date": future,
        },
    )
    resp = await client.get("/tasks")
    assert resp.status_code == 200
    tasks = resp.json()["tasks"]
    assert len(tasks) >= 1
    assert any(t.get("due_date") == future for t in tasks)


@pytest.mark.asyncio
async def test_update_task_set_due_date(
    client: AsyncClient, test_task: Task
) -> None:
    """Due date can be set via update on a task that had none."""
    future = (date.today() + timedelta(days=14)).isoformat()
    resp = await client.put(
        f"/tasks/{test_task.id}",
        json={"due_date": future},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["due_date"] == future


@pytest.mark.asyncio
async def test_update_task_modify_due_date(
    client: AsyncClient, test_project: Project
) -> None:
    """Existing due date can be edited."""
    first = (date.today() + timedelta(days=2)).isoformat()
    second = (date.today() + timedelta(days=20)).isoformat()

    create_resp = await client.post(
        "/tasks",
        json={
            "title": "Editable due",
            "project_id": str(test_project.id),
            "due_date": first,
        },
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/tasks/{task_id}",
        json={"due_date": second},
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["due_date"] == second

    get_resp = await client.get(f"/tasks/{task_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["due_date"] == second


@pytest.mark.asyncio
async def test_update_task_clear_due_date(
    client: AsyncClient, test_project: Project
) -> None:
    """Due date can be removed (set back to null) since it's optional."""
    future = (date.today() + timedelta(days=4)).isoformat()
    create_resp = await client.post(
        "/tasks",
        json={
            "title": "Clearable due",
            "project_id": str(test_project.id),
            "due_date": future,
        },
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]
    assert create_resp.json()["due_date"] == future

    clear_resp = await client.put(
        f"/tasks/{task_id}",
        json={"due_date": None},
    )
    assert clear_resp.status_code == 200, clear_resp.text
    assert clear_resp.json()["due_date"] is None

    get_resp = await client.get(f"/tasks/{task_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["due_date"] is None


@pytest.mark.asyncio
async def test_create_task_with_past_due_date_is_accepted_with_warning(
    client: AsyncClient, test_project: Project
) -> None:
    """Past due dates are allowed but should produce a warning indicator.

    Per clarification: warn_past — the request must NOT be rejected, but the
    response should include some warning surfaced to the client.
    """
    past = (date.today() - timedelta(days=3)).isoformat()
    response = await client.post(
        "/tasks",
        json={
            "title": "Past due task",
            "project_id": str(test_project.id),
            "due_date": past,
        },
    )
    # Must succeed — past dates are warned, not rejected.
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["due_date"] == past

    # Some indication of a warning should be present, either in the body
    # or in response headers.
    body_text = response.text.lower()
    headers_text = " ".join(
        f"{k}:{v}" for k, v in response.headers.items()
    ).lower()
    assert (
        "warning" in body_text
        or "warn" in body_text
        or "warning" in headers_text
    ), (
        "Expected a warning indicator when setting a past due date "
        f"(body={response.text!r}, headers={dict(response.headers)!r})"
    )


@pytest.mark.asyncio
async def test_update_task_to_past_due_date_is_accepted_with_warning(
    client: AsyncClient, test_task: Task
) -> None:
    """Updating to a past due date is accepted but warned."""
    past = (date.today() - timedelta(days=1)).isoformat()
    response = await client.put(
        f"/tasks/{test_task.id}",
        json={"due_date": past},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["due_date"] == past

    body_text = response.text.lower()
    headers_text = " ".join(
        f"{k}:{v}" for k, v in response.headers.items()
    ).lower()
    assert (
        "warning" in body_text
        or "warn" in body_text
        or "warning" in headers_text
    ), (
        "Expected a warning indicator when updating to a past due date "
        f"(body={response.text!r}, headers={dict(response.headers)!r})"
    )


@pytest.mark.asyncio
async def test_invalid_due_date_format_rejected(
    client: AsyncClient, test_project: Project
) -> None:
    """Non-date strings should be rejected by validation."""
    response = await client.post(
        "/tasks",
        json={
            "title": "Bad date",
            "project_id": str(test_project.id),
            "due_date": "not-a-date",
        },
    )
    assert response.status_code == 422
