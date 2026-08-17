"""Bounded action-space explorer that emits LoopWitness candidates."""

from __future__ import annotations

from collections import deque

from pydantic import BaseModel

from mtg_loop_engine.corpus.builders import bf, two_card  # shared with gold fixtures
from mtg_loop_engine.interactions.capabilities import extract_capabilities
from mtg_loop_engine.proofs.models import (
    ActionStep,
    EssentialCardRef,
    InitialStateSpec,
    LoopProof,
    LoopRelevantState,
    LoopWitness,
    OutputDelta,
    Prerequisite,
    StateDimension,
)
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.search.pruning import reusable_fingerprint
from mtg_loop_engine.semantics.enums import (
    ComparisonOp,
    OutputType,
    VerificationStatus,
    Zone,
)
from mtg_loop_engine.semantics.ir import ActivatedAbility, CardSemantics, SacrificeCost
from mtg_loop_engine.state.game import GameState
from mtg_loop_engine.verify.verifier import Verifier


class ExploredWitness(BaseModel):
    """First sequence the injected verifier accepts for this pair.

    Explorer is the only verification call on the discovery path. `discover_loops`
    attaches join reasons; it does not verify again.
    """

    witness: LoopWitness
    proof: LoopProof


OUTPUT_EVENT_KEYS = {
    "mana": OutputType.MANA,
    "token": OutputType.TOKEN,
    "etb": OutputType.ETB,
    "untap": OutputType.UNTAP,
    "damage": OutputType.DAMAGE,
    "life_gain": OutputType.LIFE_GAIN,
    "life_loss": OutputType.LIFE_LOSS,
    "death": OutputType.DEATH,
    "sacrifice": OutputType.SACRIFICE,
}


def default_initial_state(a: CardSemantics, b: CardSemantics) -> InitialStateSpec:
    """Place both cards on the battlefield with generic fodder/counters as needed."""
    ordered = sorted([a, b], key=lambda c: c.oracle_id)
    permanents = []
    for i, card in enumerate(ordered):
        types = {t.lower() for t in card.types}
        caps = extract_capabilities(card)
        counters = {"p1p1": 1} if caps.removes_p1p1() else {}
        is_creature = "creature" in types
        permanents.append(
            bf(
                f"c{i}",
                card.oracle_id,
                card.name,
                is_creature=is_creature,
                is_artifact="artifact" in types,
                counters=counters,
                power=1 if is_creature else None,
                toughness=1 if is_creature else None,
            )
        )
    if any(extract_capabilities(c).needs_token_fodder() for c in ordered):
        permanents.append(
            bf(
                "seed",
                "token:seed",
                "Seed",
                is_creature=True,
                is_token=True,
                power=1,
                toughness=1,
            )
        )
    return InitialStateSpec(permanents=permanents)


def _try_apply(executor: Executor, state: GameState, step: ActionStep) -> GameState | None:
    nxt = state.copy()
    err = executor.run_step(nxt, step)
    return None if err else nxt


def _effect_needs_permanent_target(ability: ActivatedAbility) -> bool:
    for effect in ability.effects:
        if getattr(effect, "target", None) == "target_permanent":
            return True
    return False


def _sac_selector(ability: ActivatedAbility) -> str | None:
    for cost in ability.costs:
        if isinstance(cost, SacrificeCost) and cost.selector != "self":
            return cost.selector
    return None


def _fodder_ids(state: GameState, selector: str) -> list[str]:
    ids: list[str] = []
    for perm in state.permanents.values():
        if perm.zone != Zone.BATTLEFIELD or perm.controller != "you":
            continue
        if selector == "token_creature_controlled" and perm.is_token and perm.is_creature:
            ids.append(perm.object_id)
        elif selector == "creature_controlled" and perm.is_creature:
            ids.append(perm.object_id)
    return ids


def legal_steps(executor: Executor, state: GameState) -> list[ActionStep]:
    """Deterministic legal actions. Pending triggers are resolved before new activations."""
    steps: list[ActionStep] = []
    if state.pending_triggers:
        bf_ids = [
            p.object_id
            for p in state.permanents.values()
            if p.zone == Zone.BATTLEFIELD and p.controller == "you"
        ]
        tapped_first = sorted(
            bf_ids,
            key=lambda oid: (not state.permanents[oid].tapped, oid),
        )
        seen: set[tuple] = set()
        for trig in state.pending_triggers:
            base = ActionStep(
                op="resolve_trigger",
                actor=trig["source_id"],
                ability_id=trig["ability_id"],
            )
            ab = executor.find_ability(
                state.permanents[trig["source_id"]].oracle_id,
                trig["ability_id"],
            )
            needs_target = False
            if ab is not None:
                for effect in getattr(ab, "effects", []):
                    if getattr(effect, "target", None) == "target_permanent":
                        needs_target = True
            candidates = tapped_first if needs_target else [None]
            for target in candidates:
                step = base.model_copy(update={"target": target})
                key = (step.actor, step.ability_id, step.target)
                if key in seen:
                    continue
                if _try_apply(executor, state, step) is not None:
                    seen.add(key)
                    steps.append(step)
        return steps

    for perm in sorted(state.permanents.values(), key=lambda p: p.object_id):
        card = executor.semantics.get(perm.oracle_id)
        if not card:
            continue
        for ab in card.abilities:
            if not isinstance(ab, ActivatedAbility) or not ab.supported:
                continue
            selector = _sac_selector(ab)
            need_effect_target = _effect_needs_permanent_target(ab)
            if selector:
                targets = _fodder_ids(state, selector)
            elif need_effect_target:
                targets = [
                    p.object_id
                    for p in state.permanents.values()
                    if p.zone == Zone.BATTLEFIELD and p.controller == "you"
                ]
            else:
                targets = [None]
            for target in targets:
                step = ActionStep(
                    op="activate",
                    actor=perm.object_id,
                    ability_id=ab.ability_id,
                    target=target,
                )
                if _try_apply(executor, state, step) is not None:
                    steps.append(step)
    return steps


def derive_relevant_state(
    spec: InitialStateSpec, before: GameState
) -> LoopRelevantState:
    dims: list[StateDimension] = []
    for perm in spec.permanents:
        if perm.is_token:
            continue
        live = before.permanents.get(perm.object_id)
        if live is None:
            continue
        dims.append(
            StateDimension(
                path=f"permanents.{perm.object_id}.zone",
                op=ComparisonOp.EXACT,
                value=live.zone.value,
            )
        )
        dims.append(
            StateDimension(
                path=f"permanents.{perm.object_id}.tapped",
                op=ComparisonOp.EXACT,
                value=live.tapped,
            )
        )
        for ctype, qty in live.counters.items():
            dims.append(
                StateDimension(
                    path=f"permanents.{perm.object_id}.counters.{ctype}",
                    op=ComparisonOp.EXACT,
                    value=qty,
                )
            )
    if any(p.is_token for p in spec.permanents):
        dims.append(
            StateDimension(
                path="count.battlefield.creature_tokens",
                op=ComparisonOp.MINIMUM,
                value=before.get_path("count.battlefield.creature_tokens"),
            )
        )
    for color in ("white", "blue", "black", "red", "green", "colorless"):
        start = getattr(before.mana, color)
        dims.append(
            StateDimension(
                path=f"mana.{color}",
                op=ComparisonOp.MINIMUM,
                value=start,
            )
        )
    return LoopRelevantState(dimensions=dims)


def derive_outputs(before: GameState, after: GameState) -> list[OutputDelta]:
    outs: list[OutputDelta] = []
    for key, typ in OUTPUT_EVENT_KEYS.items():
        delta = after.event_counters.get(key, 0) - before.event_counters.get(key, 0)
        if delta > 0:
            outs.append(OutputDelta(type=typ, delta_per_iteration=delta))
    return outs


def build_witness(
    a: CardSemantics,
    b: CardSemantics,
    spec: InitialStateSpec,
    loop_actions: list[ActionStep],
    before: GameState,
    after: GameState,
) -> LoopWitness:
    generic: list[Prerequisite] = []
    if any(p.is_token for p in spec.permanents):
        generic.append(
            Prerequisite(
                kind="board",
                description="creature token fodder (identity irrelevant)",
            )
        )
    refs = [
        EssentialCardRef(oracle_id=a.oracle_id, name=a.name),
        EssentialCardRef(oracle_id=b.oracle_id, name=b.name),
    ]
    pair_id = "__".join(sorted([a.oracle_id, b.oracle_id]))
    return LoopWitness(
        id=f"discover_{pair_id}",
        classification=two_card(essential=refs, generic=generic),
        essential_cards=refs,
        card_semantics=[a, b],
        initial_state=spec,
        loop_actions=loop_actions,
        relevant_state=derive_relevant_state(spec, before),
        expected_outputs=derive_outputs(before, after),
        assumptions=["discovered_without_pair_labels"],
        prerequisites=generic,
    )


def explore_pair(
    a: CardSemantics,
    b: CardSemantics,
    *,
    max_depth: int = 6,
    max_states: int = 4000,
    verifier: Verifier | None = None,
) -> ExploredWitness | None:
    """Search one unordered pair. Returns the first verifier-accepted loop."""
    check = verifier or Verifier()
    spec = default_initial_state(a, b)
    semantics = {a.oracle_id: a, b.oracle_id: b}
    executor = Executor(semantics)
    start = GameState.from_spec(spec)
    queue: deque[tuple[GameState, list[ActionStep]]] = deque([(start, [])])
    expanded: set[tuple] = set()
    visited = 0

    while queue:
        state, actions = queue.popleft()
        visited += 1
        if visited > max_states:
            break
        # Check arrival before expansion pruning so returning to the start
        # fingerprint can still be recognized as a loop.
        if 1 <= len(actions) <= max_depth and not state.pending_triggers:
            outputs = derive_outputs(start, state)
            if outputs:
                witness = build_witness(a, b, spec, actions, start, state)
                proof = check.verify(witness)
                if proof.status == VerificationStatus.VERIFIED:
                    return ExploredWitness(witness=witness, proof=proof)
        if len(actions) >= max_depth:
            continue
        fp = reusable_fingerprint(state)
        if fp in expanded:
            continue
        expanded.add(fp)
        for step in legal_steps(executor, state):
            nxt = _try_apply(executor, state, step)
            if nxt is None:
                continue
            queue.append((nxt, [*actions, step]))
    return None
