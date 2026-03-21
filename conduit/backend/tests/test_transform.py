"""Unit tests for the data transformation engine."""
import json
from pathlib import Path

import pytest

from app.transform.engine import TransformEngine, _resolve_path, load_mapping

FHIR_DIR = Path(__file__).parent.parent.parent.parent / "test_data" / "fhir"


def load_fixture(name: str) -> dict:
    return json.loads((FHIR_DIR / f"{name}.json").read_text())


class TestPathResolver:
    def test_simple_key(self):
        assert _resolve_path({"a": 1}, "a") == 1

    def test_nested_key(self):
        assert _resolve_path({"a": {"b": 2}}, "a.b") == 2

    def test_array_index(self):
        assert _resolve_path({"items": ["x", "y"]}, "items[1]") == "y"

    def test_missing_key_returns_none(self):
        assert _resolve_path({}, "missing") is None

    def test_out_of_bounds_returns_none(self):
        assert _resolve_path({"arr": []}, "arr[0]") is None

    def test_combined(self):
        obj = {"name": [{"family": "Smith"}]}
        assert _resolve_path(obj, "name[0].family") == "Smith"


class TestTransformEngine:
    def setup_method(self):
        self.engine = TransformEngine()

    def test_patient(self):
        patient = load_fixture("Patient")
        result = self.engine.transform_resource(patient)
        assert result is not None
        assert result["lastName"] == "JOHNSON"  # upper transform
        assert result["firstName"] == "Sarah"
        assert result["dateOfBirth"] == "1985-04-12"
        assert result["gender"] == "female"
        assert result["resourceType"] == "Patient"

    def test_condition(self):
        condition = load_fixture("Condition")
        result = self.engine.transform_resource(condition)
        assert result is not None
        assert result["diagnosis"] == "Type 2 diabetes mellitus without complications"
        assert result["icdCode"] == "E11.9"
        assert result["onsetDate"] == "2020-03-15"

    def test_allergy_intolerance(self):
        allergy = load_fixture("AllergyIntolerance")
        result = self.engine.transform_resource(allergy)
        assert result is not None
        assert "Penicillin" in result["allergen"]
        assert result["criticality"] == "high"
        assert result["reactionSeverity"] == "severe"

    def test_medication_request(self):
        med = load_fixture("MedicationRequest")
        result = self.engine.transform_resource(med)
        assert result is not None
        assert "Metformin" in result["medicationName"]
        assert result["refillsAllowed"] == 5
        assert result["status"] == "active"

    def test_bundle_transform(self):
        bundle = load_fixture("Bundle-patient-001")
        results = self.engine.transform_bundle(bundle)
        assert len(results) == 9
        resource_types = {r.get("resourceType") for r in results}
        assert "Patient" in resource_types
        assert "Condition" in resource_types

    def test_unknown_resource_type_passthrough(self):
        resource = {"resourceType": "UnknownType", "id": "x", "data": 42}
        result = self.engine.transform_resource(resource)
        assert result == resource
