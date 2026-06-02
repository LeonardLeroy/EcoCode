from __future__ import annotations

from pathlib import Path

from ecocode.core.optimizer import suggest_optimizations


def test_python_suggestions_report_line_numbers(tmp_path: Path) -> None:
    script = tmp_path / "demo.py"
    script.write_text(
        "x = 1\n"
        "y = 2\n"
        "for i in range(len([1, 2, 3])):\n"
        "    pass\n",
        encoding="utf-8",
    )

    suggestions = suggest_optimizations(script_path=script)
    by_rule = {item.rule_id: item for item in suggestions}

    assert "PY001" in by_rule
    assert by_rule["PY001"].line == 3


def test_large_file_rule_has_no_line(tmp_path: Path) -> None:
    script = tmp_path / "big.py"
    script.write_text("\n".join(f"a_{i} = {i}" for i in range(900)) + "\n", encoding="utf-8")

    suggestions = suggest_optimizations(script_path=script)
    by_rule = {item.rule_id: item for item in suggestions}

    assert "GEN001" in by_rule
    assert by_rule["GEN001"].line is None
