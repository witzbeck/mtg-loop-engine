"""M5 E11: scaled mana remainders."""

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


def test_e11_scaled_mana_cards_complete():
    for key in (
        "Magus of the Coffers",
        "Bighorner Rancher",
        "Arbor Adherent",
        "Kydele, Chosen of Kruphix",
        "Alena, Kessig Trapper",
        "Selvala, Heart of the Wilds",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.semantics.unsupported_fragments,
        )


def test_magus_swamp_mana():
    magus = _compile("Magus of the Coffers").semantics
    ab = next(a for a in magus.abilities if isinstance(a, ActivatedAbility))
    swamp = CardSemantics(
        oracle_id="oracle:swamp",
        name="Swamp",
        types=["Basic", "Land", "Swamp"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({magus.oracle_id: magus, swamp.oracle_id: swamp})
    state = GameState(
        permanents={
            "m": Permanent(
                object_id="m",
                oracle_id=magus.oracle_id,
                name=magus.name,
                is_creature=True,
                summoning_sick=False,
            ),
            "s1": Permanent(object_id="s1", oracle_id=swamp.oracle_id, name="Swamp"),
            "s2": Permanent(object_id="s2", oracle_id=swamp.oracle_id, name="Swamp"),
            "s3": Permanent(object_id="s3", oracle_id=swamp.oracle_id, name="Swamp"),
        },
        mana=ManaAmount(colorless=2),
    )
    assert (
        ex.activate(state, ActionStep(op="activate", actor="m", ability_id=ab.ability_id))
        is None
    )
    assert state.mana.black == 3


def test_kydele_drawn_mana():
    kydele = _compile("Kydele, Chosen of Kruphix").semantics
    ab = next(a for a in kydele.abilities if isinstance(a, ActivatedAbility))
    ex = Executor({kydele.oracle_id: kydele})
    state = GameState(
        permanents={
            "k": Permanent(
                object_id="k",
                oracle_id=kydele.oracle_id,
                name=kydele.name,
                is_creature=True,
                summoning_sick=False,
            )
        },
        mana=ManaAmount(),
        event_counters={"draw": 4},
    )
    assert (
        ex.activate(state, ActionStep(op="activate", actor="k", ability_id=ab.ability_id))
        is None
    )
    assert state.mana.colorless == 4


def test_alena_entered_this_turn_power():
    alena = _compile("Alena, Kessig Trapper").semantics
    ab = next(a for a in alena.abilities if isinstance(a, ActivatedAbility))
    dork = CardSemantics(
        oracle_id="oracle:dork",
        name="Dork",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({alena.oracle_id: alena, dork.oracle_id: dork})
    state = GameState(
        permanents={
            "a": Permanent(
                object_id="a",
                oracle_id=alena.oracle_id,
                name=alena.name,
                is_creature=True,
                summoning_sick=False,
                power=4,
                toughness=3,
            ),
            "d": Permanent(
                object_id="d",
                oracle_id=dork.oracle_id,
                name="Dork",
                is_creature=True,
                power=5,
                toughness=1,
                entered_this_turn=True,
            ),
            "old": Permanent(
                object_id="old",
                oracle_id=dork.oracle_id,
                name="Dork",
                is_creature=True,
                power=9,
                toughness=9,
                entered_this_turn=False,
            ),
        },
        mana=ManaAmount(),
    )
    assert (
        ex.activate(state, ActionStep(op="activate", actor="a", ability_id=ab.ability_id))
        is None
    )
    assert state.mana.red == 5


def test_scaled_mana_wrong_wording_stays_unsupported():
    report = compile_oracle_text(
        oracle_id="oracle:fake-scale",
        name="Fake Scale",
        oracle_text="{T}: Add {B} for each Mountain you control.",
        types=["Creature"],
        mana_cost=ManaAmount(black=1),
        mana_value=1,
    )
    assert report.semantics.relevant_unsupported()
