"""Starting-state assumptions and essential-piece analysis for discoveries."""

from __future__ import annotations

from mtg_loop_engine.eval.schema import (
    AssumptionKind,
    PrerequisiteAnalysis,
    StateAssumption,
)
from mtg_loop_engine.proofs.models import LoopWitness
from mtg_loop_engine.semantics.ir import ContinuousCostReduction, ManaCost


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
                    description=f"{perm.name} begins on the battlefield",
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

    for step in witness.loop_actions:
        perm = perms.get(step.actor or "")
        if perm is not None and not perm.is_token and perm.oracle_id in pair_ids:
            used.add(perm.oracle_id)

    if _loop_pays_mana(witness):
        for card in witness.card_semantics:
            if any(isinstance(ab, ContinuousCostReduction) for ab in card.abilities):
                used.add(card.oracle_id)
                notes.append(
                    f"{card.name} participates via continuous activation-cost reduction"
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
