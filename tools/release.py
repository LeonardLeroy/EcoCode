#!/usr/bin/env python3
"""Build a publishable EcoCode VS Code extension package.

Bumps the version, runs the checks that would otherwise only fail after
publishing, compiles the TypeScript and produces the .vsix to upload to the
Marketplace.

Deliberately does not touch git: no add, no commit, no tag, no push. The
suggested commands are printed at the end so history stays under your control.

Usage:
    python tools/release.py patch
    python tools/release.py minor --cli patch
    python tools/release.py 0.3.0 --dry-run
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXTENSION_DIR = REPO_ROOT / "vscode-extension"
EXTENSION_MANIFEST = EXTENSION_DIR / "package.json"
CLI_MANIFEST = REPO_ROOT / "pyproject.toml"

# Invoke the real JS entry points rather than node_modules/.bin shims: an
# install made from WSL leaves POSIX symlinks there, which Windows npm cannot run.
TSC_ENTRY = EXTENSION_DIR / "node_modules" / "typescript" / "bin" / "tsc"
VSCE_ENTRY = EXTENSION_DIR / "node_modules" / "@vscode" / "vsce" / "vsce"

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
BUMPS = ("patch", "minor", "major")


class ReleaseError(RuntimeError):
    """Anything that should stop the release with a readable message."""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    """Write LF endings so a version bump never shows up as a whole-file diff."""
    path.write_bytes(content.replace("\r\n", "\n").encode("utf-8"))


def log(message: str) -> None:
    print(f"  {message}")


def step(message: str) -> None:
    print(f"\n==> {message}")


def parse_version(raw: str) -> tuple[int, int, int]:
    match = SEMVER.match(raw.strip())
    if not match:
        raise ReleaseError(f"Not a semver version: {raw!r}")
    return int(match[1]), int(match[2]), int(match[3])


def next_version(current: str, spec: str) -> str:
    if SEMVER.match(spec):
        if parse_version(spec) <= parse_version(current):
            raise ReleaseError(
                f"Target version {spec} is not greater than the current {current}."
            )
        return spec

    major, minor, patch = parse_version(current)
    if spec == "patch":
        return f"{major}.{minor}.{patch + 1}"
    if spec == "minor":
        return f"{major}.{minor + 1}.0"
    if spec == "major":
        return f"{major + 1}.0.0"
    raise ReleaseError(
        f"Unknown bump {spec!r}; expected one of {BUMPS} or an explicit X.Y.Z."
    )


def read_extension_version() -> str:
    match = re.search(r'^\s*"version"\s*:\s*"([^"]+)"', read_text(EXTENSION_MANIFEST), re.M)
    if not match:
        raise ReleaseError(f'No "version" field in {EXTENSION_MANIFEST}')
    return match.group(1)


def read_cli_version() -> str:
    match = re.search(r'^version\s*=\s*"([^"]+)"', read_text(CLI_MANIFEST), re.M)
    if not match:
        raise ReleaseError(f"No version field in {CLI_MANIFEST}")
    return match.group(1)


def set_extension_version(version: str) -> None:
    # count=1: nested dependency blocks carry a "version" key too.
    updated, count = re.subn(
        r'^(\s*"version"\s*:\s*")[^"]+(")',
        r"\g<1>" + version + r"\g<2>",
        read_text(EXTENSION_MANIFEST),
        count=1,
        flags=re.M,
    )
    if count != 1:
        raise ReleaseError("Failed to rewrite the extension version.")
    write_text(EXTENSION_MANIFEST, updated)


def set_cli_version(version: str) -> None:
    updated, count = re.subn(
        r'^(version\s*=\s*")[^"]+(")',
        r"\g<1>" + version + r"\g<2>",
        read_text(CLI_MANIFEST),
        count=1,
        flags=re.M,
    )
    if count != 1:
        raise ReleaseError("Failed to rewrite the CLI version.")
    write_text(CLI_MANIFEST, updated)


def run(command: list[str], cwd: Path) -> None:
    log("$ " + " ".join(command))
    result = subprocess.run(command, cwd=cwd, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise ReleaseError(f"Command failed ({result.returncode}): {' '.join(command)}")


def tool(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise ReleaseError(f"{name} not found on PATH.")
    return found


def resolve_python() -> str:
    """Prefer the project venv over whatever interpreter launched this script.

    The repo is used from both Windows and WSL, and the interpreter that can run
    the script is not necessarily the one with the test dependencies installed.
    """
    candidates = (
        REPO_ROOT / ".venv" / "bin" / "python",
        REPO_ROOT / ".venv" / "Scripts" / "python.exe",
    )
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def ensure_pytest(python: str) -> None:
    try:
        probe = subprocess.run(
            [python, "-c", "import pytest"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        raise ReleaseError(f"Cannot run {python}: {exc}") from exc
    if probe.returncode == 0:
        return

    venv_python = "'.venv/bin/python'" if sys.platform != "win32" else r"'.venv\Scripts\python'"
    raise ReleaseError(
        f"pytest is not installed for {python}.\n"
        "    Set up a project environment once:\n"
        f"        {python} -m venv .venv\n"
        f"        {venv_python} -m pip install -e '.[dev]'\n"
        "    Or skip the test run with --skip-tests."
    )


def git_dirty_files() -> list[str]:
    """Modified tracked files only.

    Untracked files are ignored on purpose: they are not part of the commit the
    release is built from, and .vscodeignore already keeps them out of the
    package. Blocking on a stray scratch file would just train you to reach for
    --allow-dirty, which defeats the check.
    """
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return []
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="release.py",
        description="Bump, verify and package the EcoCode VS Code extension.",
    )
    parser.add_argument(
        "bump",
        help=f"Extension version: one of {', '.join(BUMPS)}, or an explicit X.Y.Z.",
    )
    parser.add_argument(
        "--cli",
        metavar="BUMP",
        help="Also bump the Python CLI version in pyproject.toml (same forms).",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would happen, change nothing."
    )
    parser.add_argument(
        "--skip-tests", action="store_true", help="Skip pytest (not recommended)."
    )
    parser.add_argument(
        "--allow-dirty", action="store_true", help="Package even with uncommitted changes."
    )
    args = parser.parse_args(argv)

    if not EXTENSION_MANIFEST.exists():
        raise ReleaseError(f"Missing {EXTENSION_MANIFEST}")
    for entry, package in ((TSC_ENTRY, "typescript"), (VSCE_ENTRY, "@vscode/vsce")):
        if not entry.exists():
            raise ReleaseError(
                f"Missing {package}. Run: npm install --prefix {EXTENSION_DIR}"
            )
    node = tool("node")

    current_ext = read_extension_version()
    target_ext = next_version(current_ext, args.bump)
    current_cli = read_cli_version()
    target_cli = next_version(current_cli, args.cli) if args.cli else current_cli

    step("Plan")
    log(f"extension : {current_ext} -> {target_ext}")
    log(f"cli       : {current_cli} -> {target_cli}" + ("" if args.cli else "   (unchanged)"))

    if args.dry_run:
        print("\nDry run: nothing written.")
        return 0

    dirty = git_dirty_files()
    if dirty and not args.allow_dirty:
        listed = "\n    ".join(dirty[:10])
        more = f"\n    ... and {len(dirty) - 10} more" if len(dirty) > 10 else ""
        raise ReleaseError(
            "Tracked files have uncommitted changes:\n"
            f"    {listed}{more}\n"
            "Commit them first, or pass --allow-dirty."
        )

    step("Checks")
    if args.skip_tests:
        log("pytest skipped (--skip-tests)")
    else:
        python = resolve_python()
        ensure_pytest(python)
        run([python, "-m", "pytest", "tests/", "-q"], cwd=REPO_ROOT)

    run([node, str(TSC_ENTRY), "-p", ".", "--noEmit"], cwd=EXTENSION_DIR)

    step("Bump")
    original_ext_manifest = EXTENSION_MANIFEST.read_bytes()
    original_cli_manifest = CLI_MANIFEST.read_bytes()
    set_extension_version(target_ext)
    log(f"{EXTENSION_MANIFEST.relative_to(REPO_ROOT)} -> {target_ext}")
    if args.cli:
        set_cli_version(target_cli)
        log(f"{CLI_MANIFEST.relative_to(REPO_ROOT)} -> {target_cli}")

    def rollback() -> None:
        EXTENSION_MANIFEST.write_bytes(original_ext_manifest)
        CLI_MANIFEST.write_bytes(original_cli_manifest)
        log("version bump rolled back")

    try:
        step("Build")
        run([node, str(TSC_ENTRY), "-p", "."], cwd=EXTENSION_DIR)

        step("Package")
        expected_name = f"ecocode-vscode-{target_ext}.vsix"
        for stale in EXTENSION_DIR.glob("*.vsix"):
            if stale.name != expected_name:
                log(f"removing stale {stale.name}")
                stale.unlink()
        run([node, str(VSCE_ENTRY), "package", "--out", expected_name], cwd=EXTENSION_DIR)
    except ReleaseError:
        rollback()
        raise

    vsix = EXTENSION_DIR / expected_name
    if not vsix.exists():
        produced = sorted(EXTENSION_DIR.glob("*.vsix"), key=lambda p: p.stat().st_mtime)
        if not produced:
            raise ReleaseError("vsce reported success but produced no .vsix.")
        vsix = produced[-1]

    step("Done")
    print(f"\n  Package: {vsix}")
    print(f"  Size:    {vsix.stat().st_size / 1024:.0f} KB")
    print("\n  Upload at https://marketplace.visualstudio.com/manage/publishers/ecocode")
    print("\n  Then, once you are happy with it:\n")

    files = str(EXTENSION_MANIFEST.relative_to(REPO_ROOT)).replace("\\", "/")
    if args.cli:
        files += " " + str(CLI_MANIFEST.relative_to(REPO_ROOT)).replace("\\", "/")
    print(f"    git add {files}")
    print(f'    git commit -m "chore(release): extension v{target_ext}"')
    print(f"    git tag vscode-v{target_ext}")
    if args.cli:
        print(f"    git tag cli-v{target_cli}")
    print("    git push && git push --tags\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReleaseError as exc:
        sys.stderr.write(f"\nerror: {exc}\n")
        raise SystemExit(1)
