#!/usr/bin/env python3
"""Deliberate re-freeze of Oracle gold_core witnesses (reviewed artifacts).

Captures blind ``explore_pair`` hits into JSON under
``src/mtg_loop_engine/corpus/gold_core/witnesses/``. Runtime gold loading must
**not** call this path — re-freeze only after human review of search changes.

Usage (from repo root)::

    uv run python scripts/freeze_gold_witnesses.py
    uv run python scripts/freeze_gold_witnesses.py --check  # fail if drift
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mtg_loop_engine.corpus.builders import witness as rebuild_witness
from mtg_loop_engine.proofs.models import LoopWitness, NetStateDelta
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import Consequence
from mtg_loop_engine.semantics.ir import ManaAmount
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES
from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.verify.verifier import Verifier

REPO_ROOT = Path(__file__).resolve().parents[1]
WITNESSES_DIR = (
    REPO_ROOT / "src" / "mtg_loop_engine" / "corpus" / "gold_core" / "witnesses"
)

ARTIFACT_SCHEMA_VERSION = 1
GOLD_ASSUMPTIONS = ("oracle_exact_gold", "compiled_from_audited_fixture")

# Fields frozen on disk (card_semantics recompiled from fixtures on load).
_FROZEN_KEYS = (
    "id",
    "classification",
    "essential_cards",
    "initial_state",
    "setup_actions",
    "loop_actions",
    "relevant_state",
    "expected_outputs",
    "expected_net_state",
    "expected_claim_consequence",
    "assumptions",
    "prerequisites",
    "deterministic",
    "semantic_coverage",
    "tier",
)

CASES: list[dict] = [
    {
        "gold_id": "core_guard_gond",
        "left_id": "oracle:midnight-guard",
        "right_id": "oracle:presence-of-gond",
        "expected_net_state": NetStateDelta(creature_tokens=1),
        "expected_claim_consequence": Consequence.ACCUMULATES,
        "max_depth": 8,
    },
    {
        "gold_id": "core_altar_gravecrawler_live",
        "left_id": "oracle:phyrexian-altar",
        "right_id": "oracle:gravecrawler",
        "expected_net_state": NetStateDelta(),
        "expected_claim_consequence": Consequence.REPEATABLE_EVENT,
        "max_depth": 8,
    },
    {
        "gold_id": "core_alarm_doomsayer",
        "left_id": "oracle:intruder-alarm",
        "right_id": "oracle:thraben-doomsayer",
        "expected_net_state": NetStateDelta(creature_tokens=1),
        "expected_claim_consequence": Consequence.ACCUMULATES,
        "max_depth": 8,
    },
    {
        "gold_id": "core_bond_blood",
        "left_id": "oracle:sanguine-bond",
        "right_id": "oracle:exquisite-blood",
        "expected_net_state": NetStateDelta(life_you=1, life_opponent=-1),
        "expected_claim_consequence": Consequence.LETHAL,
        "max_depth": 8,
    },
    {
        "gold_id": "core_basalt_zirda",
        "left_id": "oracle:basalt-monolith",
        "right_id": "oracle:zirda-the-dawnwaker",
        "expected_net_state": NetStateDelta(mana=ManaAmount(colorless=2)),
        "expected_claim_consequence": Consequence.ACCUMULATES,
        "max_depth": 8,
    },
    {
        "gold_id": "core_druid_vizier",
        "left_id": "oracle:devoted-druid",
        "right_id": "oracle:vizier-of-remedies",
        "expected_net_state": NetStateDelta(mana=ManaAmount(green=1)),
        "expected_claim_consequence": Consequence.ACCUMULATES,
        "max_depth": 8,
    },
    {
        "gold_id": "core_rosie_scurry",
        "left_id": "oracle:rosie-cotton-of-south-lane",
        "right_id": "oracle:scurry-oak",
        "expected_net_state": NetStateDelta(creature_tokens=1, plus_one_counters=1),
        "expected_claim_consequence": Consequence.ACCUMULATES,
        "max_depth": 10,
    },
]


def _compile(oracle_id: str):
    fix = GOLD_ORACLE_FIXTURES[oracle_id]
    report = compile_oracle_text(
        oracle_id=fix.oracle_id,
        name=fix.name,
        oracle_text=fix.oracle_text,
        types=fix.types,
    )
    if report.coverage.value != "complete":
        raise RuntimeError(
            f"{oracle_id} incomplete: {report.semantics.unsupported_fragments}"
        )
    return report.semantics


def _capture_case(case: dict) -> LoopWitness:
    gold_id = case["gold_id"]
    left = _compile(case["left_id"])
    right = _compile(case["right_id"])
    expected_net = case["expected_net_state"]
    expected_claim = case["expected_claim_consequence"]
    max_depth = case["max_depth"]
    hit = explore_pair(
        left,
        right,
        max_depth=max_depth,
        expected_net_state=expected_net,
        expected_claim_consequence=expected_claim,
    ) or explore_pair(
        right,
        left,
        max_depth=max_depth,
        expected_net_state=expected_net,
        expected_claim_consequence=expected_claim,
    )
    if hit is None:
        raise RuntimeError(f"failed to rediscover {gold_id} for freeze")
    stamped = hit.witness.model_copy(
        update={
            "id": gold_id,
            "expected_net_state": expected_net,
            "expected_claim_consequence": expected_claim,
        }
    )
    proof = Verifier().verify(stamped)
    if proof.status.value != "verified":
        raise RuntimeError(
            f"{gold_id} failed net-gated verify: {proof.status} {proof.rejection_reason}"
        )
    w = hit.witness
    assumptions = [
        a for a in w.assumptions if a != "discovered_without_pair_labels"
    ]
    for tag in GOLD_ASSUMPTIONS:
        if tag not in assumptions:
            assumptions.append(tag)
    return rebuild_witness(
        id=gold_id,
        classification=w.classification,
        essential_cards=w.essential_cards,
        card_semantics=w.card_semantics,
        initial_state=w.initial_state,
        setup_actions=w.setup_actions,
        loop_actions=w.loop_actions,
        relevant_state=w.relevant_state,
        expected_outputs=w.expected_outputs,
        expected_net_state=expected_net,
        expected_claim_consequence=expected_claim,
        prerequisites=w.prerequisites,
        assumptions=assumptions,
    )


def _artifact_payload(witness: LoopWitness) -> dict:
    dumped = witness.model_dump(mode="json")
    body = {key: dumped[key] for key in _FROZEN_KEYS}
    if "discovered_without_pair_labels" in body["assumptions"]:
        raise RuntimeError(f"{witness.id}: discovery assumption leaked into freeze")
    return {"artifact_schema_version": ARTIFACT_SCHEMA_VERSION, **body}


def _path_for(gold_id: str) -> Path:
    return WITNESSES_DIR / f"{gold_id}.json"


def freeze_all(*, check: bool) -> int:
    WITNESSES_DIR.mkdir(parents=True, exist_ok=True)
    drift: list[str] = []
    for case in CASES:
        gold_id = case["gold_id"]
        witness = _capture_case(case)
        payload = _artifact_payload(witness)
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        path = _path_for(gold_id)
        if check:
            if not path.is_file():
                drift.append(f"missing {path.name}")
                continue
            existing = path.read_text(encoding="utf-8")
            if existing != text:
                drift.append(f"drift {path.name}")
            continue
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path.relative_to(REPO_ROOT)}")
    if check and drift:
        print("freeze check failed:", ", ".join(drift), file=sys.stderr)
        return 1
    if check:
        print(f"ok: {len(CASES)} frozen witnesses match explore capture")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if committed JSON differs from a fresh explore capture",
    )
    args = parser.parse_args()
    return freeze_all(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
