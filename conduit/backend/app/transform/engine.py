"""
Data transformation engine.

Loads JSON mapping files from app/transform/mappings/ and applies them to raw
FHIR bundles to produce destination-specific payloads.

Mapping file format
-------------------
Each mapping file is named after the FHIR resource type (e.g. Patient.json)
and has the following shape::

    {
        "version": "1.0",
        "resource_type": "Patient",
        "fields": [
            {
                "source": "name[0].family",      // JSONPath-lite dot notation
                "dest": "lastName",
                "required": true,
                "transform": null                // null | "upper" | "lower" | "date_iso"
            },
            ...
        ],
        "static": {                              // Always-present destination fields
            "sourceSystem": "conduit"
        }
    }
"""
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MAPPINGS_DIR = Path(__file__).parent / "mappings"

# ── Built-in transforms ───────────────────────────────────────────────────────

_TRANSFORMS = {
    "upper": lambda v: v.upper() if isinstance(v, str) else v,
    "lower": lambda v: v.lower() if isinstance(v, str) else v,
    "date_iso": lambda v: v[:10] if isinstance(v, str) and len(v) >= 10 else v,
    "strip": lambda v: v.strip() if isinstance(v, str) else v,
    "int": lambda v: int(v) if v is not None else None,
    "str": lambda v: str(v) if v is not None else None,
}


def _apply_transform(value: Any, transform_name: Optional[str]) -> Any:
    if not transform_name:
        return value
    fn = _TRANSFORMS.get(transform_name)
    if fn is None:
        logger.warning("Unknown transform '%s'; skipping", transform_name)
        return value
    return fn(value)


# ── JSONPath-lite resolver ────────────────────────────────────────────────────

_INDEX_RE = re.compile(r"^(\w+)\[(\d+)\]$")


def _resolve_path(obj: Any, path: str) -> Any:
    """
    Resolve a simple dot-notation path with optional array indexing.
    Examples: "name[0].family"  "telecom[1].value"  "birthDate"
    Returns None if any segment is missing.
    """
    if not path:
        return obj
    for segment in path.split("."):
        if obj is None:
            return None
        m = _INDEX_RE.match(segment)
        if m:
            key, idx = m.group(1), int(m.group(2))
            obj = obj.get(key) if isinstance(obj, dict) else None
            if isinstance(obj, list):
                obj = obj[idx] if idx < len(obj) else None
            else:
                obj = None
        else:
            obj = obj.get(segment) if isinstance(obj, dict) else None
    return obj


def _set_path(obj: dict, path: str, value: Any):
    """Set a value in a nested dict using dot-notation path."""
    parts = path.split(".")
    for part in parts[:-1]:
        obj = obj.setdefault(part, {})
    obj[parts[-1]] = value


# ── Mapping loader (cached per destination) ───────────────────────────────────

_mapping_cache: Dict[str, dict] = {}


def load_mapping(resource_type: str, destination: Optional[str] = None) -> Optional[dict]:
    """
    Load a JSON mapping file.

    Search order:
    1. mappings/<destination>/<ResourceType>.json
    2. mappings/<ResourceType>.json   (generic fallback)
    """
    cache_key = f"{destination}/{resource_type}" if destination else resource_type
    if cache_key in _mapping_cache:
        return _mapping_cache[cache_key]

    candidates: List[Path] = []
    if destination:
        candidates.append(MAPPINGS_DIR / destination / f"{resource_type}.json")
    candidates.append(MAPPINGS_DIR / f"{resource_type}.json")

    for path in candidates:
        if path.exists():
            with path.open() as fh:
                mapping = json.load(fh)
            _mapping_cache[cache_key] = mapping
            logger.debug("Loaded mapping %s", path)
            return mapping

    logger.warning("No mapping found for %s (destination=%s)", resource_type, destination)
    return None


# ── Core transform logic ──────────────────────────────────────────────────────

class TransformEngine:
    """
    Apply JSON mappings to FHIR resources.

    Usage::

        engine = TransformEngine(destination="some_ehr")
        result = engine.transform_bundle(fhir_bundle)
    """

    def __init__(self, destination: Optional[str] = None):
        self.destination = destination

    def transform_resource(self, resource: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform a single FHIR resource dict."""
        resource_type = resource.get("resourceType", "")
        mapping = load_mapping(resource_type, self.destination)
        if mapping is None:
            logger.debug("Passing through unmapped resource type '%s'", resource_type)
            return resource  # pass-through

        output: Dict[str, Any] = dict(mapping.get("static", {}))

        for field_def in mapping.get("fields", []):
            source_path: str = field_def["source"]
            dest_path: str = field_def["dest"]
            required: bool = field_def.get("required", False)
            transform: Optional[str] = field_def.get("transform")
            default: Any = field_def.get("default")

            raw_value = _resolve_path(resource, source_path)
            if raw_value is None:
                if default is not None:
                    raw_value = default
                elif required:
                    logger.warning(
                        "Required field '%s' missing in %s id=%s",
                        source_path,
                        resource_type,
                        resource.get("id", "?"),
                    )
                    continue
                else:
                    continue

            transformed = _apply_transform(raw_value, transform)
            _set_path(output, dest_path, transformed)

        return output

    def transform_bundle(self, bundle: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform all entries in a FHIR Bundle."""
        results = []
        for entry in bundle.get("entry", []):
            resource = entry.get("resource", entry)
            transformed = self.transform_resource(resource)
            if transformed:
                results.append(transformed)
        return results
