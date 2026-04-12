from __future__ import annotations

import json
from pathlib import Path

from ecocode.cli import main


def test_profile_command_success(tmp_path: Path, capsys) -> None:
    script = tmp_path / "demo.py"
    script.write_text("print('hello')\n", encoding="utf-8")

    exit_code = main(["profile", str(script)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "EcoCode profile report" in captured.out
    assert "Sustainability score" in captured.out


def test_profile_command_missing_script(capsys) -> None:
    exit_code = main(["profile", "missing-script.py"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Script not found" in captured.out


def test_profile_command_json_with_runs(tmp_path: Path, capsys) -> None:
    script = tmp_path / "demo.py"
    script.write_text("print('hello')\n", encoding="utf-8")

    exit_code = main(["profile", str(script), "--json", "--runs", "3"])
    output = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(output.out)
    assert payload["runs"] == 3
    assert "summary" in payload
    assert len(payload["measurements"]) == 3


def test_baseline_create_and_compare_pass(tmp_path: Path, capsys) -> None:
    script = tmp_path / "demo.py"
    script.write_text("print('hello')\n", encoding="utf-8")
    baseline_file = tmp_path / ".ecocode" / "baseline.json"

    create_exit = main(
        ["baseline", "create", str(script), "-o", str(baseline_file)]
    )
    create_output = capsys.readouterr()

    assert create_exit == 0
    assert baseline_file.exists()
    assert "Baseline created" in create_output.out

    compare_exit = main(
        [
            "baseline",
            "compare",
            str(script),
            "--baseline",
            str(baseline_file),
        ]
    )
    compare_output = capsys.readouterr()

    assert compare_exit == 0
    assert "Status:" in compare_output.out
    assert "PASSED" in compare_output.out


def test_baseline_compare_regression_exit_code(tmp_path: Path, capsys) -> None:
    script = tmp_path / "demo.py"
    script.write_text("print('hello')\n", encoding="utf-8")
    baseline_file = tmp_path / "baseline.json"
    baseline_file.write_text(
        json.dumps(
            {
                "version": 1,
                "baseline": {
                    "estimated_energy_wh": 0.0001,
                },
            }
        ),
        encoding="utf-8",
    )

    compare_exit = main(
        [
            "baseline",
            "compare",
            str(script),
            "--baseline",
            str(baseline_file),
            "--energy-threshold-pct",
            "5",
        ]
    )
    compare_output = capsys.readouterr()

    assert compare_exit == 2
    assert "FAILED" in compare_output.out


def test_baseline_create_and_compare_with_runs(tmp_path: Path, capsys) -> None:
    script = tmp_path / "demo.py"
    script.write_text("print('hello')\n", encoding="utf-8")
    baseline_file = tmp_path / "baseline-runs.json"

    create_exit = main(
        [
            "baseline",
            "create",
            str(script),
            "-o",
            str(baseline_file),
            "--runs",
            "3",
        ]
    )
    _ = capsys.readouterr()

    assert create_exit == 0

    compare_exit = main(
        [
            "baseline",
            "compare",
            str(script),
            "--baseline",
            str(baseline_file),
            "--runs",
            "3",
            "--json",
        ]
    )
    output = capsys.readouterr()

    assert compare_exit == 0
    payload = json.loads(output.out)
    assert payload["runs"] == 3
    assert "current_statistics" in payload


def test_benchmark_command_json_success(tmp_path: Path, capsys) -> None:
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    (fixtures_dir / "one.py").write_text("print('one')\n", encoding="utf-8")
    (fixtures_dir / "two.py").write_text("print('two')\n", encoding="utf-8")

    exit_code = main(
        [
            "benchmark",
            "--fixtures-dir",
            str(fixtures_dir),
            "--runs",
            "3",
            "--json",
        ]
    )
    output = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(output.out)
    assert payload["total_fixtures"] == 2
    assert payload["runs"] == 3


def test_benchmark_command_missing_fixtures_dir(capsys) -> None:
    exit_code = main(["benchmark", "--fixtures-dir", "missing-dir", "--json"])
    output = capsys.readouterr()

    assert exit_code == 1
    assert "fixtures directory not found" in output.out.lower()


def test_benchmark_command_noise_profile_defaults(tmp_path: Path, capsys) -> None:
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    (fixtures_dir / "one.py").write_text("print('one')\n", encoding="utf-8")

    exit_code = main(
        [
            "benchmark",
            "--fixtures-dir",
            str(fixtures_dir),
            "--noise-profile",
            "cpu-bound",
            "--json",
        ]
    )
    output = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(output.out)
    assert payload["noise_profile"] == "cpu-bound"
    assert payload["runs"] == 9


def test_benchmark_command_fail_on_acceptance(tmp_path: Path, capsys) -> None:
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    (fixtures_dir / "one.py").write_text("print('one')\n", encoding="utf-8")
    (fixtures_dir / "two.py").write_text("print('two')\n", encoding="utf-8")

    exit_code = main(
        [
            "benchmark",
            "--fixtures-dir",
            str(fixtures_dir),
            "--runs",
            "3",
            "--max-suite-cv-pct",
            "0",
            "--fail-on-acceptance",
            "--json",
        ]
    )
    output = capsys.readouterr()

    payload = json.loads(output.out)
    assert payload["status"] == "failed"
    assert exit_code == 4


def test_optimize_suggest_json_success(tmp_path: Path, capsys) -> None:
    script = tmp_path / "demo.py"
    script.write_text(
        "for i in range(len([1,2,3])):\n    pass\n",
        encoding="utf-8",
    )

    exit_code = main(["optimize", "suggest", str(script), "--json"])
    output = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(output.out)
    assert payload["command"] == "optimize suggest"
    assert payload["suggestion_count"] >= 1


def test_optimize_suggest_missing_file(capsys) -> None:
    exit_code = main(["optimize", "suggest", "missing.py", "--json"])
    output = capsys.readouterr()

    assert exit_code == 1
    assert "script not found" in output.out.lower()


def test_optimize_evaluate_json_success(tmp_path: Path, capsys) -> None:
    baseline_script = tmp_path / "base.py"
    baseline_script.write_text("print('base')\n", encoding="utf-8")
    baseline_file = tmp_path / "baseline.json"

    create_exit = main(["baseline", "create", str(baseline_script), "-o", str(baseline_file)])
    assert create_exit == 0
    _ = capsys.readouterr()

    candidate = tmp_path / "candidate.py"
    candidate.write_text("print('candidate')\n", encoding="utf-8")

    exit_code = main(
        [
            "optimize",
            "evaluate",
            "--baseline",
            str(baseline_file),
            "--candidate",
            str(candidate),
            "--json",
        ]
    )
    output = capsys.readouterr()

    assert exit_code in {0, 2}
    payload = json.loads(output.out)
    assert payload["command"] == "optimize evaluate"


def test_optimize_evaluate_regression_exit_code(tmp_path: Path, capsys) -> None:
    candidate = tmp_path / "candidate.py"
    candidate.write_text("print('candidate')\n", encoding="utf-8")

    baseline_file = tmp_path / "baseline.json"
    baseline_file.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "version": 1,
                "baseline": {"estimated_energy_wh": 0.0001},
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "optimize",
            "evaluate",
            "--baseline",
            str(baseline_file),
            "--candidate",
            str(candidate),
            "--energy-threshold-pct",
            "1",
            "--json",
        ]
    )
    output = capsys.readouterr()

    assert exit_code == 2
    payload = json.loads(output.out)
    assert payload["regression"] is True


def test_optimize_patch_json_success(tmp_path: Path, capsys) -> None:
    script = tmp_path / "demo.py"
    script.write_text(
        "items = [1, 2, 3]\nfor i in range(len(items)):\n    print('ok')\n",
        encoding="utf-8",
    )

    exit_code = main(["optimize", "patch", str(script), "--json"])
    output = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(output.out)
    assert payload["command"] == "optimize patch"
    candidate_path = Path(payload["candidate_path"])
    assert candidate_path.exists()
    candidate_source = candidate_path.read_text(encoding="utf-8")
    assert "for _ in items:" in candidate_source


def test_optimize_patch_requires_patchable_rule(tmp_path: Path, capsys) -> None:
    script = tmp_path / "demo.py"
    script.write_text("print('hello')\n", encoding="utf-8")

    exit_code = main(["optimize", "patch", str(script), "--json"])
    output = capsys.readouterr()

    assert exit_code == 1
    assert "No patchable optimization suggestion" in output.out


def test_optimize_patch_py002_rule_success(tmp_path: Path, capsys) -> None:
    script = tmp_path / "demo.py"
    script.write_text(
        "result = ''\nfor item in [1, 2, 3]:\n    result += 'x'\nprint(result)\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "optimize",
            "patch",
            str(script),
            "--rule-id",
            "PY002",
            "--json",
        ]
    )
    output = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(output.out)
    assert payload["rule_id"] == "PY002"
    candidate_source = Path(payload["candidate_path"]).read_text(encoding="utf-8")
    assert "_result_parts = []" in candidate_source
    assert ".append('x')" in candidate_source
    assert "result = ''.join(_result_parts)" in candidate_source


def test_optimize_patch_use_llm_requires_llm_enabled(tmp_path: Path, monkeypatch, capsys) -> None:
    script = tmp_path / "demo.py"
    script.write_text("print('ok')\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    exit_code = main(["optimize", "patch", str(script), "--use-llm", "--json"])
    output = capsys.readouterr()

    assert exit_code == 1
    assert "optimize patch --use-llm requires optimize.llm.enabled = true" in output.out


def test_optimize_patch_use_llm_json_success(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "ecocode.toml").write_text(
        """
[optimize]
max_patch_changes = 50

[optimize.llm]
enabled = true
provider = "ollama"
model = "qwen2.5-coder:7b"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    script = tmp_path / "demo.py"
    script.write_text("print('hello')\n", encoding="utf-8")

    monkeypatch.setattr(
        "ecocode.commands.optimize.fetch_local_llm_candidate_patch",
        lambda **kwargs: ("print('hello world')\n", "LLM rewrite"),
    )
    monkeypatch.chdir(tmp_path)

    exit_code = main(["optimize", "patch", str(script), "--use-llm", "--json"])
    output = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(output.out)
    assert payload["command"] == "optimize patch"
    assert payload["rule_id"] == "LLM001"
    assert payload["strategy_title"] == "LLM rewrite"
    candidate_source = Path(payload["candidate_path"]).read_text(encoding="utf-8")
    assert "hello world" in candidate_source
