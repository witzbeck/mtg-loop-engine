"""Executor contracts for {Q} untap-symbol cost payment."""

from mtg_loop_engine.proofs.models import ActionStep, InitialStateSpec, PermanentSpec
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    CardSemantics,
    ManaAmount,
    ManaCost,
    UntapSymbolCost,
)
from mtg_loop_engine.state.game import GameState


def test_untap_symbol_on_host_untaps_tapped_creature():
    equipment = CardSemantics(
        oracle_id="oracle:umbral",
        name="Umbral Mantle",
        types=["Artifact", "Equipment"],
        abilities=[
            ActivatedAbility(
                ability_id="equipped-untap-pump",
                costs=[
                    ManaCost(amount=ManaAmount(generic=3)),
                    UntapSymbolCost(source_self=False),
                ],
                effects=[],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    host = CardSemantics(
        oracle_id="oracle:priest",
        name="Priest",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    semantics = {equipment.oracle_id: equipment, host.oracle_id: host}
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="c0",
                    oracle_id=equipment.oracle_id,
                    name="Umbral Mantle",
                    is_artifact=True,
                ),
                PermanentSpec(
                    object_id="c1",
                    oracle_id=host.oracle_id,
                    name="Priest",
                    is_creature=True,
                    tapped=True,
                ),
            ],
            mana=ManaAmount(colorless=3),
        )
    )
    err = Executor(semantics).activate(
        state,
        ActionStep(
            op="activate",
            actor="c0",
            ability_id="equipped-untap-pump",
            target="c1",
        ),
    )
    assert err is None
    assert state.permanents["c1"].tapped is False
    assert state.mana.colorless == 0


def test_untap_symbol_rejects_untapped_host():
    equipment = CardSemantics(
        oracle_id="oracle:umbral",
        name="Umbral Mantle",
        types=["Artifact", "Equipment"],
        abilities=[
            ActivatedAbility(
                ability_id="equipped-untap-pump",
                costs=[UntapSymbolCost(source_self=False)],
                effects=[],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    host = CardSemantics(
        oracle_id="oracle:priest",
        name="Priest",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    semantics = {equipment.oracle_id: equipment, host.oracle_id: host}
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="c0",
                    oracle_id=equipment.oracle_id,
                    name="Umbral Mantle",
                    is_artifact=True,
                ),
                PermanentSpec(
                    object_id="c1",
                    oracle_id=host.oracle_id,
                    name="Priest",
                    is_creature=True,
                    tapped=False,
                ),
            ]
        )
    )
    err = Executor(semantics).activate(
        state,
        ActionStep(
            op="activate",
            actor="c0",
            ability_id="equipped-untap-pump",
            target="c1",
        ),
    )
    assert err is not None
    assert "tapped" in err.message.lower()
