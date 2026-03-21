"""Integration tests for transfer endpoints."""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_list_transfers_empty(client):
    resp = await client.get("/api/v1/transfers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_create_transfer(client):
    with patch("app.services.transfer_service.TransferService.execute_transfer", new_callable=AsyncMock):
        resp = await client.post(
            "/api/v1/transfers",
            json={
                "source_patient_id": "patient-001",
                "destination_type": "api",
                "destination_name": "test-dest",
                "destination_config": {"url": "http://example.com/api/patients"},
            },
        )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "pending"
    assert data["destination_name"] == "test-dest"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_transfer_not_found(client):
    resp = await client.get("/api/v1/transfers/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_retry_non_failed_transfer_returns_409(client):
    # Create a transfer first
    with patch("app.services.transfer_service.TransferService.execute_transfer", new_callable=AsyncMock):
        create_resp = await client.post(
            "/api/v1/transfers",
            json={
                "source_patient_id": "patient-001",
                "destination_type": "api",
                "destination_name": "test-dest",
                "destination_config": {"url": "http://example.com/api/patients"},
            },
        )
    transfer_id = create_resp.json()["id"]
    # Transfer is still 'pending', not 'failed' – retry should 409
    with patch("app.services.transfer_service.TransferService.execute_transfer", new_callable=AsyncMock):
        retry_resp = await client.post(f"/api/v1/transfers/{transfer_id}/retry")
    assert retry_resp.status_code == 409


@pytest.mark.asyncio
async def test_list_transfers_filter_by_status(client):
    with patch("app.services.transfer_service.TransferService.execute_transfer", new_callable=AsyncMock):
        await client.post(
            "/api/v1/transfers",
            json={
                "source_patient_id": "patient-002",
                "destination_type": "fhir_write",
                "destination_name": "fhir-dest",
                "destination_config": {
                    "base_url": "http://fhir.example.com",
                    "token_url": "http://fhir.example.com/token",
                    "client_id": "x",
                    "client_secret": "y",
                },
            },
        )
    resp = await client.get("/api/v1/transfers?status=completed")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0  # none completed yet
