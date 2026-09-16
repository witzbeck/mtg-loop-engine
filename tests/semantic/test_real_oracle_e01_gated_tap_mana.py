"""M5 E01: gated / restricted tap-mana (inventory epic)."""

import pytest

from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.search.explorer import (
    FEROCIOUS_CREATURE_SEED_ORACLE_ID,
    HAND_ARTIFACT_SEED_ORACLE_ID,
    default_initial_state,
    explore_pair,
)
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import ManaScaleKind, SemanticCoverage, VerificationStatus
from mtg_loop_engine.semantics.ir import ActivatedAbility, AddManaEffect, ManaAmount, TapCreatureCost
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState, Permanent
from mtg_loop_engine.semantics.enums import Zone


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    mana_cost = None
    if row.mana_cost:
        from mtg_loop_engine.semantics.patterns import _parse_mana_braces

        mana_cost = _parse_mana_braces(row.mana_cost)
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-').replace(chr(39), '')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=mana_cost,
        mana_value=row.mana_value,
    )


@pytest.mark.parametrize(
    "key",
    [
        "Metalworker",
        "Omen Hawker",
        "Mox Opal",
        "Fanatic of Rhonas",
        "Supportive Parents",
    ],
)
def test_e01_cards_compile_complete(key: str):
    report = _compile(key)
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments


def test_metalworker_hand_artifact_scale():
    report = _compile("Metalworker")
    ab = next(
        a
        for a in report.semantics.abilities
        if isinstance(a, ActivatedAbility) and a.is_mana_ability
    )
    effect = ab.effects[0]
    assert isinstance(effect, AddManaEffect)
    assert effect.mana_scale == ManaScaleKind.HAND_ARTIFACTS
    assert effect.scale_multiplier == 2


def test_mox_opal_requires_metalcraft():
    report = _compile("Mox Opal")
    ab = next(a for a in report.semantics.abilities if isinstance(a, ActivatedAbility))
    assert ab.requires_metalcraft is True


def test_fanatic_ferocious_gate():
    report = _compile("Fanatic of Rhonas")
    ferocious = next(
        a
        for a in report.semantics.abilities
        if isinstance(a, ActivatedAbility) and a.requires_controlled_power_at_least == 4
    )
    assert ferocious.effects[0].amount.green == 4


def test_omen_hawker_spend_only():
    report = _compile("Omen Hawker")
    ab = next(a for a in report.semantics.abilities if isinstance(a, ActivatedAbility))
    assert ab.effects[0].spend_only == "activate_abilities"


def test_supportive_parents_tap_two():
    report = _compile("Supportive Parents")
    ab = next(a for a in report.semantics.abilities if isinstance(a, ActivatedAbility))
    cost = ab.costs[0]
    assert isinstance(cost, TapCreatureCost)
    assert cost.quantity == 2
    assert cost.allow_source is True


def test_metalcraft_gate_fail_closed_without_artifacts():
    mox = _compile("Mox Opal").semantics
    ex = Executor({mox.oracle_id: mox})
    state = GameState(
        permanents={
            "mox": Permanent(
                object_id="mox",
                oracle_id=mox.oracle_id,
                name="Mox Opal",
                is_artifact=True,
            )
        },
        mana=ManaAmount(),
    )
    ab = next(a for a in mox.abilities if isinstance(a, ActivatedAbility))
    from mtg_loop_engine.proofs.models import ActionStep

    err = ex.activate(
        state,
        ActionStep(op="activate", actor="mox", ability_id=ab.ability_id),
    )
    assert err is not None
    assert err.status == VerificationStatus.ILLEGAL_ACTION


def test_spend_only_mana_cannot_pay_cast():
    omen = _compile("Omen Hawker").semantics
    sol = _compile("Sol Ring").semantics
    ex = Executor({omen.oracle_id: omen, sol.oracle_id: sol})
    state = GameState(
        permanents={
            "omen": Permanent(
                object_id="omen",
                oracle_id=omen.oracle_id,
                name="Omen Hawker",
                is_creature=True,
                power=1,
                toughness=1,
            ),
            "sol": Permanent(
                object_id="sol",
                oracle_id=sol.oracle_id,
                name="Sol Ring",
                is_artifact=True,
                zone=Zone.HAND,
            ),
        },
        mana=ManaAmount(),
    )
    ab = next(a for a in omen.abilities if isinstance(a, ActivatedAbility))
    from mtg_loop_engine.proofs.models import ActionStep

    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="omen", ability_id=ab.ability_id),
        )
        is None
    )
    assert state.mana_activate_only.colorless == 1
    assert state.mana_activate_only.blue == 1
    assert state.mana.total() == 0
    err = ex.cast_from_hand(
        state,
        ActionStep(op="cast_from_hand", actor="sol"),
    )
    assert err is not None
    assert err.status in {
        VerificationStatus.MANA_RESTRICTION,
        VerificationStatus.RESOURCE_DEFICIT,
    }


def test_metalworker_seeds_hand_artifacts_for_staff():
    metal = _compile("Metalworker").semantics
    staff = _compile("Staff of Domination").semantics
    spec = default_initial_state(metal, staff)
    hand_arts = [
        p for p in spec.permanents if p.oracle_id == HAND_ARTIFACT_SEED_ORACLE_ID
    ]
    assert len(hand_arts) == 3


def test_fanatic_seeds_ferocious_creature():
    fanatic = _compile("Fanatic of Rhonas").semantics
    staff = _compile("Staff of Domination").semantics
    spec = default_initial_state(fanatic, staff)
    assert any(p.oracle_id == FEROCIOUS_CREATURE_SEED_ORACLE_ID for p in spec.permanents)


def test_metalworker_plus_staff_rediscovers():
    metal = _compile("Metalworker").semantics
    staff = _compile("Staff of Domination").semantics
    found = explore_pair(metal, staff, max_depth=10)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert names == {"Metalworker", "Staff of Domination"}


def test_fanatic_plus_staff_rediscovers():
    fanatic = _compile("Fanatic of Rhonas").semantics
    staff = _compile("Staff of Domination").semantics
    found = explore_pair(fanatic, staff, max_depth=10)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert names == {"Fanatic of Rhonas", "Staff of Domination"}


def test_omen_plus_freed_rediscovers():
    omen = _compile("Omen Hawker").semantics
    freed = _compile("Freed from the Real").semantics
    found = explore_pair(omen, freed, max_depth=10)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert names == {"Omen Hawker", "Freed from the Real"}
