from __future__ import annotations

import pytest

from ecocode.core.schemas import SchemaValidationError, validate_named_schema


def test_profile_schema_accepts_minimal_payload() -> None:
    payload = {
        "schemaVersion": 1,
        "script": "demo.py",
        "collector": "placeholder",
        "runs": 1,
        "cpu_seconds": 0.1,
        "memory_mb": 32.0,
        "estimated_energy_wh": 0.012,
        "sustainability_score": 99,
    }
    validate_named_schema("profile_report", payload)


def test_profile_schema_rejects_unknown_key() -> None:
    payload = {
        "schemaVersion": 1,
        "script": "demo.py",
        "collector": "placeholder",
        "runs": 1,
        "cpu_seconds": 0.1,
        "memory_mb": 32.0,
        "estimated_energy_wh": 0.012,
        "sustainability_score": 99,
        "unexpected": True,
    }

    with pytest.raises(SchemaValidationError):
        validate_named_schema("profile_report", payload)


def test_repo_schema_rejects_bad_file_item_type() -> None:
    payload = {
        "schemaVersion": 1,
        "root": "/tmp/repo",
        "collector": "placeholder",
        "runs": 1,
        "total_files": 1,
        "total_cpu_seconds": 0.3,
        "total_memory_mb": 15.0,
        "total_energy_wh": 0.02,
        "average_sustainability_score": 97.0,
        "summary": {
            "runs": 1,
            "total_energy_wh_mean": 0.02,
            "total_energy_wh_median": 0.02,
            "total_energy_wh_stddev": 0.0,
            "total_energy_wh_cv_pct": 0.0,
        },
        "stability": {
            "max_energy_cv_pct": 35.0,
            "unstable": False,
        },
        "extensions": [".py"],
        "include_globs": [],
        "exclude_globs": [],
        "files": [
            {
                "script": "a.py",
                "cpu_seconds": "invalid",
                "memory_mb": 15.0,
                "estimated_energy_wh": 0.02,
                "sustainability_score": 97,
            }
        ],
    }

    with pytest.raises(SchemaValidationError):
        validate_named_schema("repo_report", payload)


def test_trend_schema_accepts_empty_summary_points() -> None:
    payload = {
        "schemaVersion": 1,
        "history_dir": "/tmp/.ecocode/history",
        "summary": {
            "count": 0,
            "first_energy_wh": None,
            "last_energy_wh": None,
            "min_energy_wh": None,
            "max_energy_wh": None,
            "delta_wh": None,
            "delta_pct": None,
        },
        "points": [],
    }

    validate_named_schema("trend_report", payload)


def test_benchmark_schema_accepts_valid_payload() -> None:
    payload = {
        "schemaVersion": 1,
        "fixtures_dir": "/tmp/fixtures",
        "collector": "placeholder",
        "noise_profile": "warm",
        "runs": 5,
        "max_energy_cv_pct": 35.0,
        "max_suite_cv_pct": 10.0,
        "max_unstable_fixtures": 0,
        "total_fixtures": 2,
        "unstable_fixtures": 0,
        "status": "passed",
        "summary": {
            "energy_wh_mean": 0.12,
            "energy_wh_median": 0.11,
            "energy_wh_stddev": 0.01,
            "energy_wh_cv_pct": 8.333333,
        },
        "fixtures": [
            {
                "script": "/tmp/fixtures/a.py",
                "runs": 5,
                "energy_wh_mean": 0.12,
                "energy_wh_median": 0.11,
                "energy_wh_stddev": 0.01,
                "energy_wh_cv_pct": 8.333333,
                "unstable": False,
            }
        ],
    }

    validate_named_schema("benchmark_report", payload)
