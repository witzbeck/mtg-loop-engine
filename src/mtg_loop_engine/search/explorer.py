"""Bounded action-space explorer that emits LoopWitness candidates."""

from __future__ import annotations

from collections import deque

from pydantic import BaseModel

from mtg_loop_engine.corpus.builders import bf, two_card  # shared with gold fixtures
from mtg_loop_engine.eval.classify import analyze_prerequisites
from mtg_loop_engine.interactions.capabilities import extract_capabilities
from mtg_loop_engine.proofs.models import (
    ActionStep,
    Classification,
    EssentialCardRef,
    InitialStateSpec,
    LoopProof,
    LoopRelevantState,
    LoopWitness,
    NetStateDelta,
    OutputDelta,
    Prerequisite,
    StateDimension,
)
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.search.pruning import reusable_fingerprint
from mtg_loop_engine.semantics.enums import (
    ComparisonOp,
    Consequence,
    OutputType,
    Provenance,
    SemanticCoverage,
    TriggerEvent,
    VerificationStatus,
    Zone,
)
from mtg_loop_engine.semantics.provenance import provenance_of
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    AddCounterEffect,
    CardSemantics,
    DealDamageEffect,
    GrantLifelinkEffect,
    ManaAmount,
    ManaCost,
    SacrificeCost,
    TapCost,
    TriggeredAbility,
)
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES
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
    "mill": OutputType.MILL,
    "death": OutputType.DEATH,
    "sacrifice": OutputType.SACRIFICE,
    "draw": OutputType.DRAW,
}


ZOMBIE_SEED_ORACLE_ID = "token:zombie-seed"
# Setup permanent for host-tap auras (Presence of Gond class). Not a loop-created
# token: must appear in LoopRelevantState so host tapped EXACT is checked.
AURA_HOST_OBJECT_ID = "aura-host"
AURA_HOST_ORACLE_ID = "setup:aura-host"


def _needs_zombie_gate(card: CardSemantics) -> bool:
    return any(
        isinstance(ab, ActivatedAbility) and ab.requires_zombie for ab in card.abilities
    )


def _needs_tap_host(card: CardSemantics) -> bool:
    return any(
        isinstance(ab, ActivatedAbility)
        and any(isinstance(c, TapCost) and not c.source_self for c in ab.costs)
        for ab in card.abilities
    )


def _grant_lifelink_ability(card: CardSemantics) -> ActivatedAbility | None:
    for ab in card.abilities:
        if isinstance(ab, ActivatedAbility) and any(
            isinstance(e, GrantLifelinkEffect) for e in ab.effects
        ):
            return ab
    return None


def _mana_for_grant_lifelink(card: CardSemantics) -> ManaAmount | None:
    """Seed pool for one paid grant-lifelink activate ({1}{W} class).

    Generic cost is seeded as colorless so ``pay_mana`` can spend it (Path b
    style mana prerequisite — not a free grant op).
    """
    ab = _grant_lifelink_ability(card)
    if ab is None:
        return None
    for cost in ab.costs:
        if isinstance(cost, ManaCost):
            need = cost.amount
            return ManaAmount(
                white=need.white,
                blue=need.blue,
                black=need.black,
                red=need.red,
                green=need.green,
                colorless=need.colorless + need.generic,
                any_color=need.any_color,
            )
    return None


def default_initial_state(a: CardSemantics, b: CardSemantics) -> InitialStateSpec:
    """Place both cards on the battlefield with generic fodder/counters as needed."""
    ordered = sorted([a, b], key=lambda c: c.oracle_id)
    permanents = []
    for i, card in enumerate(ordered):
        types = {t.lower() for t in card.types}
        caps = extract_capabilities(card)
        is_creature = "creature" in types
        fix = GOLD_ORACLE_FIXTURES.get(card.oracle_id)
        if (
            is_creature
            and fix is not None
            and fix.power is not None
            and fix.toughness is not None
        ):
            power, toughness = fix.power, fix.toughness
        else:
            power = 1 if is_creature else None
            toughness = 1 if is_creature else None
        # Counter-mana engines need enough p1p1 to pay Staff-class untap:
        # {3} untap creature + {1} untap Staff in the same cycle.
        if caps.needs_p1p1_mana_seed():
            counters = {"p1p1": 4}
        elif caps.removes_p1p1():
            # 0/0 counter-removers need ≥2 so one ping leaves a legal creature (SBA).
            counters = {"p1p1": 2 if toughness == 0 else 1}
        else:
            counters = {}
        permanents.append(
            bf(
                f"c{i}",
                card.oracle_id,
                card.name,
                is_creature=is_creature,
                is_artifact="artifact" in types,
                counters=counters,
                power=power,
                toughness=toughness,
            )
        )
    need_token = any(extract_capabilities(c).needs_token_fodder() for c in ordered)
    need_zombie = any(_needs_zombie_gate(c) for c in ordered)
    need_tap_host = any(_needs_tap_host(c) for c in ordered)
    has_creature = any(p.is_creature for p in permanents)
    # One generic Zombie token covers cast-from-GY gates and sac fodder when both apply.
    if need_zombie:
        permanents.append(
            bf(
                "seed",
                ZOMBIE_SEED_ORACLE_ID,
                "Zombie",
                is_creature=True,
                is_token=True,
                power=1,
                toughness=1,
            )
        )
    elif need_token:
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
    # Presence of Gond class: tap a host creature (prefer partner; else seed).
    # Seed as a non-token setup permanent so derive_relevant_state tracks tapped.
    if need_tap_host and not has_creature:
        permanents.append(
            bf(
                AURA_HOST_OBJECT_ID,
                AURA_HOST_ORACLE_ID,
                "Aura Host",
                is_creature=True,
                is_token=False,
                power=1,
                toughness=1,
            )
        )
    mana = ManaAmount()
    for card in ordered:
        seed = _mana_for_grant_lifelink(card)
        if seed is None:
            continue
        mana = ManaAmount(
            white=mana.white + seed.white,
            blue=mana.blue + seed.blue,
            black=mana.black + seed.black,
            red=mana.red + seed.red,
            green=mana.green + seed.green,
            colorless=mana.colorless + seed.colorless,
            any_color=mana.any_color + seed.any_color,
        )
    return InitialStateSpec(permanents=permanents, mana=mana)


def _try_apply(executor: Executor, state: GameState, step: ActionStep) -> GameState | None:
    nxt = state.copy()
    err = executor.run_step(nxt, step)
    return None if err else nxt


def _effect_needs_permanent_target(ability: ActivatedAbility) -> bool:
    for effect in ability.effects:
        if getattr(effect, "target", None) in {
            "target_permanent",
            "target_other_creature",
        }:
            return True
    return False


def _any_target_damage(ability: ActivatedAbility) -> bool:
    return any(
        isinstance(e, DealDamageEffect) and e.target == "any_target"
        for e in ability.effects
    )


def _tap_cost_needs_host(ability: ActivatedAbility) -> bool:
    return any(isinstance(c, TapCost) and not c.source_self for c in ability.costs)

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
            exclude_source = False
            if ab is not None:
                for effect in getattr(ab, "effects", []):
                    tgt = getattr(effect, "target", None)
                    if tgt in {"target_permanent", "target_other_creature"}:
                        needs_target = True
                    if tgt == "target_other_creature":
                        exclude_source = True
            if needs_target:
                candidates = [
                    oid
                    for oid in tapped_first
                    if not exclude_source or oid != trig["source_id"]
                ]
                if exclude_source:
                    candidates = [
                        oid
                        for oid in candidates
                        if state.permanents[oid].is_creature
                    ]
            else:
                candidates = [None]
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
            need_tap_host = _tap_cost_needs_host(ab)
            any_target_dmg = _any_target_damage(ab)
            if selector:
                targets = _fodder_ids(state, selector)
            elif need_tap_host:
                targets = [
                    p.object_id
                    for p in state.permanents.values()
                    if p.zone == Zone.BATTLEFIELD
                    and p.controller == "you"
                    and p.is_creature
                    and not p.tapped
                    and p.object_id != perm.object_id
                ]
            elif any_target_dmg:
                # Opponent first (Heliod/Ballista); self legal for undying self-ping.
                targets = ["opponent", perm.object_id]
            elif need_effect_target:
                exclude_source = any(
                    getattr(e, "target", None) == "target_other_creature"
                    for e in ab.effects
                )
                targets = [
                    p.object_id
                    for p in state.permanents.values()
                    if p.zone == Zone.BATTLEFIELD
                    and p.controller == "you"
                    and (not exclude_source or p.object_id != perm.object_id)
                    and (
                        not exclude_source
                        or p.is_creature
                    )
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
    spec: InitialStateSpec,
    before: GameState,
    *,
    loop_actions: list[ActionStep] | None = None,
    cards: list[CardSemantics] | None = None,
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
            # Accumulating +1/+1 loops (Rosie/Scurry) need MINIMUM; reload loops
            # that return to the same count still satisfy MINIMUM.
            op = (
                ComparisonOp.MINIMUM
                if ctype in {"p1p1", "+1/+1"}
                else ComparisonOp.EXACT
            )
            dims.append(
                StateDimension(
                    path=f"permanents.{perm.object_id}.counters.{ctype}",
                    op=op,
                    value=qty,
                )
            )
    # Once-per-turn + pending-trigger dims: shared with verifier (ADR 0008).
    from mtg_loop_engine.verify.mandatory_recurrence import (
        once_per_turn_dimensions,
        pending_trigger_dimensions,
    )

    if loop_actions and cards:
        dims.extend(
            once_per_turn_dimensions(
                loop_actions=loop_actions, cards=cards, before=before
            )
        )
    dims.extend(pending_trigger_dimensions(before))
    if any(p.is_token for p in spec.permanents):
        dims.append(
            StateDimension(
                path="count.battlefield.creature_tokens",
                op=ComparisonOp.MINIMUM,
                value=before.get_path("count.battlefield.creature_tokens"),
            )
        )
    for color in (
        "white",
        "blue",
        "black",
        "red",
        "green",
        "colorless",
        "any_color",
    ):
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


def _needs_life_gain_seed(card: CardSemantics) -> bool:
    """Path-b life-drain seed (Bond/Blood), not Heliod counter-on-gain."""
    from mtg_loop_engine.semantics.ir import LoseLifeEffect

    return any(
        isinstance(ab, TriggeredAbility)
        and ab.event == TriggerEvent.GAIN_LIFE
        and any(isinstance(e, LoseLifeEffect) for e in ab.effects)
        for ab in card.abilities
    )


def _needs_opponent_lose_life_seed(card: CardSemantics) -> bool:
    """Path-b mill feedback seed (Mindcrank / Bloodchief class)."""
    from mtg_loop_engine.semantics.ir import MillEffect

    return any(
        isinstance(ab, TriggeredAbility)
        and ab.event == TriggerEvent.OPPONENT_LOSE_LIFE
        and any(isinstance(e, MillEffect) for e in ab.effects)
        for ab in card.abilities
    )


def _needs_token_create_seed(card: CardSemantics) -> bool:
    return any(
        isinstance(ab, TriggeredAbility) and ab.event == TriggerEvent.CREATE_TOKEN
        for ab in card.abilities
    )


def _needs_lifelink_grant_seed(card: CardSemantics) -> bool:
    """Heliod-class: GAIN_LIFE → counter, partner removes counters for damage."""
    return any(
        isinstance(ab, TriggeredAbility)
        and ab.event == TriggerEvent.GAIN_LIFE
        and any(isinstance(e, AddCounterEffect) for e in ab.effects)
        for ab in card.abilities
    )


def build_witness(
    a: CardSemantics,
    b: CardSemantics,
    spec: InitialStateSpec,
    loop_actions: list[ActionStep],
    before: GameState,
    after: GameState,
    *,
    setup_actions: list[ActionStep] | None = None,
) -> LoopWitness:
    generic: list[Prerequisite] = []
    if any(p.is_token for p in spec.permanents):
        generic.append(
            Prerequisite(
                kind="board",
                description="creature token fodder (identity irrelevant)",
            )
        )
    if any(p.object_id == AURA_HOST_OBJECT_ID for p in spec.permanents):
        generic.append(
            Prerequisite(
                kind="board",
                description="generic creature host for aura tap cost (identity irrelevant)",
            )
        )
    setup = setup_actions or []
    if any(s.op == "seed_gain_life" for s in setup):
        generic.append(
            Prerequisite(
                kind="board",
                description=(
                    "generic life-gain seed to start GAIN_LIFE triggers "
                    "(identity irrelevant)"
                ),
            )
        )
    if any(s.op == "seed_lose_life" for s in setup):
        generic.append(
            Prerequisite(
                kind="board",
                description=(
                    "generic opponent life-loss seed to start OPPONENT_LOSE_LIFE "
                    "triggers (identity irrelevant)"
                ),
            )
        )
    if any(s.op == "seed_create_token" for s in setup):
        generic.append(
            Prerequisite(
                kind="board",
                description=(
                    "generic token-create seed to start CREATE_TOKEN triggers "
                    "(Food identity irrelevant)"
                ),
            )
        )
    if any(s.op == "seed_grant_lifelink" for s in setup):
        generic.append(
            Prerequisite(
                kind="board",
                description=(
                    "physics lifelink grant seed (not product-legal for ORACLE_EXACT; "
                    "identity of grant source irrelevant once lifelink is on the pinger)"
                ),
            )
        )
    grant_ability_ids = {
        ab.ability_id
        for card in (a, b)
        if (ab := _grant_lifelink_ability(card)) is not None
    }
    if any(
        s.op == "activate" and s.ability_id in grant_ability_ids for s in setup
    ):
        generic.append(
            Prerequisite(
                kind="board",
                description=(
                    "generic mana for one paid grant-lifelink activation "
                    "(Path b; identity of mana source irrelevant)"
                ),
            )
        )
    refs = [
        EssentialCardRef(oracle_id=a.oracle_id, name=a.name),
        EssentialCardRef(oracle_id=b.oracle_id, name=b.name),
    ]
    pair_id = "__".join(sorted([a.oracle_id, b.oracle_id]))
    witness = LoopWitness(
        id=f"discover_{pair_id}",
        classification=two_card(essential=refs, generic=generic),
        essential_cards=refs,
        card_semantics=[a, b],
        initial_state=spec,
        setup_actions=setup,
        loop_actions=loop_actions,
        relevant_state=derive_relevant_state(
            spec, before, loop_actions=loop_actions, cards=[a, b]
        ),
        expected_outputs=derive_outputs(before, after),
        assumptions=["discovered_without_pair_labels"],
        prerequisites=generic,
    )
    analysis = analyze_prerequisites(witness)
    functional = [
        Prerequisite(kind="functional", description=item)
        for item in analysis.functional_external_requirements
    ]
    generic_prereqs = [
        Prerequisite(kind="board", description=item)
        for item in analysis.generic_prerequisites
    ] or generic
    witness.classification = Classification(
        essential_card_count=max(analysis.essential_functional_count, 1),
        strict_two_card=analysis.strict_two_card,
        generic_prerequisites=generic_prereqs,
        functional_external_requirements=functional,
    )
    witness.prerequisites = generic_prereqs + functional
    witness.assumptions = ["discovered_without_pair_labels"] + [
        f"{item.kind.value}: {item.description}" for item in analysis.assumptions
    ]
    return witness


def explore_pair(
    a: CardSemantics,
    b: CardSemantics,
    *,
    max_depth: int = 6,
    max_states: int = 4000,
    verifier: Verifier | None = None,
    expected_net_state: NetStateDelta | None = None,
    expected_claim_consequence: Consequence | None = None,
) -> ExploredWitness | None:
    """Search one unordered pair.

    Returns the first verifier-accepted loop where both searched essentials
    participate (`strict_two_card`). Bystander-verified sequences are skipped
    silently so BFS can continue; if none qualify, returns ``None``.

    When ``expected_net_state`` / ``expected_claim_consequence`` are set, stamp
    them on candidate witnesses before verify so shallow gross-only loops can
    be skipped in favor of the claimed net benefit (gold promotion).
    """
    check = verifier or Verifier()
    spec = default_initial_state(a, b)
    semantics = {a.oracle_id: a, b.oracle_id: b}
    if any(p.oracle_id == ZOMBIE_SEED_ORACLE_ID for p in spec.permanents):
        semantics[ZOMBIE_SEED_ORACLE_ID] = CardSemantics(
            oracle_id=ZOMBIE_SEED_ORACLE_ID,
            name="Zombie",
            types=["Creature", "Zombie"],
            abilities=[],
            coverage=SemanticCoverage.COMPLETE,
        )
    executor = Executor(semantics)
    start = GameState.from_spec(spec)
    setup_actions: list[ActionStep] = []
    if _needs_life_gain_seed(a) or _needs_life_gain_seed(b):
        seed_actor = None
        for perm in sorted(start.permanents.values(), key=lambda p: p.object_id):
            card = semantics.get(perm.oracle_id)
            if card is not None and _needs_life_gain_seed(card):
                seed_actor = perm.object_id
                break
        if seed_actor is not None:
            seed = ActionStep(
                op="seed_gain_life",
                actor=seed_actor,
                note="generic life-gain seed (Path b)",
            )
            err = executor.run_step(start, seed)
            if err is None:
                setup_actions = [seed]
    if _needs_opponent_lose_life_seed(a) or _needs_opponent_lose_life_seed(b):
        seed_actor = None
        for perm in sorted(start.permanents.values(), key=lambda p: p.object_id):
            card = semantics.get(perm.oracle_id)
            if card is not None and _needs_opponent_lose_life_seed(card):
                seed_actor = perm.object_id
                break
        if seed_actor is not None:
            seed = ActionStep(
                op="seed_lose_life",
                actor=seed_actor,
                note="generic opponent life-loss seed (Path b)",
            )
            err = executor.run_step(start, seed)
            if err is None:
                setup_actions = [*setup_actions, seed]
    if _needs_token_create_seed(a) or _needs_token_create_seed(b):
        seed_actor = None
        for perm in sorted(start.permanents.values(), key=lambda p: p.object_id):
            card = semantics.get(perm.oracle_id)
            if card is not None and _needs_token_create_seed(card):
                seed_actor = perm.object_id
                break
        if seed_actor is not None:
            seed = ActionStep(
                op="seed_create_token",
                actor=seed_actor,
                note="generic token-create seed (Rosie class)",
            )
            err = executor.run_step(start, seed)
            if err is None:
                setup_actions = [*setup_actions, seed]
    # seed_grant_lifelink is a physics stand-in only. Never emit on ORACLE_EXACT
    # product pairs (Heliod requires a paid {1}{W} activation for product VERIFIED).
    both_oracle_exact = (
        provenance_of(a.oracle_id) is Provenance.ORACLE_EXACT
        and provenance_of(b.oracle_id) is Provenance.ORACLE_EXACT
    )
    if (
        not both_oracle_exact
        and (_needs_lifelink_grant_seed(a) or _needs_lifelink_grant_seed(b))
        and _grant_lifelink_ability(a) is None
        and _grant_lifelink_ability(b) is None
    ):
        # Grant lifelink to a partner that can remove counters for damage.
        grantor = None
        pinger = None
        for perm in sorted(start.permanents.values(), key=lambda p: p.object_id):
            card = semantics.get(perm.oracle_id)
            if card is None:
                continue
            if _needs_lifelink_grant_seed(card):
                grantor = perm.object_id
            caps = extract_capabilities(card)
            if caps.removes_p1p1() and perm.is_creature:
                pinger = perm.object_id
        if grantor is not None and pinger is not None and grantor != pinger:
            seed = ActionStep(
                op="seed_grant_lifelink",
                actor=grantor,
                target=pinger,
                note="physics lifelink grant seed (non-product path)",
            )
            err = executor.run_step(start, seed)
            if err is None:
                setup_actions = [*setup_actions, seed]
    # Paid Heliod-class grant: activate once in setup targeting the counter-pinger.
    grant_card = a if _grant_lifelink_ability(a) is not None else (
        b if _grant_lifelink_ability(b) is not None else None
    )
    if grant_card is not None:
        grant_ab = _grant_lifelink_ability(grant_card)
        grantor = None
        pinger = None
        for perm in sorted(start.permanents.values(), key=lambda p: p.object_id):
            card = semantics.get(perm.oracle_id)
            if card is None:
                continue
            if card.oracle_id == grant_card.oracle_id:
                grantor = perm.object_id
            caps = extract_capabilities(card)
            if caps.removes_p1p1() and perm.is_creature:
                pinger = perm.object_id
        if (
            grant_ab is not None
            and grantor is not None
            and pinger is not None
            and grantor != pinger
        ):
            step = ActionStep(
                op="activate",
                actor=grantor,
                ability_id=grant_ab.ability_id,
                target=pinger,
                note="paid lifelink grant setup (Path b mana prerequisite)",
            )
            err = executor.run_step(start, step)
            if err is None:
                setup_actions = [*setup_actions, step]
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
        # Empty pending: classic closed loop. Same trigger ability/source/amount
        # as post-seed start: Path-b life-drain feedback (subject_id may change).
        if 1 <= len(actions) <= max_depth:
            def _trigger_close_key(st: GameState) -> tuple:
                return tuple(
                    (
                        t.get("ability_id"),
                        t.get("source_id"),
                        t.get("amount"),
                    )
                    for t in st.pending_triggers
                )

            can_close = (not state.pending_triggers) or (
                bool(start.pending_triggers)
                and _trigger_close_key(state) == _trigger_close_key(start)
            )
            if can_close:
                outputs = derive_outputs(start, state)
                if outputs:
                    witness = build_witness(
                        a,
                        b,
                        spec,
                        actions,
                        start,
                        state,
                        setup_actions=setup_actions,
                    )
                    if (
                        expected_net_state is not None
                        or expected_claim_consequence is not None
                    ):
                        witness = witness.model_copy(
                            update={
                                k: v
                                for k, v in {
                                    "expected_net_state": expected_net_state,
                                    "expected_claim_consequence": (
                                        expected_claim_consequence
                                    ),
                                }.items()
                                if v is not None
                            }
                        )
                    proof = check.verify(witness)
                    # Participant gate (search-only): physics may verify a one-card
                    # self-loop while the other searched card never acts. Detection
                    # already stamps strict_two_card; enforce it before acceptance.
                    if (
                        proof.status == VerificationStatus.VERIFIED
                        and witness.classification.strict_two_card
                    ):
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
