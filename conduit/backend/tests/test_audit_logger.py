"""Unit tests for the audit logger."""
import pytest

from app.audit.logger import AuditLogger, _patient_token


class TestPatientToken:
    def test_deterministic(self):
        assert _patient_token("patient-001") == _patient_token("patient-001")

    def test_different_ids_differ(self):
        assert _patient_token("patient-001") != _patient_token("patient-002")

    def test_token_is_64_chars(self):
        token = _patient_token("any-id")
        assert len(token) == 64


@pytest.mark.asyncio
async def test_log_fhir_fetch(db_session):
    logger = AuditLogger(db_session)
    entry = await logger.log_fhir_fetch(
        patient_id="patient-001",
        source_system="modmed",
        resource_types=["Patient", "Condition"],
        resource_count=2,
        success=True,
    )
    assert entry.event_type == "fhir_fetch"
    assert entry.outcome == "success"
    assert entry.resource_count == 2
    # Verify patient ID is NOT stored raw
    assert "patient-001" not in entry.patient_token


@pytest.mark.asyncio
async def test_log_error(db_session):
    logger = AuditLogger(db_session)
    entry = await logger.log_error(
        patient_id="patient-001",
        source_system="modmed",
        detail="Connection refused",
    )
    assert entry.event_type == "error"
    assert entry.outcome == "failure"
    assert entry.detail == "Connection refused"


@pytest.mark.asyncio
async def test_log_deliver(db_session):
    logger = AuditLogger(db_session)
    entry = await logger.log_deliver(
        patient_id="patient-001",
        source_system="modmed",
        destination_name="partner-ehr",
        resource_types=["Patient"],
        resource_count=1,
        success=True,
    )
    assert entry.destination_name == "partner-ehr"
    assert entry.outcome == "success"
