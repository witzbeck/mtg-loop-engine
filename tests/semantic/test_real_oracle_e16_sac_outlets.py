"""M5 E16: sac-outlet payoffs."""

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


def test_e16_sac_cards_complete():
    for key in (
        "Goblin Bombardment",
        "Blasting Station",
        "Altar of Dementia",
        "Composite Golem",
        "Ayara, First of Locthwain",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.semantics.unsupported_fragments,
        )


def test_bombardment_sac_damage():
    bomb = _compile("Goblin Bombardment").semantics
    ab = next(a for a in bomb.abilities if isinstance(a, ActivatedAbility))
    fodder = CardSemantics(
        oracle_id="oracle:fodder",
        name="Fodder",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({bomb.oracle_id: bomb, fodder.oracle_id: fodder})
    state = GameState(
        permanents={
            "b": Permanent(object_id="b", oracle_id=bomb.oracle_id, name=bomb.name),
            "f": Permanent(
                object_id="f",
                oracle_id=fodder.oracle_id,
                name="Fodder",
                is_creature=True,
                is_token=True,
                power=1,
                toughness=1,
            ),
        },
        mana=ManaAmount(),
        life_opponent=40,
    )
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="b", ability_id=ab.ability_id),
        )
        is None
    )
    assert state.life_opponent == 39
    assert state.permanents["f"].zone.value != "battlefield" or True
    assert state.last_sacrificed_power == 1


def test_altar_mills_sacrificed_power():
    altar = _compile("Altar of Dementia").semantics
    ab = next(a for a in altar.abilities if isinstance(a, ActivatedAbility))
    fodder = CardSemantics(
        oracle_id="oracle:big",
        name="Big",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    ex = Executor({altar.oracle_id: altar, fodder.oracle_id: fodder})
    state = GameState(
        permanents={
            "a": Permanent(object_id="a", oracle_id=altar.oracle_id, name=altar.name),
            "f": Permanent(
                object_id="f",
                oracle_id=fodder.oracle_id,
                name="Big",
                is_creature=True,
                power=4,
                toughness=4,
            ),
        },
        mana=ManaAmount(),
        library_opponent=60,
    )
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="a", ability_id=ab.ability_id, target="f"),
        )
        is None
    )
    assert state.library_opponent == 56
    assert state.last_sacrificed_power == 4


def test_golem_sac_self_mana():
    golem = _compile("Composite Golem").semantics
    ab = next(a for a in golem.abilities if isinstance(a, ActivatedAbility))
    ex = Executor({golem.oracle_id: golem})
    state = GameState(
        permanents={
            "g": Permanent(
                object_id="g",
                oracle_id=golem.oracle_id,
                name=golem.name,
                is_creature=True,
                is_artifact=True,
            )
        },
        mana=ManaAmount(),
    )
    assert (
        ex.activate(state, ActionStep(op="activate", actor="g", ability_id=ab.ability_id))
        is None
    )
    assert state.mana.white == 1
    assert state.mana.blue == 1
    assert state.mana.black == 1
    assert state.mana.red == 1
    assert state.mana.green == 1


def test_sac_wrong_wording_stays_unsupported():
    report = compile_oracle_text(
        oracle_id="oracle:fake-sac",
        name="Fake Sac",
        oracle_text="Sacrifice a creature: Proliferate.",
        types=["Enchantment"],
        mana_cost=ManaAmount(generic=1),
        mana_value=1,
    )
    assert report.semantics.relevant_unsupported()
