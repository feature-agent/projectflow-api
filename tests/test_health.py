"""Tests for the health check endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_returns_200(client: AsyncClient) -> None:
    """GET /health returns status code 200."""
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_check_response_body(client: AsyncClient) -> None:
    """GET /health returns body equal to {\"status\": \"ok\"}."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_check_status_field(client: AsyncClient) -> None:
    """GET /health response contains status field equal to 'ok'."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_check_content_type_json(client: AsyncClient) -> None:
    """GET /health returns a JSON content type."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
