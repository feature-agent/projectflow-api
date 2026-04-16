"""Tests for project management endpoints."""

import uuid

import pytest
from httpx import AsyncClient

from app.models.project import Project
from app.models.user import User


@pytest.mark.asyncio
async def test_create_project_success(
    client: AsyncClient, test_user: User
) -> None:
    """POST /projects creates a project and returns 201."""
    response = await client.post(
        "/projects",
        json={
            "name": "New Project",
            "description": "A new project",
            "owner_id": str(test_user.id),
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Project"
    assert data["description"] == "A new project"
    assert data["status"] == "active"
    assert data["owner_id"] == str(test_user.id)
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_project_invalid_owner_returns_404(
    client: AsyncClient,
) -> None:
    """POST /projects with non-existent owner returns 404."""
    response = await client.post(
        "/projects",
        json={
            "name": "Orphan Project",
            "owner_id": str(uuid.uuid4()),
        },
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_project_missing_fields_returns_422(
    client: AsyncClient,
) -> None:
    """POST /projects without required fields returns 422."""
    response = await client.post("/projects", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_projects_empty(client: AsyncClient) -> None:
    """GET /projects with no projects returns empty list."""
    response = await client.get("/projects")
    assert response.status_code == 200
    assert response.json()["projects"] == []


@pytest.mark.asyncio
async def test_list_projects_excludes_archived(
    client: AsyncClient, test_user: User, test_project: Project
) -> None:
    """GET /projects excludes archived projects."""
    # test_project is active, so it should appear
    response = await client.get("/projects")
    assert response.status_code == 200
    projects = response.json()["projects"]
    assert len(projects) == 1
    assert projects[0]["id"] == str(test_project.id)

    # Archive it via DELETE
    await client.delete(f"/projects/{test_project.id}")

    # Now list should be empty
    response = await client.get("/projects")
    assert response.status_code == 200
    assert response.json()["projects"] == []


@pytest.mark.asyncio
async def test_get_project_success(
    client: AsyncClient, test_project: Project
) -> None:
    """GET /projects/{id} returns the project."""
    response = await client.get(f"/projects/{test_project.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_project.id)
    assert data["name"] == test_project.name


@pytest.mark.asyncio
async def test_get_project_not_found_returns_404(
    client: AsyncClient,
) -> None:
    """GET /projects/{id} with unknown ID returns 404."""
    response = await client.get(f"/projects/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_project_success(
    client: AsyncClient, test_project: Project
) -> None:
    """PUT /projects/{id} updates and returns the project."""
    response = await client.put(
        f"/projects/{test_project.id}",
        json={"name": "Updated Project"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Project"


@pytest.mark.asyncio
async def test_update_project_not_found_returns_404(
    client: AsyncClient,
) -> None:
    """PUT /projects/{id} with unknown ID returns 404."""
    response = await client.put(
        f"/projects/{uuid.uuid4()}",
        json={"name": "Ghost"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_project_partial(
    client: AsyncClient, test_project: Project
) -> None:
    """PUT /projects/{id} with partial data only updates provided fields."""
    response = await client.put(
        f"/projects/{test_project.id}",
        json={"description": "Updated description"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated description"
    assert data["name"] == test_project.name  # unchanged


@pytest.mark.asyncio
async def test_delete_project_soft_deletes(
    client: AsyncClient, test_project: Project
) -> None:
    """DELETE /projects/{id} sets status to archived."""
    response = await client.delete(f"/projects/{test_project.id}")
    assert response.status_code == 200
    assert "archived" in response.json()["message"].lower()

    # Project still exists but is archived
    get_response = await client.get(f"/projects/{test_project.id}")
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_delete_project_not_found_returns_404(
    client: AsyncClient,
) -> None:
    """DELETE /projects/{id} with unknown ID returns 404."""
    response = await client.delete(f"/projects/{uuid.uuid4()}")
    assert response.status_code == 404
