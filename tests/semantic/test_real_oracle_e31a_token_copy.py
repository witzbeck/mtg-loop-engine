"""M5 E31a: token-copy with haste (Kiki / Twin)."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage
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


def _state(**kwargs) -> GameState:
    kwargs.setdefault("mana", ManaAmount())
    return GameState(**kwargs)


def test_e31a_cards_complete():
    for key in ("Kiki-Jiki, Mirror Breaker", "Splinter Twin"):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_kiki_copies_target_with_haste():
    kiki = _compile("Kiki-Jiki, Mirror Breaker").semantics
    beater = CardSemantics(
        oracle_id="oracle:beater",
        name="Beater",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({kiki.oracle_id: kiki, beater.oracle_id: beater})
    state = _state(
        permanents={
            "k": Permanent(
                object_id="k",
                oracle_id=kiki.oracle_id,
                name=kiki.name,
                is_creature=True,
                power=2,
                toughness=2,
            ),
            "b": Permanent(
                object_id="b",
                oracle_id=beater.oracle_id,
                name="Beater",
                is_creature=True,
                power=4,
                toughness=4,
            ),
        }
    )
    ab = next(a for a in kiki.abilities if isinstance(a, ActivatedAbility))
    before = len(state.permanents)
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="k", ability_id=ab.ability_id, target="b"),
        )
        is None
    )
    assert len(state.permanents) == before + 1
    tok = next(p for p in state.permanents.values() if p.is_token)
    assert tok.name == "Beater"
    assert tok.power == 4 and tok.toughness == 4
    assert tok.summoning_sick is False


def test_twin_grant_copies_host():
    twin = _compile("Splinter Twin").semantics
    beater = CardSemantics(
        oracle_id="oracle:beater",
        name="Beater",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({twin.oracle_id: twin, beater.oracle_id: beater})
    state = _state(
        permanents={
            "t": Permanent(
                object_id="t",
                oracle_id=twin.oracle_id,
                name=twin.name,
            ),
            "b": Permanent(
                object_id="b",
                oracle_id=beater.oracle_id,
                name="Beater",
                is_creature=True,
                power=3,
                toughness=3,
            ),
        }
    )
    granted = ex.iter_granted_activated(state, state.permanents["b"])
    assert granted
    ab = granted[0]
    before = len(state.permanents)
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="b", ability_id=ab.ability_id),
        )
        is None
    )
    assert len(state.permanents) == before + 1
    tok = next(p for p in state.permanents.values() if p.is_token)
    assert tok.name == "Beater" and tok.summoning_sick is False
