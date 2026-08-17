"""Shared builders for gold fixtures and discovered witnesses.

Search imports `bf` / `two_card` from here on purpose: a discovered
`LoopWitness` is constructed with the same board and classification
vocabulary as gold_core, so verifier inputs stay comparable. This package
still must not leak pair labels into search.
"""

from __future__ import annotations

from mtg_loop_engine.proofs.models import (
    ActionStep,
    Classification,
    EssentialCardRef,
    InitialStateSpec,
    LoopRelevantState,
    LoopWitness,
    OutputDelta,
    PermanentSpec,
    Prerequisite,
    StateDimension,
)
from mtg_loop_engine.semantics.enums import (
    ComparisonOp,
    Consequence,
    LoopType,
    OutputType,
    SemanticCoverage,
    VerificationStatus,
    Zone,
)
from mtg_loop_engine.semantics.ir import CardSemantics, ManaAmount


def two_card(
    *,
    essential: list[EssentialCardRef],
    generic: list[Prerequisite] | None = None,
    functional: list[Prerequisite] | None = None,
) -> Classification:
    functional = functional or []
    return Classification(
        essential_card_count=2,
        strict_two_card=len(functional) == 0,
        generic_prerequisites=generic or [],
        functional_external_requirements=functional,
        loop_type=LoopType.ARBITRARY_REPEATABLE,
    )


def dim(path: str, op: ComparisonOp, value=None) -> StateDimension:
    return StateDimension(path=path, op=op, value=value)


def witness(
    *,
    id: str,
    classification: Classification,
    essential_cards: list[EssentialCardRef],
    card_semantics: list[CardSemantics],
    initial_state: InitialStateSpec,
    loop_actions: list[ActionStep],
    relevant_state: LoopRelevantState,
    expected_outputs: list[OutputDelta],
    setup_actions: list[ActionStep] | None = None,
    expected_status: VerificationStatus | None = None,
    tier: str = "gold_core",
    coverage: SemanticCoverage = SemanticCoverage.COMPLETE,
    prerequisites: list[Prerequisite] | None = None,
    assumptions: list[str] | None = None,
    deterministic: bool = True,
) -> LoopWitness:
    return LoopWitness(
        id=id,
        classification=classification,
        essential_cards=essential_cards,
        card_semantics=card_semantics,
        initial_state=initial_state,
        setup_actions=setup_actions or [],
        loop_actions=loop_actions,
        relevant_state=relevant_state,
        expected_outputs=expected_outputs,
        expected_status=expected_status,
        tier=tier,  # type: ignore[arg-type]
        semantic_coverage=coverage,
        prerequisites=prerequisites or [],
        assumptions=assumptions or [],
        deterministic=deterministic,
    )


def bf(
    object_id: str,
    oracle_id: str,
    name: str,
    *,
    tapped: bool = False,
    is_creature: bool = False,
    is_artifact: bool = False,
    is_token: bool = False,
    counters: dict | None = None,
    summoning_sick: bool = False,
    power: int | None = None,
    toughness: int | None = None,
) -> PermanentSpec:
    return PermanentSpec(
        object_id=object_id,
        oracle_id=oracle_id,
        name=name,
        zone=Zone.BATTLEFIELD,
        tapped=tapped,
        is_creature=is_creature,
        is_artifact=is_artifact,
        is_token=is_token,
        counters=counters or {},
        summoning_sick=summoning_sick,
        power=power,
        toughness=toughness,
    )


def out(type_: OutputType, delta: int = 1, cons: Consequence = Consequence.ACCUMULATES) -> OutputDelta:
    return OutputDelta(type=type_, delta_per_iteration=delta, consequence=cons)


__all__ = [
    "ManaAmount",
    "two_card",
    "dim",
    "witness",
    "bf",
    "out",
    "ActionStep",
    "Classification",
    "EssentialCardRef",
    "InitialStateSpec",
    "LoopRelevantState",
    "OutputDelta",
    "Prerequisite",
    "ComparisonOp",
    "Consequence",
    "OutputType",
    "VerificationStatus",
    "SemanticCoverage",
    "Zone",
]
