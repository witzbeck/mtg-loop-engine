"""The verify package must not import or mention the search package."""

from pathlib import Path

import mtg_loop_engine.verify as verify_pkg


def test_verify_package_does_not_import_search():
    root = Path(verify_pkg.__file__).resolve().parent
    offenders: list[str] = []
    for path in root.rglob("*"):
        if path.suffix not in {".py", ".md"}:
            continue
        text = path.read_text(encoding="utf-8")
        if "mtg_loop_engine.search" in text:
            offenders.append(str(path.relative_to(root)))
    assert not offenders, f"verify package mentions search: {offenders}"
