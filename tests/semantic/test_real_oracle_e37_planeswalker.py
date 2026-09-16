"""M5 E37a: planeswalker loyalty (Teferi untap, Saheeli copy, Aminatou blink)."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, Zone
from mtg_loop_engine.semantics.ir import ActivatedAbility, ManaAmount
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


def test_e37a_cards_complete():
    for key in (
        "Teferi, Who Slows the Sunset",
        "Saheeli Rai",
        "Aminatou, the Fateshifter",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_teferi_plus_untaps_and_gains_loyalty():
    teferi = _compile("Teferi, Who Slows the Sunset").semantics
    ex = Executor({teferi.oracle_id: teferi})
    state = GameState(
        mana=ManaAmount(),
        permanents={
            "t": Permanent(
                object_id="t",
                oracle_id=teferi.oracle_id,
                name=teferi.name,
                counters={"loyalty": 4},
            ),
            "r": Permanent(
                object_id="r",
                oracle_id="oracle:rock",
                name="Rock",
                is_artifact=True,
                tapped=True,
            ),
        },
    )
    ab = next(a for a in teferi.abilities if isinstance(a, ActivatedAbility))
    assert (
        ex.activate(
            state,
            ActionStep(
                op="activate", actor="t", ability_id=ab.ability_id, target="r"
            ),
        )
        is None
    )
    assert state.permanents["r"].tapped is False
    assert state.permanents["t"].counters["loyalty"] == 5


def test_loyalty_hard_negative_insufficient():
    saheeli = _compile("Saheeli Rai").semantics
    ex = Executor({saheeli.oracle_id: saheeli})
    state = GameState(
        mana=ManaAmount(),
        permanents={
            "s": Permanent(
                object_id="s",
                oracle_id=saheeli.oracle_id,
                name=saheeli.name,
                counters={"loyalty": 1},
            ),
            "c": Permanent(
                object_id="c",
                oracle_id="oracle:c",
                name="Creature",
                is_creature=True,
                power=1,
                toughness=1,
            ),
        },
    )
    ab = next(a for a in saheeli.abilities if isinstance(a, ActivatedAbility))
    err = ex.activate(
        state,
        ActionStep(op="activate", actor="s", ability_id=ab.ability_id, target="c"),
    )
    assert err is not None
