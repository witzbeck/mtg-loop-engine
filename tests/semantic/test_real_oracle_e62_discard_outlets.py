"""M5 E62: discard outlets (Mind Over Matter / Skirge / Glint-Horn)."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, VerificationStatus
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
    kwargs.setdefault("hand_you", 7)
    return GameState(**kwargs)


def test_e62_cards_complete():
    for key in ("Mind Over Matter", "Skirge Familiar", "Glint-Horn Buccaneer"):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_mind_over_matter_untaps_with_discard():
    mom = _compile("Mind Over Matter").semantics
    dork = CardSemantics(
        oracle_id="oracle:dork",
        name="Dork",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({mom.oracle_id: mom, dork.oracle_id: dork})
    state = _state(
        permanents={
            "m": Permanent(
                object_id="m",
                oracle_id=mom.oracle_id,
                name=mom.name,
            ),
            "d": Permanent(
                object_id="d",
                oracle_id=dork.oracle_id,
                name="Dork",
                is_creature=True,
                power=1,
                toughness=1,
                tapped=True,
            ),
        },
        hand_you=3,
    )
    ab = next(a for a in mom.abilities if isinstance(a, ActivatedAbility))
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="m", ability_id=ab.ability_id, target="d"),
        )
        is None
    )
    assert state.hand_you == 2
    assert state.permanents["d"].tapped is False


def test_discard_resource_deficit():
    mom = _compile("Mind Over Matter").semantics
    dork = CardSemantics(
        oracle_id="oracle:dork",
        name="Dork",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({mom.oracle_id: mom, dork.oracle_id: dork})
    state = _state(
        permanents={
            "m": Permanent(
                object_id="m",
                oracle_id=mom.oracle_id,
                name=mom.name,
            ),
            "d": Permanent(
                object_id="d",
                oracle_id=dork.oracle_id,
                name="Dork",
                is_creature=True,
                power=1,
                toughness=1,
                tapped=True,
            ),
        },
        hand_you=0,
    )
    ab = next(a for a in mom.abilities if isinstance(a, ActivatedAbility))
    err = ex.activate(
        state,
        ActionStep(op="activate", actor="m", ability_id=ab.ability_id, target="d"),
    )
    assert err is not None
    assert err.status == VerificationStatus.RESOURCE_DEFICIT


def test_skirge_adds_black_mana():
    skirge = _compile("Skirge Familiar").semantics
    ex = Executor({skirge.oracle_id: skirge})
    state = _state(
        permanents={
            "s": Permanent(
                object_id="s",
                oracle_id=skirge.oracle_id,
                name=skirge.name,
                is_creature=True,
                power=2,
                toughness=1,
            )
        },
        hand_you=2,
    )
    ab = next(a for a in skirge.abilities if isinstance(a, ActivatedAbility))
    assert (
        ex.activate(
            state, ActionStep(op="activate", actor="s", ability_id=ab.ability_id)
        )
        is None
    )
    assert state.hand_you == 1
    assert state.mana.black == 1


def test_glint_horn_discard_damages():
    glint = _compile("Glint-Horn Buccaneer").semantics
    mom = _compile("Mind Over Matter").semantics
    dork = CardSemantics(
        oracle_id="oracle:dork",
        name="Dork",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor(
        {glint.oracle_id: glint, mom.oracle_id: mom, dork.oracle_id: dork}
    )
    state = _state(
        permanents={
            "g": Permanent(
                object_id="g",
                oracle_id=glint.oracle_id,
                name=glint.name,
                is_creature=True,
                power=2,
                toughness=4,
            ),
            "m": Permanent(
                object_id="m",
                oracle_id=mom.oracle_id,
                name=mom.name,
            ),
            "d": Permanent(
                object_id="d",
                oracle_id=dork.oracle_id,
                name="Dork",
                is_creature=True,
                power=1,
                toughness=1,
                tapped=True,
            ),
        },
        hand_you=3,
        life_opponent=20,
    )
    ab = next(a for a in mom.abilities if isinstance(a, ActivatedAbility))
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="m", ability_id=ab.ability_id, target="d"),
        )
        is None
    )
    # DISCARD trigger pending from Mind Over Matter cost
    assert state.pending_triggers
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.life_opponent == 19
