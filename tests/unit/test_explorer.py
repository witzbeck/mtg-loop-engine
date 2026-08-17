"""Explorer primitives: default board, legal steps, fingerprints, injected verifier."""

from mtg_loop_engine.corpus.gold_core.cases import (
    BASALT,
    INTRUDER_ALARM,
    TOKEN_TAPPER,
    TRAINING_GROUNDS,
)
from mtg_loop_engine.proofs.models import LoopProof
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.search.discover import discover_loops
from mtg_loop_engine.search.explorer import default_initial_state, explore_pair, legal_steps
from mtg_loop_engine.search.pruning import reusable_fingerprint
from mtg_loop_engine.semantics.enums import VerificationStatus, Zone
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    AddManaEffect,
    CardSemantics,
    ManaAmount,
    RemoveCounterEffect,
    SacrificeCost,
    TapCost,
)
from mtg_loop_engine.state.game import GameState, Permanent
from mtg_loop_engine.verify.verifier import Verifier


def _partner() -> CardSemantics:
    return CardSemantics(oracle_id="u:partner", name="Partner", types=["Enchantment"])


class _RejectAll(Verifier):
    def verify(self, witness):
        proof = super().verify(witness)
        return proof.model_copy(update={"status": VerificationStatus.RESOURCE_DEFICIT})


class _SpyVerifier(Verifier):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[object] = []

    def verify(self, witness):
        self.calls.append(witness)
        return super().verify(witness)


def test_default_state_seeds_token_fodder_when_required():
    outlet = CardSemantics(
        oracle_id="u:outlet",
        name="Outlet",
        types=["Artifact"],
        abilities=[
            ActivatedAbility(
                ability_id="sac",
                costs=[SacrificeCost(selector="token_creature_controlled")],
                effects=[AddManaEffect(amount=ManaAmount(black=1))],
            )
        ],
    )
    spec = default_initial_state(outlet, _partner())
    seeds = [p for p in spec.permanents if p.is_token]
    assert len(seeds) == 1
    assert seeds[0].object_id == "seed"
    assert seeds[0].is_creature


def test_default_state_seeds_p1p1_when_counters_are_spent():
    gun = CardSemantics(
        oracle_id="u:gun",
        name="Gun",
        types=["Artifact"],
        abilities=[
            ActivatedAbility(
                ability_id="shot",
                costs=[],
                effects=[RemoveCounterEffect(counter_type="p1p1", quantity=1)],
            )
        ],
    )
    spec = default_initial_state(gun, _partner())
    gun_perm = next(p for p in spec.permanents if p.oracle_id == "u:gun")
    assert gun_perm.counters.get("p1p1") == 1
    partner = next(p for p in spec.permanents if p.oracle_id == "u:partner")
    assert partner.counters == {}


def test_legal_steps_resolve_pending_triggers_before_activations():
    spec = default_initial_state(TOKEN_TAPPER, INTRUDER_ALARM)
    semantics = {
        TOKEN_TAPPER.oracle_id: TOKEN_TAPPER,
        INTRUDER_ALARM.oracle_id: INTRUDER_ALARM,
    }
    executor = Executor(semantics)
    state = GameState.from_spec(spec)
    activations = legal_steps(executor, state)
    assert activations
    assert all(step.op == "activate" for step in activations)
    assert any(step.ability_id == "tap-make-token" for step in activations)

    alarm_id = next(
        p.object_id for p in spec.permanents if p.oracle_id == INTRUDER_ALARM.oracle_id
    )
    state.pending_triggers = [{"source_id": alarm_id, "ability_id": "alarm-untap"}]
    pending = legal_steps(executor, state)
    assert pending
    assert all(step.op == "resolve_trigger" for step in pending)
    assert all(step.ability_id == "alarm-untap" for step in pending)


def test_reusable_fingerprint_ignores_event_counters_not_board():
    spec = default_initial_state(BASALT, TRAINING_GROUNDS)
    a = GameState.from_spec(spec)
    b = a.copy()
    b.event_counters["mana"] = 99
    assert reusable_fingerprint(a) == reusable_fingerprint(b)

    tapped = a.copy()
    basalt_id = next(
        oid for oid, perm in tapped.permanents.items() if perm.oracle_id == BASALT.oracle_id
    )
    tapped.permanents[basalt_id].tapped = True
    assert reusable_fingerprint(a) != reusable_fingerprint(tapped)

    tokened = a.copy()
    tokened.permanents["seed"] = Permanent(
        object_id="seed",
        oracle_id="token:seed",
        name="Seed",
        is_token=True,
        is_creature=True,
        zone=Zone.BATTLEFIELD,
    )
    assert reusable_fingerprint(a) != reusable_fingerprint(tokened)


def test_injected_verifier_is_the_acceptance_oracle():
    report = discover_loops([BASALT, TRAINING_GROUNDS], verifier=_RejectAll())
    assert report.candidate_pairs >= 1
    assert report.searched_pairs >= 1
    assert report.verified == []
    found = explore_pair(BASALT, TRAINING_GROUNDS, verifier=_RejectAll())
    assert found is None


def test_discover_does_not_verify_an_accepted_witness_twice():
    spy = _SpyVerifier()
    report = discover_loops([BASALT, TRAINING_GROUNDS], verifier=spy)
    assert len(report.verified) == 1
    winning = report.verified[0].witness
    assert isinstance(report.verified[0].proof, LoopProof)
    assert report.verified[0].proof.status == VerificationStatus.VERIFIED
    assert sum(1 for seen in spy.calls if seen is winning) == 1
    assert spy.calls, "injected verifier must be used during search"
