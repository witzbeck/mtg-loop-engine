"""Once-per-turn ability usage must be proof-relevant for recurrence."""

from mtg_loop_engine.corpus.gold_core.cases import INTRUDER_ALARM, ONCE_TAPPER, TOKEN_TAPPER
from mtg_loop_engine.proofs.models import (
    ActionStep,
    Classification,
    EssentialCardRef,
    InitialStateSpec,
    LoopRelevantState,
    LoopWitness,
    OutputDelta,
    PermanentSpec,
    StateDimension,
)
from mtg_loop_engine.search.explorer import derive_relevant_state, explore_pair
from mtg_loop_engine.semantics.enums import (
    ComparisonOp,
    LoopType,
    OutputType,
    VerificationStatus,
)
from mtg_loop_engine.semantics.ir import CardSemantics
from mtg_loop_engine.state.game import GameState
from mtg_loop_engine.verify.verifier import Verifier, check_recurrence


def test_get_path_once_per_turn_used_bool():
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="p",
                    oracle_id="oracle:once",
                    name="Once",
                    is_creature=True,
                )
            ]
        )
    )
    assert state.get_path("permanents.p.once_per_turn_used.tap-make-token") is False
    state.permanents["p"].once_per_turn_used.add("tap-make-token")
    assert state.get_path("permanents.p.once_per_turn_used.tap-make-token") is True


def test_recurrence_fails_when_once_per_turn_becomes_used():
    before = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="p_tapper",
                    oracle_id=ONCE_TAPPER.oracle_id,
                    name=ONCE_TAPPER.name,
                    is_creature=True,
                )
            ]
        )
    )
    after = before.copy()
    after.permanents["p_tapper"].once_per_turn_used.add("tap-make-token")
    witness = LoopWitness(
        id="once-recurrence",
        classification=Classification(
            essential_card_count=2,
            strict_two_card=True,
            loop_type=LoopType.ARBITRARY_REPEATABLE,
        ),
        essential_cards=[
            EssentialCardRef(oracle_id="a", name="A"),
            EssentialCardRef(oracle_id="b", name="B"),
        ],
        card_semantics=[
            CardSemantics(oracle_id="a", name="A"),
            CardSemantics(oracle_id="b", name="B"),
        ],
        initial_state=InitialStateSpec(),
        loop_actions=[ActionStep(op="noop")],
        relevant_state=LoopRelevantState(
            dimensions=[
                StateDimension(
                    path="permanents.p_tapper.once_per_turn_used.tap-make-token",
                    op=ComparisonOp.EXACT,
                    value=False,
                )
            ]
        ),
    )
    result = check_recurrence(before, after, witness)
    assert not result.ok


def test_derive_relevant_state_tracks_once_per_turn_ability():
    spec = InitialStateSpec(
        permanents=[
            PermanentSpec(
                object_id="p_alarm",
                oracle_id=INTRUDER_ALARM.oracle_id,
                name=INTRUDER_ALARM.name,
            ),
            PermanentSpec(
                object_id="p_tapper",
                oracle_id=ONCE_TAPPER.oracle_id,
                name=ONCE_TAPPER.name,
                is_creature=True,
            ),
        ]
    )
    before = GameState.from_spec(spec)
    dims = derive_relevant_state(
        spec,
        before,
        loop_actions=[
            ActionStep(
                op="activate",
                actor="p_tapper",
                ability_id="tap-make-token",
            )
        ],
        cards=[INTRUDER_ALARM, ONCE_TAPPER],
    )
    paths = {d.path: d for d in dims.dimensions}
    key = "permanents.p_tapper.once_per_turn_used.tap-make-token"
    assert key in paths
    assert paths[key].op == ComparisonOp.EXACT
    assert paths[key].value is False


def test_alarm_plus_once_tapper_not_discovered():
    found = explore_pair(INTRUDER_ALARM, ONCE_TAPPER)
    assert found is None


def test_alarm_plus_repeatable_tapper_still_discovered():
    found = explore_pair(INTRUDER_ALARM, TOKEN_TAPPER)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED


def test_hand_authored_once_loop_rejects_on_recurrence():
    """Adversarial witness that activates once-per-turn; recurrence must fail."""
    witness = LoopWitness(
        id="adv_once_recurrence",
        classification=Classification(
            essential_card_count=2,
            strict_two_card=True,
            loop_type=LoopType.ARBITRARY_REPEATABLE,
        ),
        essential_cards=[
            EssentialCardRef(
                oracle_id=INTRUDER_ALARM.oracle_id, name=INTRUDER_ALARM.name
            ),
            EssentialCardRef(oracle_id=ONCE_TAPPER.oracle_id, name=ONCE_TAPPER.name),
        ],
        card_semantics=[INTRUDER_ALARM, ONCE_TAPPER],
        initial_state=InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="p_alarm",
                    oracle_id=INTRUDER_ALARM.oracle_id,
                    name=INTRUDER_ALARM.name,
                ),
                PermanentSpec(
                    object_id="p_tapper",
                    oracle_id=ONCE_TAPPER.oracle_id,
                    name=ONCE_TAPPER.name,
                    is_creature=True,
                    power=1,
                    toughness=1,
                ),
            ]
        ),
        loop_actions=[
            ActionStep(op="activate", actor="p_tapper", ability_id="tap-make-token"),
            ActionStep(
                op="resolve_trigger",
                actor="p_alarm",
                ability_id="alarm-untap",
                target="p_tapper",
            ),
        ],
        relevant_state=LoopRelevantState(
            dimensions=[
                StateDimension(
                    path="permanents.p_tapper.tapped",
                    op=ComparisonOp.EXACT,
                    value=False,
                ),
                StateDimension(
                    path="permanents.p_tapper.once_per_turn_used.tap-make-token",
                    op=ComparisonOp.EXACT,
                    value=False,
                ),
            ]
        ),
        expected_outputs=[OutputDelta(type=OutputType.TOKEN, delta_per_iteration=1)],
    )
    proof = Verifier().verify(witness)
    assert proof.status == VerificationStatus.STATE_NOT_RECURRENT


def test_omitting_once_per_turn_dim_still_rejects():
    """ADR 0008: verifier injects once-per-turn dims even when the witness omits them."""
    witness = LoopWitness(
        id="adv_once_omit_dim",
        classification=Classification(
            essential_card_count=2,
            strict_two_card=True,
            loop_type=LoopType.ARBITRARY_REPEATABLE,
        ),
        essential_cards=[
            EssentialCardRef(
                oracle_id=INTRUDER_ALARM.oracle_id, name=INTRUDER_ALARM.name
            ),
            EssentialCardRef(oracle_id=ONCE_TAPPER.oracle_id, name=ONCE_TAPPER.name),
        ],
        card_semantics=[INTRUDER_ALARM, ONCE_TAPPER],
        initial_state=InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="p_alarm",
                    oracle_id=INTRUDER_ALARM.oracle_id,
                    name=INTRUDER_ALARM.name,
                ),
                PermanentSpec(
                    object_id="p_tapper",
                    oracle_id=ONCE_TAPPER.oracle_id,
                    name=ONCE_TAPPER.name,
                    is_creature=True,
                    power=1,
                    toughness=1,
                ),
            ]
        ),
        loop_actions=[
            ActionStep(op="activate", actor="p_tapper", ability_id="tap-make-token"),
            ActionStep(
                op="resolve_trigger",
                actor="p_alarm",
                ability_id="alarm-untap",
                target="p_tapper",
            ),
        ],
        # Deliberately omit once_per_turn_used — only tap recurrence declared.
        relevant_state=LoopRelevantState(
            dimensions=[
                StateDimension(
                    path="permanents.p_tapper.tapped",
                    op=ComparisonOp.EXACT,
                    value=False,
                ),
            ]
        ),
        expected_outputs=[OutputDelta(type=OutputType.TOKEN, delta_per_iteration=1)],
    )
    proof = Verifier().verify(witness)
    assert proof.status == VerificationStatus.STATE_NOT_RECURRENT
    assert any("once_per_turn_used" in d for d in proof.recurrence.details)


def test_omitting_pending_trigger_count_still_rejects():
    """Leaving a trigger pending must fail recurrence via mandatory pending_triggers.count."""
    witness = LoopWitness(
        id="adv_pending_omit",
        classification=Classification(
            essential_card_count=2,
            strict_two_card=True,
            loop_type=LoopType.ARBITRARY_REPEATABLE,
        ),
        essential_cards=[
            EssentialCardRef(
                oracle_id=INTRUDER_ALARM.oracle_id, name=INTRUDER_ALARM.name
            ),
            EssentialCardRef(oracle_id=TOKEN_TAPPER.oracle_id, name=TOKEN_TAPPER.name),
        ],
        card_semantics=[INTRUDER_ALARM, TOKEN_TAPPER],
        initial_state=InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="p_alarm",
                    oracle_id=INTRUDER_ALARM.oracle_id,
                    name=INTRUDER_ALARM.name,
                ),
                PermanentSpec(
                    object_id="p_tapper",
                    oracle_id=TOKEN_TAPPER.oracle_id,
                    name=TOKEN_TAPPER.name,
                    is_creature=True,
                    power=1,
                    toughness=1,
                ),
            ]
        ),
        # Activate only — ETB trigger stays pending; no resolve_trigger.
        loop_actions=[
            ActionStep(op="activate", actor="p_tapper", ability_id="tap-make-token"),
        ],
        relevant_state=LoopRelevantState(
            dimensions=[
                StateDimension(
                    path="permanents.p_tapper.tapped",
                    op=ComparisonOp.EXACT,
                    value=True,
                ),
            ]
        ),
        expected_outputs=[OutputDelta(type=OutputType.TOKEN, delta_per_iteration=1)],
    )
    proof = Verifier().verify(witness)
    assert proof.status == VerificationStatus.STATE_NOT_RECURRENT
    assert any("pending_triggers.count" in d for d in proof.recurrence.details)
