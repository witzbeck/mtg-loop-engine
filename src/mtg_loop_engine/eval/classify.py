"""Starting-state assumptions and essential-piece analysis for discoveries."""

from __future__ import annotations

from mtg_loop_engine.eval.schema import (
    AssumptionKind,
    PrerequisiteAnalysis,
    StateAssumption,
)
from mtg_loop_engine.proofs.models import LoopWitness
from mtg_loop_engine.semantics.enums import Zone
from mtg_loop_engine.semantics.ir import (
    AddCounterCost,
    AddManaEffect,
    ContinuousCostReduction,
    FreeCastCreaturesByManaValue,
    InstantGrantTapBounce,
    ManaCost,
    ReplacementMultiplyTapMana,
    ReplacementReduceM1M1Counters,
    TapCost,
)

# Intrinsic pair-piece wording must match witness zones (hand-seeded free-cast, etc.).
_ZONE_BEGIN_PHRASE: dict[Zone, str] = {
    Zone.BATTLEFIELD: "on the battlefield",
    Zone.HAND: "in hand",
    Zone.GRAVEYARD: "in the graveyard",
    Zone.EXILE: "in exile",
    Zone.LIBRARY: "in the library",
    Zone.STACK: "on the stack",
    Zone.COMMAND: "in the command zone",
}


def _intrinsic_start_description(name: str, zone: Zone) -> str:
    """Zone-aware intrinsic assumption text for a searched pair piece."""
    phrase = _ZONE_BEGIN_PHRASE.get(zone, f"in zone {zone.value}")
    return f"{name} begins {phrase}"

# Must match search.explorer seed ids (avoid import cycle with explorer → classify).
_AURA_HOST_OBJECT_ID = "aura-host"
_SCALED_MANA_SEED_LABELS: dict[str, str] = {
    "scaled-mana:creature-seed": (
        "seeded generic creature for board-scaled mana (identity irrelevant)"
    ),
    "scaled-mana:elf-seed": (
        "seeded generic elf for board-scaled mana (identity irrelevant)"
    ),
    "scaled-mana:defender-seed": (
        "seeded generic defender for board-scaled mana (identity irrelevant)"
    ),
    "setup:basic-island": (
        "seeded generic basic Island for enchanted-land tap / Earthcraft "
        "(identity irrelevant)"
    ),
    "setup:basic-plains": (
        "seeded generic basic Plains for paid {Q} create / Earthcraft "
        "(identity irrelevant; double-tap pays {1}{W})"
    ),
    "setup:mana-dork-seed": (
        "generic tap-mana dork fodder for cast-from-hand loops (identity irrelevant)"
    ),
    "setup:bounce-creature-seed": (
        "generic creature in hand to cast/bounce under grant+Alarm "
        "(identity irrelevant)"
    ),
}

# Setup ActionStep.op → disclosed generic prerequisite (Path-b / Instant grant / …).
_SETUP_SEED_OP_LABELS: dict[str, str] = {
    "seed_gain_life": (
        "generic life-gain seed to start GAIN_LIFE triggers (identity irrelevant)"
    ),
    "seed_lose_life": (
        "generic opponent life-loss seed to start OPPONENT_LOSE_LIFE "
        "triggers (identity irrelevant)"
    ),
    "seed_create_token": (
        "generic token-create seed to start CREATE_TOKEN triggers "
        "(Food identity irrelevant)"
    ),
    "seed_grant_lifelink": (
        "physics lifelink grant seed (not product-legal for ORACLE_EXACT; "
        "identity of grant source irrelevant once lifelink is on the pinger)"
    ),
    "seed_grant_tap_bounce": (
        "Instant tap-bounce grant seed (Banishing Knack / Retraction Helix "
        "class; grant persists for the witness)"
    ),
}


def _loop_pays_mana(witness: LoopWitness) -> bool:
    by_oracle = {card.oracle_id: card for card in witness.card_semantics}
    perms = {p.object_id: p for p in witness.initial_state.permanents}
    for step in witness.loop_actions:
        if step.op != "activate" or not step.actor:
            continue
        perm = perms.get(step.actor)
        if perm is None:
            continue
        card = by_oracle.get(perm.oracle_id)
        if card is None:
            continue
        for ability in card.abilities:
            if getattr(ability, "ability_id", None) != step.ability_id:
                continue
            for cost in getattr(ability, "costs", []):
                if isinstance(cost, ManaCost) and cost.amount.total() > 0:
                    return True
    return False


def _loop_pays_m1m1_counter(witness: LoopWitness) -> bool:
    by_oracle = {card.oracle_id: card for card in witness.card_semantics}
    perms = {p.object_id: p for p in witness.initial_state.permanents}
    for step in witness.loop_actions:
        if step.op != "activate" or not step.actor:
            continue
        perm = perms.get(step.actor)
        if perm is None:
            continue
        card = by_oracle.get(perm.oracle_id)
        if card is None:
            continue
        for ability in card.abilities:
            if getattr(ability, "ability_id", None) != step.ability_id:
                continue
            for cost in getattr(ability, "costs", []):
                if isinstance(cost, AddCounterCost) and cost.counter_type in {
                    "m1m1",
                    "-1/-1",
                }:
                    return True
    return False


def _loop_taps_for_mana(witness: LoopWitness) -> bool:
    by_oracle = {card.oracle_id: card for card in witness.card_semantics}
    perms = {p.object_id: p for p in witness.initial_state.permanents}
    for step in witness.loop_actions:
        if step.op != "activate" or not step.actor:
            continue
        perm = perms.get(step.actor)
        if perm is None:
            continue
        card = by_oracle.get(perm.oracle_id)
        if card is None:
            continue
        for ability in card.abilities:
            if getattr(ability, "ability_id", None) != step.ability_id:
                continue
            if getattr(ability, "is_mana_ability", False):
                return True
            costs = getattr(ability, "costs", [])
            effects = getattr(ability, "effects", [])
            if any(isinstance(c, TapCost) for c in costs) and any(
                isinstance(e, AddManaEffect) for e in effects
            ):
                return True
    return False


def analyze_prerequisites(witness: LoopWitness) -> PrerequisiteAnalysis:
    """Classify seeded resources and which searched cards actually participate."""
    pair_ids = [ref.oracle_id for ref in witness.essential_cards]
    perms = {p.object_id: p for p in witness.initial_state.permanents}
    used: set[str] = set()
    assumptions: list[StateAssumption] = []
    generic: list[str] = []
    functional: list[str] = []
    notes: list[str] = []

    for perm in witness.initial_state.permanents:
        if perm.oracle_id in pair_ids:
            assumptions.append(
                StateAssumption(
                    kind=AssumptionKind.INTRINSIC,
                    description=_intrinsic_start_description(perm.name, perm.zone),
                    object_id=perm.object_id,
                    oracle_id=perm.oracle_id,
                )
            )
        if perm.is_token:
            text = f"seeded generic creature token {perm.name!r} ({perm.object_id})"
            assumptions.append(
                StateAssumption(
                    kind=AssumptionKind.GENERIC_PREREQUISITE,
                    description=text,
                    object_id=perm.object_id,
                    oracle_id=perm.oracle_id,
                )
            )
            generic.append(text)
        elif perm.object_id == _AURA_HOST_OBJECT_ID:
            text = (
                f"seeded generic aura host creature {perm.name!r} "
                f"({perm.object_id})"
            )
            assumptions.append(
                StateAssumption(
                    kind=AssumptionKind.GENERIC_PREREQUISITE,
                    description=text,
                    object_id=perm.object_id,
                    oracle_id=perm.oracle_id,
                )
            )
            generic.append(text)
        elif perm.oracle_id in _SCALED_MANA_SEED_LABELS:
            kind = _SCALED_MANA_SEED_LABELS[perm.oracle_id]
            text = f"{kind} {perm.name!r} ({perm.object_id})"
            assumptions.append(
                StateAssumption(
                    kind=AssumptionKind.GENERIC_PREREQUISITE,
                    description=text,
                    object_id=perm.object_id,
                    oracle_id=perm.oracle_id,
                )
            )
            generic.append(text)
        if perm.counters:
            text = (
                f"seeded counters {dict(perm.counters)} on {perm.name} "
                f"({perm.object_id})"
            )
            assumptions.append(
                StateAssumption(
                    kind=AssumptionKind.GENERIC_PREREQUISITE,
                    description=text,
                    object_id=perm.object_id,
                    oracle_id=perm.oracle_id,
                )
            )
            generic.append(text)

    seen_generics = set(generic)
    for step in witness.setup_actions:
        label = _SETUP_SEED_OP_LABELS.get(step.op)
        if label is None or label in seen_generics:
            continue
        seen_generics.add(label)
        assumptions.append(
            StateAssumption(
                kind=AssumptionKind.GENERIC_PREREQUISITE,
                description=label,
            )
        )
        generic.append(label)

    for step in witness.loop_actions:
        perm = perms.get(step.actor or "")
        if perm is not None and not perm.is_token and perm.oracle_id in pair_ids:
            used.add(perm.oracle_id)
        if step.op == "cast_from_hand" and perm is not None and perm.oracle_id in pair_ids:
            used.add(perm.oracle_id)

    if _loop_pays_mana(witness):
        for card in witness.card_semantics:
            if any(isinstance(ab, ContinuousCostReduction) for ab in card.abilities):
                used.add(card.oracle_id)
                notes.append(
                    f"{card.name} participates via continuous activation-cost reduction"
                )

    if any(s.op == "cast_from_hand" for s in witness.loop_actions):
        for card in witness.card_semantics:
            if any(isinstance(ab, FreeCastCreaturesByManaValue) for ab in card.abilities):
                used.add(card.oracle_id)
                notes.append(
                    f"{card.name} participates via free cast of creatures by mana value"
                )

    if any(s.op == "activate_granted_tap_bounce" for s in witness.loop_actions):
        for card in witness.card_semantics:
            if any(isinstance(ab, InstantGrantTapBounce) for ab in card.abilities):
                used.add(card.oracle_id)
                notes.append(
                    f"{card.name} participates via Instant grant of {{T}}: bounce nonland"
                )

    if _loop_pays_m1m1_counter(witness):
        for card in witness.card_semantics:
            if any(isinstance(ab, ReplacementReduceM1M1Counters) for ab in card.abilities):
                used.add(card.oracle_id)
                notes.append(
                    f"{card.name} participates via -1/-1 counter put replacement"
                )

    if _loop_taps_for_mana(witness):
        for card in witness.card_semantics:
            if any(isinstance(ab, ReplacementMultiplyTapMana) for ab in card.abilities):
                used.add(card.oracle_id)
                notes.append(
                    f"{card.name} participates via tap-mana multiplier replacement"
                )

    unused = [oid for oid in pair_ids if oid not in used]
    for oid in unused:
        name = next((c.name for c in witness.card_semantics if c.oracle_id == oid), oid)
        notes.append(
            f"{name} is in the searched pair but does not participate in the loop"
        )

    essential_count = len(used)
    strict = essential_count == 2 and not functional
    return PrerequisiteAnalysis(
        used_oracle_ids=sorted(used),
        unused_oracle_ids=unused,
        assumptions=assumptions,
        generic_prerequisites=generic,
        functional_external_requirements=functional,
        essential_functional_count=essential_count,
        strict_two_card=strict,
        notes=notes,
    )
