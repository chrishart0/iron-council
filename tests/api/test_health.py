from http import HTTPStatus

import pytest
from httpx import ASGITransport, AsyncClient
from server.main import app


@pytest.mark.asyncio
async def test_health_returns_stable_json_contract() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "status": "ok",
    }
