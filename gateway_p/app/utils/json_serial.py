"""Convert dicts/values to JSON-serializable form for DB (JSONB) and API responses."""
from decimal import Decimal
from datetime import datetime, date
from typing import Any, Dict
from uuid import UUID


def to_json_serializable(value: Any) -> Any:
    """Recursively convert values so they are safe for JSON (and PostgreSQL JSONB)."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: to_json_serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json_serializable(v) for v in value]
    return value


def sanitize_metadata(metadata: Dict[str, Any] | None) -> Dict[str, Any]:
    """Return a copy of metadata safe for JSON/JSONB serialization."""
    if not metadata:
        return {}
    return to_json_serializable(dict(metadata))
