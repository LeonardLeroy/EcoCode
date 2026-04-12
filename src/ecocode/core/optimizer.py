from __future__ import annotations

import ast
import difflib
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class OptimizationSuggestion:
    rule_id: str
    title: str
    rationale: str
    impact: str
    confidence: float
    language: str


@dataclass(slots=True)
class OptimizationPatchResult:
    script: str
    candidate_path: str
    rule_id: str
    strategy_title: str
    applied: bool
    changes_count: int
    diff: str


def suggest_optimizations(script_path: Path, max_suggestions: int = 10) -> list[OptimizationSuggestion]:
    if not script_path.exists() or not script_path.is_file():
        raise FileNotFoundError(f"Script not found: {script_path}")
    if max_suggestions <= 0:
        raise ValueError("max_suggestions must be greater than 0")

    source = script_path.read_text(encoding="utf-8", errors="replace")
    suffix = script_path.suffix.lower()
    language = _detect_language(suffix)

    suggestions: list[OptimizationSuggestion] = []
    suggestions.extend(_generic_rules(source, language))

    if language == "python":
        suggestions.extend(_python_rules(source))
    elif language in {"javascript", "typescript"}:
        suggestions.extend(_js_rules(source, language))
    elif language in {"c", "cpp", "csharp", "rust"}:
        suggestions.extend(_native_rules(source, language))
    elif language in {"html", "css"}:
        suggestions.extend(_web_rules(source, language))
    elif language == "assembly":
        suggestions.extend(_asm_rules(source))

    deduped: list[OptimizationSuggestion] = []
    seen: set[str] = set()
    for item in suggestions:
        key = f"{item.rule_id}:{item.title}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= max_suggestions:
            break

    return deduped


def generate_optimization_patch(
    script_path: Path,
    output_path: Path,
    rule_id: str | None = None,
    overwrite: bool = False,
) -> OptimizationPatchResult:
    if not script_path.exists() or not script_path.is_file():
        raise FileNotFoundError(f"Script not found: {script_path}")
    if output_path.exists() and not overwrite:
        raise ValueError(f"Candidate file already exists: {output_path}")

    source = script_path.read_text(encoding="utf-8", errors="replace")
    suffix = script_path.suffix.lower()
    language = _detect_language(suffix)
    if language != "python":
        raise ValueError("optimize patch MVP currently supports only Python files")

    suggestions = suggest_optimizations(script_path=script_path, max_suggestions=50)
    selected = _select_patch_suggestion(suggestions, rule_id=rule_id)
    if selected is None:
        requested = rule_id or "(auto)"
        raise ValueError(f"No patchable optimization suggestion found for rule: {requested}")

    candidate_source, changes_count = _apply_python_patch_strategy(source, selected.rule_id)
    if changes_count == 0:
        raise ValueError(f"Rule {selected.rule_id} was detected but no safe patch could be applied")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(candidate_source, encoding="utf-8")

    diff = "\n".join(
        difflib.unified_diff(
            source.splitlines(),
            candidate_source.splitlines(),
            fromfile=str(script_path),
            tofile=str(output_path),
            lineterm="",
        )
    )

    return OptimizationPatchResult(
        script=str(script_path),
        candidate_path=str(output_path),
        rule_id=selected.rule_id,
        strategy_title=selected.title,
        applied=True,
        changes_count=changes_count,
        diff=diff,
    )


def _select_patch_suggestion(
    suggestions: list[OptimizationSuggestion],
    rule_id: str | None,
) -> OptimizationSuggestion | None:
    patchable_rule_ids = {"PY001", "PY002"}
    if rule_id is not None:
        for item in suggestions:
            if item.rule_id == rule_id and item.rule_id in patchable_rule_ids:
                return item
        return None

    for item in suggestions:
        if item.rule_id in patchable_rule_ids:
            return item
    return None


def _apply_python_patch_strategy(source: str, rule_id: str) -> tuple[str, int]:
    if rule_id == "PY001":
        return _apply_python_direct_iteration_patch(source)
    if rule_id == "PY002":
        return _apply_python_string_concat_patch(source)
    return source, 0


def _apply_python_direct_iteration_patch(source: str) -> tuple[str, int]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ValueError(f"Failed to parse Python source for patching: {exc}") from exc

    lines = source.splitlines()
    replacement_lines: dict[int, str] = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        if not isinstance(node.target, ast.Name):
            continue
        if not isinstance(node.iter, ast.Call):
            continue

        loop_var = node.target.id
        collection_name = _extract_range_len_collection_name(node.iter)
        if collection_name is None:
            continue

        if _name_used_in_body(loop_var, node.body):
            continue

        line_number = node.lineno
        if line_number < 1 or line_number > len(lines):
            continue

        original_line = lines[line_number - 1]
        replacement_line = _rewrite_for_header_line(
            original_line=original_line,
            loop_var=loop_var,
            collection_name=collection_name,
        )
        if replacement_line is None:
            continue

        replacement_lines[line_number - 1] = replacement_line

    if not replacement_lines:
        return source, 0

    updated_lines = list(lines)
    for index, value in replacement_lines.items():
        updated_lines[index] = value

    updated_source = "\n".join(updated_lines)
    if source.endswith("\n"):
        updated_source += "\n"

    return updated_source, len(replacement_lines)


def _apply_python_string_concat_patch(source: str) -> tuple[str, int]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ValueError(f"Failed to parse Python source for patching: {exc}") from exc

    lines = source.splitlines()
    replacement_lines: dict[int, str] = {}
    insert_before: dict[int, list[str]] = {}
    insert_after: dict[int, list[str]] = {}

    for body in _iter_statement_bodies(tree):
        for index, statement in enumerate(body):
            if not isinstance(statement, ast.For):
                continue

            transforms = _collect_loop_concat_transforms(source, statement, body, index)
            if not transforms:
                continue

            for variable_name, parts_name, aug_assign in transforms:
                if aug_assign.lineno < 1 or aug_assign.lineno > len(lines):
                    continue

                expr_source = ast.get_source_segment(source, aug_assign.value)
                if expr_source is None:
                    continue

                original_line = lines[aug_assign.lineno - 1]
                indent = _leading_whitespace(original_line)
                replacement_lines[aug_assign.lineno - 1] = f"{indent}{parts_name}.append({expr_source})"

                for_indent = _leading_whitespace(lines[statement.lineno - 1])
                before_line = f"{for_indent}{parts_name} = []"
                after_line = f"{for_indent}{variable_name} = ''.join({parts_name})"

                insert_before.setdefault(statement.lineno, [])
                if before_line not in insert_before[statement.lineno]:
                    insert_before[statement.lineno].append(before_line)

                end_line = statement.end_lineno or statement.lineno
                insert_after.setdefault(end_line, [])
                if after_line not in insert_after[end_line]:
                    insert_after[end_line].append(after_line)

    if not replacement_lines and not insert_before and not insert_after:
        return source, 0

    rebuilt: list[str] = []
    for line_number, original_line in enumerate(lines, start=1):
        for line in insert_before.get(line_number, []):
            rebuilt.append(line)

        replacement = replacement_lines.get(line_number - 1)
        rebuilt.append(replacement if replacement is not None else original_line)

        for line in insert_after.get(line_number, []):
            rebuilt.append(line)

    updated_source = "\n".join(rebuilt)
    if source.endswith("\n"):
        updated_source += "\n"

    changes_count = len(replacement_lines) + sum(len(v) for v in insert_before.values()) + sum(
        len(v) for v in insert_after.values()
    )
    return updated_source, changes_count


def _iter_statement_bodies(root: ast.AST) -> list[list[ast.stmt]]:
    bodies: list[list[ast.stmt]] = []

    def visit(node: ast.AST) -> None:
        for field_name in ("body", "orelse", "finalbody"):
            maybe_body = getattr(node, field_name, None)
            if isinstance(maybe_body, list) and maybe_body and all(
                isinstance(item, ast.stmt) for item in maybe_body
            ):
                typed_body = maybe_body
                bodies.append(typed_body)
                for item in typed_body:
                    visit(item)

    visit(root)
    return bodies


def _collect_loop_concat_transforms(
    source: str,
    loop_statement: ast.For,
    parent_body: list[ast.stmt],
    loop_index: int,
) -> list[tuple[str, str, ast.AugAssign]]:
    transforms: list[tuple[str, str, ast.AugAssign]] = []

    for loop_item in loop_statement.body:
        if not isinstance(loop_item, ast.AugAssign):
            continue
        if not isinstance(loop_item.op, ast.Add):
            continue
        if not isinstance(loop_item.target, ast.Name):
            continue
        if not isinstance(loop_item.value, ast.Constant) or not isinstance(loop_item.value.value, str):
            continue

        variable_name = loop_item.target.id
        if _find_latest_empty_string_initializer(parent_body, loop_index, variable_name) is None:
            continue
        if _name_loaded_in_statements(loop_statement.body, variable_name):
            continue

        parts_name = _choose_unique_parts_name(variable_name, source)
        transforms.append((variable_name, parts_name, loop_item))

    return transforms


def _find_latest_empty_string_initializer(
    statements: list[ast.stmt],
    stop_index: int,
    variable_name: str,
) -> ast.Assign | None:
    for statement in reversed(statements[:stop_index]):
        if not isinstance(statement, ast.Assign):
            continue
        if len(statement.targets) != 1:
            continue
        target = statement.targets[0]
        if not isinstance(target, ast.Name) or target.id != variable_name:
            continue
        if not isinstance(statement.value, ast.Constant) or statement.value.value != "":
            continue
        return statement
    return None


def _name_loaded_in_statements(statements: list[ast.stmt], variable_name: str) -> bool:
    for statement in statements:
        for node in ast.walk(statement):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id == variable_name:
                return True
    return False


def _choose_unique_parts_name(variable_name: str, source: str) -> str:
    base_name = f"_{variable_name}_parts"
    if re.search(rf"\b{re.escape(base_name)}\b", source) is None:
        return base_name

    counter = 2
    while True:
        candidate = f"{base_name}{counter}"
        if re.search(rf"\b{re.escape(candidate)}\b", source) is None:
            return candidate
        counter += 1


def _leading_whitespace(line: str) -> str:
    matched = re.match(r"^\s*", line)
    if matched is None:
        return ""
    return matched.group(0)


def _extract_range_len_collection_name(iter_node: ast.Call) -> str | None:
    if not isinstance(iter_node.func, ast.Name) or iter_node.func.id != "range":
        return None
    if len(iter_node.args) != 1:
        return None

    first_arg = iter_node.args[0]
    if not isinstance(first_arg, ast.Call):
        return None
    if not isinstance(first_arg.func, ast.Name) or first_arg.func.id != "len":
        return None
    if len(first_arg.args) != 1:
        return None

    collection = first_arg.args[0]
    if not isinstance(collection, ast.Name):
        return None
    return collection.id


def _name_used_in_body(name: str, body: list[ast.stmt]) -> bool:
    for statement in body:
        for node in ast.walk(statement):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id == name:
                return True
    return False


def _rewrite_for_header_line(
    original_line: str,
    loop_var: str,
    collection_name: str,
) -> str | None:
    pattern = re.compile(
        rf"^(?P<indent>\s*)for\s+{re.escape(loop_var)}\s+in\s+range\(\s*len\(\s*{re.escape(collection_name)}\s*\)\s*\)\s*:\s*$"
    )
    matched = pattern.match(original_line)
    if matched is None:
        return None
    return f"{matched.group('indent')}for _ in {collection_name}:"


def _detect_language(suffix: str) -> str:
    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".c": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".cs": "csharp",
        ".rs": "rust",
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".s": "assembly",
        ".asm": "assembly",
    }
    return mapping.get(suffix, "unknown")


def _generic_rules(source: str, language: str) -> list[OptimizationSuggestion]:
    suggestions: list[OptimizationSuggestion] = []
    lines = source.splitlines()

    if len(lines) > 800:
        suggestions.append(
            OptimizationSuggestion(
                rule_id="GEN001",
                title="Split very large file",
                rationale="Large files are harder to optimize and often hide duplicated work.",
                impact="medium",
                confidence=0.72,
                language=language,
            )
        )

    if source.count("TODO") >= 5:
        suggestions.append(
            OptimizationSuggestion(
                rule_id="GEN002",
                title="Review deferred hot-path TODOs",
                rationale="Many TODO markers may indicate pending performance-sensitive code paths.",
                impact="low",
                confidence=0.55,
                language=language,
            )
        )

    return suggestions


def _python_rules(source: str) -> list[OptimizationSuggestion]:
    suggestions: list[OptimizationSuggestion] = []

    if re.search(r"for\s+\w+\s+in\s+range\(len\(", source):
        suggestions.append(
            OptimizationSuggestion(
                rule_id="PY001",
                title="Prefer direct iteration over range(len())",
                rationale="Index-based loops can add overhead and reduce readability in Python.",
                impact="medium",
                confidence=0.84,
                language="python",
            )
        )

    if re.search(r"\+\=\s*['\"]", source):
        suggestions.append(
            OptimizationSuggestion(
                rule_id="PY002",
                title="Avoid repeated string concatenation",
                rationale="Repeated string concatenation may cause unnecessary allocations; prefer join/buffer patterns.",
                impact="medium",
                confidence=0.78,
                language="python",
            )
        )

    if source.count("for ") >= 2 and source.count("range(") >= 2:
        suggestions.append(
            OptimizationSuggestion(
                rule_id="PY003",
                title="Check nested loops for algorithmic complexity",
                rationale="Nested loops are common hotspots; evaluate data structures and loop bounds.",
                impact="high",
                confidence=0.7,
                language="python",
            )
        )

    return suggestions


def _js_rules(source: str, language: str) -> list[OptimizationSuggestion]:
    suggestions: list[OptimizationSuggestion] = []

    if "forEach(" in source and "await " in source:
        suggestions.append(
            OptimizationSuggestion(
                rule_id="JS001",
                title="Avoid async work inside forEach",
                rationale="async forEach patterns may be suboptimal; consider for...of with await control.",
                impact="medium",
                confidence=0.75,
                language=language,
            )
        )

    if re.search(r"new\s+Array\(\d+\)", source):
        suggestions.append(
            OptimizationSuggestion(
                rule_id="JS002",
                title="Validate large array preallocation",
                rationale="Large preallocated arrays can increase memory pressure.",
                impact="medium",
                confidence=0.66,
                language=language,
            )
        )

    return suggestions


def _native_rules(source: str, language: str) -> list[OptimizationSuggestion]:
    suggestions: list[OptimizationSuggestion] = []

    if source.count("for (") + source.count("for(") >= 2:
        suggestions.append(
            OptimizationSuggestion(
                rule_id="NAT001",
                title="Review nested/native loops",
                rationale="Nested loops in native code often dominate runtime and energy usage.",
                impact="high",
                confidence=0.73,
                language=language,
            )
        )

    if "malloc(" in source or "new " in source:
        suggestions.append(
            OptimizationSuggestion(
                rule_id="NAT002",
                title="Inspect allocation churn",
                rationale="Frequent allocations can increase CPU and memory overhead.",
                impact="medium",
                confidence=0.68,
                language=language,
            )
        )

    return suggestions


def _web_rules(source: str, language: str) -> list[OptimizationSuggestion]:
    suggestions: list[OptimizationSuggestion] = []

    if language == "html" and "style=" in source:
        suggestions.append(
            OptimizationSuggestion(
                rule_id="WEB001",
                title="Reduce inline style duplication",
                rationale="Heavy inline styles can duplicate declarations and increase page weight.",
                impact="low",
                confidence=0.71,
                language=language,
            )
        )

    if language == "css" and source.count("box-shadow") >= 3:
        suggestions.append(
            OptimizationSuggestion(
                rule_id="WEB002",
                title="Review expensive paint effects",
                rationale="Multiple heavy shadows may increase rendering cost on low-power devices.",
                impact="medium",
                confidence=0.64,
                language=language,
            )
        )

    return suggestions


def _asm_rules(source: str) -> list[OptimizationSuggestion]:
    suggestions: list[OptimizationSuggestion] = []

    if source.lower().count("mov") >= 20:
        suggestions.append(
            OptimizationSuggestion(
                rule_id="ASM001",
                title="Review register move density",
                rationale="High move density can indicate opportunities for instruction simplification.",
                impact="medium",
                confidence=0.6,
                language="assembly",
            )
        )

    return suggestions
