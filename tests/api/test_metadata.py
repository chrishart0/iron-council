from http import HTTPStatus

import pytest
from httpx import ASGITransport, AsyncClient

from server.main import app


@pytest.mark.asyncio
async def test_root_returns_service_metadata_contract() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "service": "iron-counsil-server",
        "status": "ok",
        "version": "0.1.0",
    }
