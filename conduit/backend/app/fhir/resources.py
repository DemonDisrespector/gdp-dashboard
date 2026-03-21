"""FHIR R4 resource type definitions and metadata."""
from dataclasses import dataclass, field
from typing import List, Optional

RESOURCE_TYPES: List[str] = [
    "Patient",
    "Coverage",
    "Condition",
    "Procedure",
    "ServiceRequest",
    "Practitioner",
    "DocumentReference",
    "AllergyIntolerance",
    "MedicationRequest",
]


@dataclass
class ResourceMeta:
    """Metadata describing how each resource type is searched."""

    resource_type: str
    patient_search_param: Optional[str]  # None = not patient-scoped (e.g. Practitioner)
    required_for_transfer: bool = True
    supported_includes: List[str] = field(default_factory=list)


RESOURCE_META: dict[str, ResourceMeta] = {
    "Patient": ResourceMeta(
        resource_type="Patient",
        patient_search_param=None,  # fetched by ID
        required_for_transfer=True,
    ),
    "Coverage": ResourceMeta(
        resource_type="Coverage",
        patient_search_param="patient",
        required_for_transfer=True,
        supported_includes=["Coverage:payor"],
    ),
    "Condition": ResourceMeta(
        resource_type="Condition",
        patient_search_param="patient",
        required_for_transfer=True,
        supported_includes=["Condition:asserter"],
    ),
    "Procedure": ResourceMeta(
        resource_type="Procedure",
        patient_search_param="patient",
        required_for_transfer=False,
        supported_includes=["Procedure:performer"],
    ),
    "ServiceRequest": ResourceMeta(
        resource_type="ServiceRequest",
        patient_search_param="patient",
        required_for_transfer=True,
        supported_includes=["ServiceRequest:requester", "ServiceRequest:performer"],
    ),
    "Practitioner": ResourceMeta(
        resource_type="Practitioner",
        patient_search_param=None,  # fetched by reference from other resources
        required_for_transfer=False,
    ),
    "DocumentReference": ResourceMeta(
        resource_type="DocumentReference",
        patient_search_param="patient",
        required_for_transfer=False,
        supported_includes=["DocumentReference:author"],
    ),
    "AllergyIntolerance": ResourceMeta(
        resource_type="AllergyIntolerance",
        patient_search_param="patient",
        required_for_transfer=True,
    ),
    "MedicationRequest": ResourceMeta(
        resource_type="MedicationRequest",
        patient_search_param="patient",
        required_for_transfer=True,
        supported_includes=["MedicationRequest:medication"],
    ),
}
