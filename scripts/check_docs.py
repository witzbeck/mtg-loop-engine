#!/usr/bin/env python3
"""Lightweight repository documentation checks for CI."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    "out",
    "target",
    "coverage",
    ".next",
    ".turbo",
    ".cursor",
    ".idea",
    "data",  # gitignored snapshots; has its own README when present
}

# Meaningful trees that must carry a README.md (Agent 2 / package docs).
REQUIRED_README_DIRS = [
    ROOT,
    ROOT / "docs",
    ROOT / "docs" / "runbooks",
    ROOT / "docs" / "decisions",
    ROOT / "scripts",
    ROOT / "eval",
    ROOT / "eval" / "baseline",
    ROOT / "src",
    ROOT / "src" / "mtg_loop_engine",
    ROOT / "tests",
]

REQUIRED_FILES = [
    ROOT / "AGENTS.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "ROADMAP.md",
    ROOT / "docs" / "PHILOSOPHY.md",
    ROOT / "docs" / "ARCHITECTURE.md",
    ROOT / "docs" / "TERMINOLOGY.md",
    ROOT / "docs" / "STATUS.md",
    ROOT / "docs" / "EVALUATION.md",
    ROOT / "docs" / "ADJUDICATION.md",
    ROOT / "docs" / "CLI.md",
    ROOT / "docs" / "runbooks" / "M4_FOLLOW_THROUGH.md",
    ROOT / ".github" / "pull_request_template.md",
]

# Paths that docs frequently link; existence checked when referenced.
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _iter_markdown_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*.md"):
        parts = set(path.parts)
        if parts & SKIP_DIR_NAMES:
            continue
        if ".venv" in path.parts:
            continue
        files.append(path)
    return files


def check_required_files() -> list[str]:
    errors: list[str] = []
    for path in REQUIRED_FILES:
        if not path.is_file():
            errors.append(f"missing required file: {path.relative_to(ROOT)}")
    return errors


def check_readmes() -> list[str]:
    errors: list[str] = []
    for directory in REQUIRED_README_DIRS:
        readme = directory / "README.md"
        if not readme.is_file():
            errors.append(f"missing README.md in {directory.relative_to(ROOT) or '.'}")
    # Package subpackages under src/mtg_loop_engine (one level)
    pkg = ROOT / "src" / "mtg_loop_engine"
    if pkg.is_dir():
        for child in sorted(pkg.iterdir()):
            if child.is_dir() and child.name not in SKIP_DIR_NAMES and not child.name.startswith("__"):
                if not (child / "README.md").is_file():
                    errors.append(
                        f"missing README.md in {child.relative_to(ROOT)}"
                    )
    return errors


def _resolve_link(source: Path, target: str) -> Path | None:
    if target.startswith(("http://", "https://", "mailto:")):
        return None
    if target.startswith("#"):
        return None
    path_part = target.split("#", 1)[0]
    if not path_part:
        return None
    # Absolute-from-repo style (/docs/...) not used; treat as relative
    resolved = (source.parent / path_part).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return resolved  # outside repo — still check existence
    return resolved


def _link_check_sources() -> list[Path]:
    """Governance, narrative hub, and eval docs with stable internal links."""
    sources = [
        ROOT / "README.md",
        ROOT / "ROADMAP.md",
        ROOT / "AGENTS.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "docs" / "PHILOSOPHY.md",
        ROOT / "docs" / "ARCHITECTURE.md",
        ROOT / "docs" / "TERMINOLOGY.md",
        ROOT / "docs" / "STATUS.md",
        ROOT / "docs" / "EVALUATION.md",
        ROOT / "docs" / "ADJUDICATION.md",
        ROOT / "docs" / "CLI.md",
        ROOT / "docs" / "README.md",
        ROOT / "docs" / "runbooks" / "README.md",
        ROOT / "docs" / "runbooks" / "M4_FOLLOW_THROUGH.md",
        ROOT / "docs" / "decisions" / "README.md",
    ]
    return [p for p in sources if p.is_file()]


def check_internal_links() -> list[str]:
    errors: list[str] = []
    for md in _link_check_sources():
        text = md.read_text(encoding="utf-8")
        for _label, target in LINK_RE.findall(text):
            resolved = _resolve_link(md, target)
            if resolved is None:
                continue
            if not resolved.exists():
                errors.append(
                    f"broken link in {md.relative_to(ROOT)}: "
                    f"({target}) -> {resolved}"
                )
    return errors


def check_status_freshness() -> list[str]:
    """Optionally ensure STATUS generated section matches baselines."""
    render = ROOT / "scripts" / "render_status.py"
    if not render.is_file():
        return ["missing scripts/render_status.py"]
    # Import by path without installing
    import runpy
    from io import StringIO
    from contextlib import redirect_stdout, redirect_stderr

    stdout = StringIO()
    stderr = StringIO()
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            # Execute check mode
            sys_argv = sys.argv
            sys.argv = ["render_status.py", "--check"]
            try:
                ns = runpy.run_path(str(render), run_name="__not_main__")
                code = ns["main"](["--check"])
            finally:
                sys.argv = sys_argv
    except SystemExit as exc:
        code = int(exc.code or 0)
    if code != 0:
        msg = stderr.getvalue().strip() or stdout.getvalue().strip() or "STATUS out of sync"
        return [msg]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-status",
        action="store_true",
        help="Do not run render_status --check (CI runs it as a separate step)",
    )
    args = parser.parse_args(argv)

    errors: list[str] = []
    errors.extend(check_required_files())
    errors.extend(check_readmes())
    errors.extend(check_internal_links())
    if not args.skip_status:
        errors.extend(check_status_freshness())

    if errors:
        print("docs check failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print("OK: docs check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
