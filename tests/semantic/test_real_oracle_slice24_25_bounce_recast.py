"""M5 slices 24–25: cast-from-hand + Aluren; Banishing Knack / Retraction Helix grant."""

from mtg_loop_engine.corpus.builders import bf
from mtg_loop_engine.proofs.models import ActionStep, InitialStateSpec
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, VerificationStatus, Zone
from mtg_loop_engine.semantics.ir import (
    FreeCastCreaturesByManaValue,
    InstantGrantTapBounce,
    ManaAmount,
)
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    slug = key.lower().replace(" ", "-")
    cost = _parse_mana_braces(row.mana_cost) if row.mana_cost else ManaAmount()
    return compile_oracle_text(
        oracle_id=f"oracle:{slug}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=cost,
        mana_value=row.mana_value,
    )


def test_aluren_compiles_complete():
    report = _compile("Aluren")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    free = next(
        a for a in report.semantics.abilities if isinstance(a, FreeCastCreaturesByManaValue)
    )
    assert free.max_mana_value == 3


def test_knack_helix_compile_complete():
    for key in ("Banishing Knack", "Retraction Helix"):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
        assert any(isinstance(a, InstantGrantTapBounce) for a in report.semantics.abilities)


def test_cast_from_hand_free_under_aluren():
    aluren = _compile("Aluren").semantics
    drake = _compile("Shrieking Drake").semantics
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                bf("a", aluren.oracle_id, aluren.name),
                bf(
                    "d",
                    drake.oracle_id,
                    drake.name,
                    is_creature=True,
                    power=1,
                    toughness=1,
                    zone=Zone.HAND,
                ),
            ]
        )
    )
    ex = Executor({aluren.oracle_id: aluren, drake.oracle_id: drake})
    err = ex.run_step(state, ActionStep(op="cast_from_hand", actor="d"))
    assert err is None
    assert state.permanents["d"].zone == Zone.BATTLEFIELD
    assert state.event_counters.get("cast", 0) == 1
    assert state.event_counters.get("etb", 0) == 1


def test_granted_tap_bounce_returns_nonland():
    host = bf("h", "setup:host", "Host", is_creature=True, power=1, toughness=1)
    target = bf("t", "setup:target", "Target", is_creature=True, power=1, toughness=1)
    state = GameState.from_spec(InitialStateSpec(permanents=[host, target]))
    state.permanents["h"].tap_bounce_nonland = True
    ex = Executor({})
    err = ex.run_step(
        state,
        ActionStep(op="activate_granted_tap_bounce", actor="h", target="t"),
    )
    assert err is None
    assert state.permanents["h"].tapped
    assert state.permanents["t"].zone == Zone.HAND


def test_grant_tap_bounce_effect_and_move_nonland():
    from mtg_loop_engine.semantics.ir import (
        GrantTapBounceNonlandEffect,
        MoveToZoneEffect,
    )

    knack = _compile("Banishing Knack").semantics
    host = bf("h", "setup:host", "Host", is_creature=True, power=1, toughness=1)
    rock = bf(
        "r",
        "setup:rock",
        "Rock",
        is_creature=False,
        is_artifact=True,
    )
    land = bf("l", "setup:land", "Land", is_creature=False)
    state = GameState.from_spec(InitialStateSpec(permanents=[host, rock, land]))
    ex = Executor(
        {
            knack.oracle_id: knack,
            "setup:host": _compile("Shrieking Drake").semantics.model_copy(
                update={"oracle_id": "setup:host", "types": ["Creature"]}
            ),
            "setup:rock": _compile("Mesmeric Orb").semantics.model_copy(
                update={"oracle_id": "setup:rock", "types": ["Artifact"]}
            ),
            "setup:land": _compile("Aluren").semantics.model_copy(
                update={"oracle_id": "setup:land", "types": ["Land"]}
            ),
        }
    )
    err = ex.apply_effects(
        state,
        state.permanents["h"],
        [GrantTapBounceNonlandEffect()],
        "h",
    )
    assert err is None
    assert state.permanents["h"].tap_bounce_nonland
    err = ex.apply_effects(
        state,
        state.permanents["h"],
        [MoveToZoneEffect(zone=Zone.HAND, target="target_nonland")],
        "r",
    )
    assert err is None
    assert state.permanents["r"].zone == Zone.HAND
    err = ex.apply_effects(
        state,
        state.permanents["h"],
        [MoveToZoneEffect(zone=Zone.HAND, target="target_nonland")],
        "l",
    )
    assert err is not None
    assert err.status == VerificationStatus.ILLEGAL_TARGET


def test_cast_from_hand_pays_mana_without_aluren():
    drake = _compile("Shrieking Drake").semantics
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                bf(
                    "d",
                    drake.oracle_id,
                    drake.name,
                    is_creature=True,
                    power=1,
                    toughness=1,
                    zone=Zone.HAND,
                ),
            ],
            mana=ManaAmount(blue=1),
        )
    )
    ex = Executor({drake.oracle_id: drake})
    err = ex.run_step(state, ActionStep(op="cast_from_hand", actor="d"))
    assert err is None
    assert state.permanents["d"].zone == Zone.BATTLEFIELD
    assert state.mana.blue == 0


def test_drake_plus_aluren_rediscovers():
    drake = _compile("Shrieking Drake").semantics
    aluren = _compile("Aluren").semantics
    found = explore_pair(drake, aluren, max_depth=8)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert "Shrieking Drake" in names
    assert "Aluren" in names
    assert any(s.op == "cast_from_hand" for s in found.witness.loop_actions)


def test_lion_plus_aluren_rediscovers():
    lion = _compile("Whitemane Lion").semantics
    aluren = _compile("Aluren").semantics
    found = explore_pair(lion, aluren, max_depth=8)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert "Whitemane Lion" in names
    assert "Aluren" in names


def test_knack_plus_alarm_rediscovers():
    knack = _compile("Banishing Knack").semantics
    alarm = _compile("Intruder Alarm Live").semantics
    found = explore_pair(knack, alarm, max_depth=12)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert "Banishing Knack" in names
    assert "Intruder Alarm" in names
    assert any(s.op == "activate_granted_tap_bounce" for s in found.witness.loop_actions)
    assert any(s.op == "cast_from_hand" for s in found.witness.loop_actions)


def test_helix_plus_alarm_rediscovers():
    helix = _compile("Retraction Helix").semantics
    alarm = _compile("Intruder Alarm Live").semantics
    found = explore_pair(helix, alarm, max_depth=12)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
