"""Gold_core load path must not rediscover via search."""

from __future__ import annotations

import ast
from pathlib import Path

from mtg_loop_engine.corpus import all_gold_core
from mtg_loop_engine.corpus.gold_core import oracle_cases


def test_oracle_cases_source_has_no_explore_import():
    path = Path(oracle_cases.__file__).resolve()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if "search" in node.module.split("."):
                raise AssertionError(
                    f"oracle_cases must not import search ({node.module})"
                )
            for alias in node.names:
                if alias.name == "explore_pair":
                    raise AssertionError("oracle_cases must not import explore_pair")
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "search" in alias.name.split("."):
                    raise AssertionError(
                        f"oracle_cases must not import search ({alias.name})"
                    )


def test_all_gold_core_does_not_call_explore_pair(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise AssertionError("explore_pair must not run during all_gold_core()")

    monkeypatch.setattr(
        "mtg_loop_engine.search.explorer.explore_pair",
        _boom,
    )
    witnesses = all_gold_core()
    assert {w.id for w in witnesses} == {
        "core_guard_gond",
        "core_altar_gravecrawler_live",
        "core_alarm_doomsayer",
        "core_bond_blood",
        "core_basalt_zirda",
        "core_druid_vizier",
        "core_rosie_scurry",
        "core_heliod_ballista",
        "core_bloodchief_mindcrank",
    }
    for w in witnesses:
        assert "oracle_exact_gold" in w.assumptions
        assert "compiled_from_audited_fixture" in w.assumptions
        assert "discovered_without_pair_labels" not in w.assumptions
        assert len(w.card_semantics) == 2
        assert w.expected_net_state is not None
        assert w.expected_claim_consequence is not None


def test_frozen_witness_files_exist():
    root = Path(oracle_cases.__file__).resolve().parent / "witnesses"
    for gold_id in (
        "core_guard_gond",
        "core_altar_gravecrawler_live",
        "core_alarm_doomsayer",
        "core_bond_blood",
        "core_basalt_zirda",
        "core_druid_vizier",
        "core_rosie_scurry",
        "core_heliod_ballista",
        "core_bloodchief_mindcrank",
    ):
        assert (root / f"{gold_id}.json").is_file()
