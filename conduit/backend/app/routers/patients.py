"""Patient lookup endpoints (proxy to FHIR source)."""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.fhir.client import FHIRClient, get_fhir_client

router = APIRouter(prefix="/patients")

SUPPORTED_RESOURCES = [
    "Patient", "Coverage", "Condition", "Procedure",
    "ServiceRequest", "Practitioner", "DocumentReference",
    "AllergyIntolerance", "MedicationRequest",
]


@router.get("/{patient_id}", summary="Fetch patient summary from FHIR source")
async def get_patient(
    patient_id: str,
    client: FHIRClient = Depends(get_fhir_client),
):
    return await client.get_resource("Patient", patient_id)


@router.get("/{patient_id}/bundle", summary="Fetch full patient bundle")
async def get_patient_bundle(
    patient_id: str,
    resource_types: Optional[str] = Query(
        None,
        description="Comma-separated resource types. Defaults to all supported types.",
    ),
    client: FHIRClient = Depends(get_fhir_client),
):
    types = (
        [t.strip() for t in resource_types.split(",")]
        if resource_types
        else SUPPORTED_RESOURCES
    )
    bundle = {}
    for rtype in types:
        if rtype == "Patient":
            bundle["Patient"] = await client.get_resource("Patient", patient_id)
        else:
            bundle[rtype] = await client.search_resource(
                rtype, {"patient": patient_id}
            )
    return bundle
