"""M5 E55: spell / affinity cost reduction."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text, split_oracle_abilities
from mtg_loop_engine.semantics.enums import SemanticCoverage, Zone
from mtg_loop_engine.semantics.ir import (
    CardSemantics,
    ManaAmount,
)
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState, Permanent


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    mana_cost = _parse_mana_braces(row.mana_cost) if row.mana_cost else None
    return compile_oracle_text(
        oracle_id=(
            f"oracle:{key.lower().replace(' ', '-').replace(',', '').replace(chr(39), '')}"
        ),
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=mana_cost,
        mana_value=row.mana_value,
    )


def test_e55_cards_complete():
    for key in (
        "Temur Battlecrier",
        "Sami, Wildcat Captain",
        "Animar, Soul of Elements",
        "Marauding Raptor",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_split_keyword_list_and_animar_join():
    sami = split_oracle_abilities(
        "Double strike, vigilance\n"
        "Spells you cast have affinity for artifacts. "
        "(They cost {1} less to cast for each artifact you control.)"
    )
    assert sami[0] == "Double strike, vigilance"
    assert sami[1].startswith("Spells you cast have affinity")

    animar = split_oracle_abilities(
        "Whenever you cast a creature spell, put a +1/+1 counter on Animar. "
        "Creature spells you cast cost {1} less to cast for each +1/+1 counter on Animar."
    )
    assert len(animar) == 2
    assert animar[0].startswith("Whenever you cast")
    assert animar[1].startswith("Creature spells you cast cost")


def test_affinity_reduces_cast_generic():
    sami = _compile("Sami, Wildcat Captain").semantics
    creature = CardSemantics(
        oracle_id="oracle:fodder",
        name="Fodder",
        types=["Creature"],
        mana_cost=ManaAmount(generic=3, red=1),
        mana_value=4,
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({sami.oracle_id: sami, creature.oracle_id: creature})
    state = GameState(
        mana=ManaAmount(generic=0, red=1, colorless=1),
        permanents={
            "s": Permanent(
                object_id="s",
                oracle_id=sami.oracle_id,
                name=sami.name,
                is_creature=True,
                is_artifact=False,
                power=2,
                toughness=2,
            ),
            "a1": Permanent(
                object_id="a1",
                oracle_id="oracle:sol",
                name="Sol Ring",
                is_artifact=True,
                zone=Zone.BATTLEFIELD,
            ),
            "a2": Permanent(
                object_id="a2",
                oracle_id="oracle:sol2",
                name="Mana Crypt",
                is_artifact=True,
                zone=Zone.BATTLEFIELD,
            ),
            "c": Permanent(
                object_id="c",
                oracle_id=creature.oracle_id,
                name="Fodder",
                is_creature=True,
                zone=Zone.HAND,
                power=1,
                toughness=1,
            ),
        },
    )
    # Affinity: −2 generic from two artifacts → pay {R}{1} only.
    assert (
        ex.cast_from_hand(state, ActionStep(op="cast_from_hand", actor="c")) is None
    )
    assert state.permanents["c"].zone == Zone.BATTLEFIELD
    assert state.mana.red == 0
    assert state.mana.colorless == 0


def test_creature_spell_reduction_hard_negative_noncreature():
    """Creature-spell reducers do not discount noncreature casts."""
    raptor = _compile("Marauding Raptor").semantics
    artifact = CardSemantics(
        oracle_id="oracle:rock",
        name="Rock",
        types=["Artifact"],
        mana_cost=ManaAmount(generic=2),
        mana_value=2,
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({raptor.oracle_id: raptor, artifact.oracle_id: artifact})
    state = GameState(
        mana=ManaAmount(colorless=1),
        permanents={
            "r": Permanent(
                object_id="r",
                oracle_id=raptor.oracle_id,
                name=raptor.name,
                is_creature=True,
                power=2,
                toughness=2,
            ),
            "a": Permanent(
                object_id="a",
                oracle_id=artifact.oracle_id,
                name="Rock",
                is_artifact=True,
                zone=Zone.HAND,
            ),
        },
    )
    err = ex.cast_from_hand(state, ActionStep(op="cast_from_hand", actor="a"))
    assert err is not None
    assert state.permanents["a"].zone == Zone.HAND


def test_animar_p1p1_scales_creature_spell_cost():
    animar = _compile("Animar, Soul of Elements").semantics
    creature = CardSemantics(
        oracle_id="oracle:beast",
        name="Beast",
        types=["Creature"],
        mana_cost=ManaAmount(generic=3, green=1),
        mana_value=4,
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({animar.oracle_id: animar, creature.oracle_id: creature})
    state = GameState(
        mana=ManaAmount(green=1, colorless=1),
        permanents={
            "a": Permanent(
                object_id="a",
                oracle_id=animar.oracle_id,
                name=animar.name,
                is_creature=True,
                power=3,
                toughness=3,
                counters={"p1p1": 2},
            ),
            "c": Permanent(
                object_id="c",
                oracle_id=creature.oracle_id,
                name="Beast",
                is_creature=True,
                zone=Zone.HAND,
                power=2,
                toughness=2,
            ),
        },
    )
    # −2 generic from two p1p1 → pay {G}{1}.
    assert (
        ex.cast_from_hand(state, ActionStep(op="cast_from_hand", actor="c")) is None
    )
    assert state.permanents["c"].zone == Zone.BATTLEFIELD
