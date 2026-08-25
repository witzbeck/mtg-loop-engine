"""Proof and witness contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from mtg_loop_engine.semantics.enums import (
    ComparisonOp,
    Consequence,
    LoopType,
    OutputType,
    ProofKind,
    SemanticCoverage,
    VerificationStatus,
    Zone,
)
from mtg_loop_engine.semantics.ir import CardSemantics, ManaAmount


class Prerequisite(BaseModel):
    kind: str
    description: str
    details: dict[str, Any] = Field(default_factory=dict)


class EssentialCardRef(BaseModel):
    oracle_id: str
    name: str
    role: str | None = None


class Classification(BaseModel):
    essential_card_count: int
    strict_two_card: bool
    generic_prerequisites: list[Prerequisite] = Field(default_factory=list)
    functional_external_requirements: list[Prerequisite] = Field(default_factory=list)
    loop_type: LoopType = LoopType.ARBITRARY_REPEATABLE


class StateDimension(BaseModel):
    """One dimension of proof-specific LoopRelevantState."""

    path: str
    op: ComparisonOp
    value: Any


class LoopRelevantState(BaseModel):
    """Proof-specific recurrence projection (dependency set D)."""

    dimensions: list[StateDimension] = Field(default_factory=list)


class OutputDelta(BaseModel):
    type: OutputType
    delta_per_iteration: int
    consequence: Consequence = Consequence.ACCUMULATES
    repeatable: bool = True


class NetStateDelta(BaseModel):
    """Net pool/life/board benefit across one loop iteration (not gross events)."""

    mana: ManaAmount = Field(default_factory=ManaAmount)
    life_you: int = 0
    life_opponent: int = 0
    creature_tokens: int = 0
    plus_one_counters: int = 0


class PermanentSpec(BaseModel):
    object_id: str
    oracle_id: str
    name: str
    controller: Literal["you", "opponent"] = "you"
    zone: Zone = Zone.BATTLEFIELD
    tapped: bool = False
    summoning_sick: bool = False
    counters: dict[str, int] = Field(default_factory=dict)
    is_token: bool = False
    is_creature: bool = False
    is_artifact: bool = False
    power: int | None = None
    toughness: int | None = None
    undying: bool = False
    damage_marked: int = 0


class InitialStateSpec(BaseModel):
    permanents: list[PermanentSpec] = Field(default_factory=list)
    mana: ManaAmount = Field(default_factory=ManaAmount)
    life_you: int = 40
    life_opponent: int = 40
    event_counters: dict[str, int] = Field(default_factory=dict)


class ActionStep(BaseModel):
    """A single proposed action in a witness sequence."""

    op: str
    # Common fields; unused ones stay None.
    actor: str | None = None  # permanent object_id
    ability_id: str | None = None
    target: str | None = None
    choose_may: bool | None = None
    note: str | None = None


class LoopWitness(BaseModel):
    """Witness-in contract for the verifier (no search)."""

    id: str
    classification: Classification
    essential_cards: list[EssentialCardRef]
    card_semantics: list[CardSemantics]
    initial_state: InitialStateSpec
    setup_actions: list[ActionStep] = Field(default_factory=list)
    loop_actions: list[ActionStep]
    relevant_state: LoopRelevantState
    expected_outputs: list[OutputDelta] = Field(default_factory=list)
    expected_net_state: NetStateDelta | None = None
    expected_claim_consequence: Consequence | None = None
    assumptions: list[str] = Field(default_factory=list)
    prerequisites: list[Prerequisite] = Field(default_factory=list)
    deterministic: bool = True
    semantic_coverage: SemanticCoverage = SemanticCoverage.COMPLETE
    # For hard negatives / extended: expected verification outcome.
    expected_status: VerificationStatus | None = None
    tier: Literal["gold_core", "gold_extended", "hard_negative"] = "gold_core"


class VersionIdentity(BaseModel):
    oracle_snapshot_hash: str | None = None
    spellbook_snapshot_hash: str | None = None
    rules_version: str
    semantic_schema_version: str
    engine_version: str
    proof_schema_version: str
    git_sha: str | None = None


class RecurrenceResult(BaseModel):
    ok: bool
    details: list[str] = Field(default_factory=list)


class LoopProof(BaseModel):
    kind: ProofKind = ProofKind.VALID
    witness_id: str
    essential_cards: list[EssentialCardRef]
    classification: Classification
    versions: VersionIdentity
    assumptions: list[str] = Field(default_factory=list)
    prerequisites: list[Prerequisite] = Field(default_factory=list)
    initial_state: InitialStateSpec
    setup_actions: list[ActionStep] = Field(default_factory=list)
    loop_actions: list[ActionStep] = Field(default_factory=list)
    recurrence: RecurrenceResult
    output_deltas: list[OutputDelta] = Field(default_factory=list)
    net_state: NetStateDelta | None = None
    claim_consequence: Consequence | None = None
    consequences: list[Consequence] = Field(default_factory=list)
    status: VerificationStatus
    rejection_reason: str | None = None
    semantic_coverage: SemanticCoverage
    proof_hash: str
