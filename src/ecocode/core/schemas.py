from __future__ import annotations

from typing import Any


class SchemaValidationError(ValueError):
    """Raised when a payload does not match the expected JSON schema."""


PROFILE_REPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "script",
        "collector",
        "runs",
        "cpu_seconds",
        "memory_mb",
        "estimated_energy_wh",
        "sustainability_score",
    ],
    "properties": {
        "script": {"type": "string"},
        "collector": {"type": "string", "enum": ["placeholder", "runtime"]},
        "runs": {"type": "integer", "minimum": 1},
        "cpu_seconds": {"type": "number"},
        "memory_mb": {"type": "number"},
        "estimated_energy_wh": {"type": "number"},
        "sustainability_score": {"type": "integer"},
        "summary": {
            "type": "object",
            "required": [
                "cpu_seconds_mean",
                "cpu_seconds_median",
                "cpu_seconds_stddev",
                "memory_mb_mean",
                "memory_mb_median",
                "memory_mb_stddev",
                "estimated_energy_wh_mean",
                "estimated_energy_wh_median",
                "estimated_energy_wh_stddev",
                "estimated_energy_wh_cv_pct",
                "sustainability_score_mean",
                "sustainability_score_min",
                "sustainability_score_max",
            ],
            "properties": {
                "cpu_seconds_mean": {"type": "number"},
                "cpu_seconds_median": {"type": "number"},
                "cpu_seconds_stddev": {"type": "number"},
                "memory_mb_mean": {"type": "number"},
                "memory_mb_median": {"type": "number"},
                "memory_mb_stddev": {"type": "number"},
                "estimated_energy_wh_mean": {"type": "number"},
                "estimated_energy_wh_median": {"type": "number"},
                "estimated_energy_wh_stddev": {"type": "number"},
                "estimated_energy_wh_cv_pct": {"type": "number"},
                "sustainability_score_mean": {"type": "number"},
                "sustainability_score_min": {"type": "integer"},
                "sustainability_score_max": {"type": "integer"},
            },
            "additionalProperties": False,
        },
        "measurements": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "cpu_seconds",
                    "memory_mb",
                    "estimated_energy_wh",
                    "sustainability_score",
                ],
                "properties": {
                    "cpu_seconds": {"type": "number"},
                    "memory_mb": {"type": "number"},
                    "estimated_energy_wh": {"type": "number"},
                    "sustainability_score": {"type": "integer"},
                },
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}


BASELINE_FILE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["version", "collector", "runs", "baseline", "statistics"],
    "properties": {
        "version": {"type": "integer"},
        "collector": {"type": "string", "enum": ["placeholder", "runtime"]},
        "runs": {"type": "integer", "minimum": 1},
        "baseline": {
            "type": "object",
            "required": [
                "script",
                "cpu_seconds",
                "memory_mb",
                "estimated_energy_wh",
                "sustainability_score",
            ],
            "properties": {
                "script": {"type": "string"},
                "cpu_seconds": {"type": "number"},
                "memory_mb": {"type": "number"},
                "estimated_energy_wh": {"type": "number"},
                "sustainability_score": {"type": "integer"},
            },
            "additionalProperties": False,
        },
        "statistics": {
            "type": "object",
            "required": [
                "estimated_energy_wh_mean",
                "estimated_energy_wh_median",
                "estimated_energy_wh_stddev",
                "cpu_seconds_median",
                "memory_mb_median",
            ],
            "properties": {
                "estimated_energy_wh_mean": {"type": "number"},
                "estimated_energy_wh_median": {"type": "number"},
                "estimated_energy_wh_stddev": {"type": "number"},
                "cpu_seconds_median": {"type": "number"},
                "memory_mb_median": {"type": "number"},
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}


BASELINE_COMPARE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "baseline_path",
        "collector",
        "runs",
        "threshold_pct",
        "baseline_energy_wh",
        "current_energy_wh",
        "increase_pct",
        "regression",
        "status",
        "current",
        "current_statistics",
        "stability",
    ],
    "properties": {
        "baseline_path": {"type": "string"},
        "collector": {"type": "string", "enum": ["placeholder", "runtime"]},
        "runs": {"type": "integer", "minimum": 1},
        "threshold_pct": {"type": "number"},
        "baseline_energy_wh": {"type": "number"},
        "current_energy_wh": {"type": "number"},
        "increase_pct": {"type": "number"},
        "regression": {"type": "boolean"},
        "status": {"type": "string", "enum": ["passed", "failed"]},
        "current": BASELINE_FILE_SCHEMA["properties"]["baseline"],
        "current_statistics": {
            "type": "object",
            "required": [
                "estimated_energy_wh_mean",
                "estimated_energy_wh_median",
                "estimated_energy_wh_stddev",
                "estimated_energy_wh_cv_pct",
                "cpu_seconds_median",
                "memory_mb_median",
            ],
            "properties": {
                "estimated_energy_wh_mean": {"type": "number"},
                "estimated_energy_wh_median": {"type": "number"},
                "estimated_energy_wh_stddev": {"type": "number"},
                "estimated_energy_wh_cv_pct": {"type": "number"},
                "cpu_seconds_median": {"type": "number"},
                "memory_mb_median": {"type": "number"},
            },
            "additionalProperties": False,
        },
        "stability": {
            "type": "object",
            "required": ["max_energy_cv_pct", "unstable"],
            "properties": {
                "max_energy_cv_pct": {"type": "number"},
                "unstable": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}


REPO_REPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "root",
        "collector",
        "runs",
        "total_files",
        "total_cpu_seconds",
        "total_memory_mb",
        "total_energy_wh",
        "average_sustainability_score",
        "summary",
        "stability",
        "extensions",
        "include_globs",
        "exclude_globs",
        "files",
    ],
    "properties": {
        "root": {"type": "string"},
        "collector": {"type": "string", "enum": ["placeholder", "runtime"]},
        "runs": {"type": "integer", "minimum": 1},
        "total_files": {"type": "integer", "minimum": 0},
        "total_cpu_seconds": {"type": "number"},
        "total_memory_mb": {"type": "number"},
        "total_energy_wh": {"type": "number"},
        "average_sustainability_score": {"type": "number"},
        "summary": {
            "type": "object",
            "required": [
                "runs",
                "total_energy_wh_mean",
                "total_energy_wh_median",
                "total_energy_wh_stddev",
                "total_energy_wh_cv_pct",
            ],
            "properties": {
                "runs": {"type": "integer", "minimum": 1},
                "total_energy_wh_mean": {"type": "number"},
                "total_energy_wh_median": {"type": "number"},
                "total_energy_wh_stddev": {"type": "number"},
                "total_energy_wh_cv_pct": {"type": "number"},
            },
            "additionalProperties": False,
        },
        "stability": {
            "type": "object",
            "required": ["max_energy_cv_pct", "unstable"],
            "properties": {
                "max_energy_cv_pct": {"type": "number"},
                "unstable": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        "extensions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "include_globs": {
            "type": "array",
            "items": {"type": "string"},
        },
        "exclude_globs": {
            "type": "array",
            "items": {"type": "string"},
        },
        "files": {
            "type": "array",
            "items": BASELINE_FILE_SCHEMA["properties"]["baseline"],
        },
    },
    "additionalProperties": False,
}


TREND_REPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["history_dir", "summary", "points"],
    "properties": {
        "history_dir": {"type": "string"},
        "summary": {
            "type": "object",
            "required": [
                "count",
                "first_energy_wh",
                "last_energy_wh",
                "min_energy_wh",
                "max_energy_wh",
                "delta_wh",
                "delta_pct",
            ],
            "properties": {
                "count": {"type": "integer", "minimum": 0},
                "first_energy_wh": {"type": ["number", "null"]},
                "last_energy_wh": {"type": ["number", "null"]},
                "min_energy_wh": {"type": ["number", "null"]},
                "max_energy_wh": {"type": ["number", "null"]},
                "delta_wh": {"type": ["number", "null"]},
                "delta_pct": {"type": ["number", "null"]},
            },
            "additionalProperties": False,
        },
        "points": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["timestamp", "command", "energy_wh"],
                "properties": {
                    "timestamp": {"type": "string"},
                    "command": {"type": "string"},
                    "energy_wh": {"type": "number"},
                },
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}


SCHEMAS: dict[str, dict[str, Any]] = {
    "profile_report": PROFILE_REPORT_SCHEMA,
    "baseline_file": BASELINE_FILE_SCHEMA,
    "baseline_compare": BASELINE_COMPARE_SCHEMA,
    "repo_report": REPO_REPORT_SCHEMA,
    "trend_report": TREND_REPORT_SCHEMA,
}


def validate_named_schema(schema_name: str, payload: Any) -> None:
    schema = SCHEMAS.get(schema_name)
    if schema is None:
        raise SchemaValidationError(f"Unknown schema: {schema_name}")
    _validate(schema, payload, path="$")


def _validate(schema: dict[str, Any], value: Any, path: str) -> None:
    schema_type = schema.get("type")
    if schema_type is not None:
        _validate_type(schema_type, value, path)

    if "enum" in schema and value not in schema["enum"]:
        raise SchemaValidationError(f"{path}: value {value!r} is not in enum {schema['enum']!r}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        if minimum is not None and value < minimum:
            raise SchemaValidationError(f"{path}: value {value!r} is below minimum {minimum!r}")

    if isinstance(value, dict):
        _validate_object(schema, value, path)
        return

    if isinstance(value, list):
        _validate_array(schema, value, path)


def _validate_type(schema_type: str | list[str], value: Any, path: str) -> None:
    expected_types = schema_type if isinstance(schema_type, list) else [schema_type]
    if any(_is_type_match(expected, value) for expected in expected_types):
        return
    raise SchemaValidationError(
        f"{path}: expected type {expected_types!r}, got {type(value).__name__}"
    )


def _is_type_match(expected_type: str, value: Any) -> bool:
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "null":
        return value is None
    return False


def _validate_object(schema: dict[str, Any], value: dict[str, Any], path: str) -> None:
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    for key in required:
        if key not in value:
            raise SchemaValidationError(f"{path}: missing required key {key!r}")

    allow_additional = schema.get("additionalProperties", True)
    if not allow_additional:
        unknown = set(value.keys()) - set(properties.keys())
        if unknown:
            unknown_list = ", ".join(sorted(unknown))
            raise SchemaValidationError(f"{path}: unknown keys: {unknown_list}")

    for key, sub_schema in properties.items():
        if key in value:
            _validate(sub_schema, value[key], path=f"{path}.{key}")


def _validate_array(schema: dict[str, Any], value: list[Any], path: str) -> None:
    item_schema = schema.get("items")
    if item_schema is None:
        return
    for index, item in enumerate(value):
        _validate(item_schema, item, path=f"{path}[{index}]")