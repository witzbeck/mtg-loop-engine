"""M5 E18: GY → hand recursion."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent, Zone
from mtg_loop_engine.semantics.ir import ActivatedAbility, CardSemantics, ManaAmount
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState, Permanent


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    mana_cost = _parse_mana_braces(row.mana_cost) if row.mana_cost else None
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-').replace(',', '')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=mana_cost,
        mana_value=row.mana_value,
    )


def test_e18_gy_cards_complete():
    for key in (
        "Eternal Witness",
        "Archaeomancer",
        "Auriok Salvagers",
        "Enduring Renewal",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.semantics.unsupported_fragments,
        )


def test_witness_returns_from_gy():
    witness = _compile("Eternal Witness").semantics
    spell = CardSemantics(
        oracle_id="oracle:bolt",
        name="Bolt",
        types=["Instant"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
        mana_value=1,
    )
    ex = Executor({witness.oracle_id: witness, spell.oracle_id: spell})
    state = GameState(
        permanents={
            "w": Permanent(
                object_id="w",
                oracle_id=witness.oracle_id,
                name=witness.name,
                is_creature=True,
            ),
            "s": Permanent(
                object_id="s",
                oracle_id=spell.oracle_id,
                name="Bolt",
                zone=Zone.GRAVEYARD,
            ),
        },
        mana=ManaAmount(),
    )
    ex._queue_triggers(state, TriggerEvent.ENTER_BATTLEFIELD, state.permanents["w"])
    assert (
        ex.resolve_trigger(
            state, ActionStep(op="resolve_trigger", target="s")
        )
        is None
    )
    assert state.permanents["s"].zone == Zone.HAND


def test_salvagers_returns_cheap_artifact():
    salvagers = _compile("Auriok Salvagers").semantics
    ab = next(a for a in salvagers.abilities if isinstance(a, ActivatedAbility))
    mox = CardSemantics(
        oracle_id="oracle:mox",
        name="Mox",
        types=["Artifact"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
        mana_value=0,
    )
    ex = Executor({salvagers.oracle_id: salvagers, mox.oracle_id: mox})
    state = GameState(
        permanents={
            "a": Permanent(
                object_id="a",
                oracle_id=salvagers.oracle_id,
                name=salvagers.name,
                is_creature=True,
            ),
            "m": Permanent(
                object_id="m",
                oracle_id=mox.oracle_id,
                name="Mox",
                zone=Zone.GRAVEYARD,
                is_artifact=True,
            ),
        },
        mana=ManaAmount(white=1, colorless=1),
    )
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="a", ability_id=ab.ability_id, target="m"),
        )
        is None
    )
    assert state.permanents["m"].zone == Zone.HAND


def test_renewal_returns_dead_creature_to_hand():
    renewal = _compile("Enduring Renewal").semantics
    fodder = CardSemantics(
        oracle_id="oracle:fodder",
        name="Fodder",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({renewal.oracle_id: renewal, fodder.oracle_id: fodder})
    state = GameState(
        permanents={
            "r": Permanent(
                object_id="r", oracle_id=renewal.oracle_id, name=renewal.name
            ),
            "f": Permanent(
                object_id="f",
                oracle_id=fodder.oracle_id,
                name="Fodder",
                is_creature=True,
            ),
        },
        mana=ManaAmount(),
    )
    ex.die(state, state.permanents["f"])
    assert state.permanents["f"].zone == Zone.GRAVEYARD
    assert state.pending_triggers
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.permanents["f"].zone == Zone.HAND


def test_gy_wrong_wording_stays_unsupported():
    report = compile_oracle_text(
        oracle_id="oracle:fake-gy",
        name="Fake GY",
        oracle_text="When this creature enters, exile target card from a graveyard.",
        types=["Creature"],
        mana_cost=ManaAmount(generic=1),
        mana_value=1,
    )
    assert report.semantics.relevant_unsupported()
