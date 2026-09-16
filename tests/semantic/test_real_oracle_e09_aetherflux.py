"""M5 E09: Aetherflux cast-count life + pay-life damage."""

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, VerificationStatus, Zone
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    CardSemantics,
    ManaAmount,
    PayLifeCost,
    TriggeredAbility,
)
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM
from mtg_loop_engine.state.game import GameState, Permanent


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    mana_cost = _parse_mana_braces(row.mana_cost) if row.mana_cost else None
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=mana_cost,
        mana_value=row.mana_value,
    )


def test_e09_aetherflux_complete():
    report = _compile("Aetherflux Reservoir")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    abs_ = [a for a in report.semantics.abilities if isinstance(a, ActivatedAbility)]
    trigs = [a for a in report.semantics.abilities if isinstance(a, TriggeredAbility)]
    assert len(trigs) == 1
    assert trigs[0].effects[0].equal_to_spells_cast_this_turn
    assert len(abs_) == 1
    assert isinstance(abs_[0].costs[0], PayLifeCost)
    assert abs_[0].costs[0].amount == 50


def test_cast_gains_life_per_spell_count():
    flux = _compile("Aetherflux Reservoir").semantics
    rock = CardSemantics(
        oracle_id="oracle:rock",
        name="Mana Rock",
        types=["Artifact"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
        mana_cost=ManaAmount(generic=0),
        mana_value=0,
    )
    ex = Executor({flux.oracle_id: flux, rock.oracle_id: rock})
    state = GameState(
        permanents={
            "flux": Permanent(
                object_id="flux",
                oracle_id=flux.oracle_id,
                name=flux.name,
                is_artifact=True,
            ),
            "r1": Permanent(
                object_id="r1",
                oracle_id=rock.oracle_id,
                name=rock.name,
                zone=Zone.HAND,
                is_artifact=True,
            ),
            "r2": Permanent(
                object_id="r2",
                oracle_id=rock.oracle_id,
                name=rock.name,
                zone=Zone.HAND,
                is_artifact=True,
            ),
        },
        mana=ManaAmount(),
        life_you=20,
    )
    assert ex.cast_from_hand(state, ActionStep(op="cast_from_hand", actor="r1")) is None
    assert state.pending_triggers
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.life_you == 21  # 1st spell
    assert ex.cast_from_hand(state, ActionStep(op="cast_from_hand", actor="r2")) is None
    assert ex.resolve_trigger(state, ActionStep(op="resolve_trigger")) is None
    assert state.life_you == 23  # +2 for 2nd spell


def test_pay_life_damage_and_deficit():
    flux = _compile("Aetherflux Reservoir").semantics
    ab = next(a for a in flux.abilities if isinstance(a, ActivatedAbility))
    ex = Executor({flux.oracle_id: flux})
    state = GameState(
        permanents={
            "flux": Permanent(
                object_id="flux",
                oracle_id=flux.oracle_id,
                name=flux.name,
                is_artifact=True,
            )
        },
        mana=ManaAmount(),
        life_you=60,
        life_opponent=40,
    )
    assert (
        ex.activate(
            state,
            ActionStep(op="activate", actor="flux", ability_id=ab.ability_id),
        )
        is None
    )
    assert state.life_you == 10
    assert state.life_opponent == -10

    state2 = GameState(
        permanents={
            "flux": Permanent(
                object_id="flux",
                oracle_id=flux.oracle_id,
                name=flux.name,
                is_artifact=True,
            )
        },
        mana=ManaAmount(),
        life_you=49,
    )
    err = ex.activate(
        state2,
        ActionStep(op="activate", actor="flux", ability_id=ab.ability_id),
    )
    assert err is not None
    assert err.status == VerificationStatus.RESOURCE_DEFICIT


def test_pay_life_wrong_wording_stays_unsupported():
    report = compile_oracle_text(
        oracle_id="oracle:fake-pay",
        name="Fake Pay",
        oracle_text="Lose 50 life: This Artifact deals 50 damage to any target.",
        types=["Artifact"],
        mana_cost=ManaAmount(generic=4),
        mana_value=4,
    )
    assert report.semantics.relevant_unsupported()
