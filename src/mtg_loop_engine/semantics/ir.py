"""Semantic IR: abilities, costs, effects, and card-level semantics."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent, Zone


class ManaAmount(BaseModel):
    white: int = 0
    blue: int = 0
    black: int = 0
    red: int = 0
    green: int = 0
    colorless: int = 0
    generic: int = 0

    def total(self) -> int:
        return (
            self.white
            + self.blue
            + self.black
            + self.red
            + self.green
            + self.colorless
            + self.generic
        )


class TapCost(BaseModel):
    kind: Literal["tap"] = "tap"
    source_self: bool = True


class ManaCost(BaseModel):
    kind: Literal["mana"] = "mana"
    amount: ManaAmount = Field(default_factory=ManaAmount)


class SacrificeCost(BaseModel):
    kind: Literal["sacrifice"] = "sacrifice"
    # Generic fodder vs self.
    selector: Literal["self", "creature_controlled", "token_creature_controlled"] = (
        "creature_controlled"
    )


Cost = Annotated[TapCost | ManaCost | SacrificeCost, Field(discriminator="kind")]


class AddManaEffect(BaseModel):
    kind: Literal["add_mana"] = "add_mana"
    amount: ManaAmount


class UntapEffect(BaseModel):
    kind: Literal["untap"] = "untap"
    target: Literal["self", "target_permanent"] = "self"


class TapEffect(BaseModel):
    kind: Literal["tap"] = "tap"
    target: Literal["self", "target_permanent"] = "self"


class CreateTokenEffect(BaseModel):
    kind: Literal["create_token"] = "create_token"
    name: str = "Token"
    power: int = 1
    toughness: int = 1
    quantity: int = 1
    is_creature: bool = True
    is_artifact: bool = False
    treasure: bool = False


class AddCounterEffect(BaseModel):
    kind: Literal["add_counter"] = "add_counter"
    counter_type: str = "p1p1"
    quantity: int = 1
    target: Literal["self", "target_permanent"] = "self"


class RemoveCounterEffect(BaseModel):
    kind: Literal["remove_counter"] = "remove_counter"
    counter_type: str = "p1p1"
    quantity: int = 1
    target: Literal["self"] = "self"


class ReturnToBattlefieldEffect(BaseModel):
    kind: Literal["return_to_battlefield"] = "return_to_battlefield"
    target: Literal["self"] = "self"


class DealDamageEffect(BaseModel):
    kind: Literal["deal_damage"] = "deal_damage"
    amount: int = 1
    target: Literal["opponent", "any_target"] = "opponent"


class GainLifeEffect(BaseModel):
    kind: Literal["gain_life"] = "gain_life"
    amount: int = 1


class LoseLifeEffect(BaseModel):
    kind: Literal["lose_life"] = "lose_life"
    amount: int = 1
    who: Literal["opponent", "you"] = "opponent"


class MoveToZoneEffect(BaseModel):
    kind: Literal["move_to_zone"] = "move_to_zone"
    zone: Zone
    target: Literal["self"] = "self"


Effect = Annotated[
    AddManaEffect
    | UntapEffect
    | TapEffect
    | CreateTokenEffect
    | AddCounterEffect
    | RemoveCounterEffect
    | ReturnToBattlefieldEffect
    | DealDamageEffect
    | GainLifeEffect
    | LoseLifeEffect
    | MoveToZoneEffect,
    Field(discriminator="kind"),
]


class ActivatedAbility(BaseModel):
    kind: Literal["activated"] = "activated"
    ability_id: str
    costs: list[Cost] = Field(default_factory=list)
    effects: list[Effect] = Field(default_factory=list)
    uses_stack: bool = True
    is_mana_ability: bool = False
    once_per_turn: bool = False
    supported: bool = True


class TriggeredAbility(BaseModel):
    kind: Literal["triggered"] = "triggered"
    ability_id: str
    event: TriggerEvent
    # Optional filter: only tokens, only controlled creatures, etc.
    filter: Literal["any", "creature", "token_creature", "self"] = "any"
    effects: list[Effect] = Field(default_factory=list)
    intervening_if: str | None = None
    supported: bool = True


class ContinuousCostReduction(BaseModel):
    kind: Literal["continuous_cost_reduction"] = "continuous_cost_reduction"
    ability_id: str
    reduce_generic: int = 1
    applies_to: Literal["activated_abilities_you_control"] = (
        "activated_abilities_you_control"
    )
    supported: bool = True


class ReplacementExileInsteadOfGraveyard(BaseModel):
    """Simple replacement: if a creature would die, exile it instead."""

    kind: Literal["replacement_exile_on_death"] = "replacement_exile_on_death"
    ability_id: str
    applies_to: Literal["creatures_you_control"] = "creatures_you_control"
    supported: bool = True


class ProofIrrelevantStatic(BaseModel):
    """Oracle text intentionally modeled as supported but non-participating in loop proofs."""

    kind: Literal["proof_irrelevant_static"] = "proof_irrelevant_static"
    ability_id: str
    clause: str
    supported: bool = True


Ability = Annotated[
    ActivatedAbility
    | TriggeredAbility
    | ContinuousCostReduction
    | ReplacementExileInsteadOfGraveyard
    | ProofIrrelevantStatic,
    Field(discriminator="kind"),
]


class CardSemantics(BaseModel):
    oracle_id: str
    name: str
    types: list[str] = Field(default_factory=list)
    abilities: list[Ability] = Field(default_factory=list)
    unsupported_fragments: list[str] = Field(default_factory=list)
    coverage: SemanticCoverage = SemanticCoverage.COMPLETE

    def relevant_unsupported(self) -> bool:
        return self.coverage == SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF or any(
            not getattr(a, "supported", True) for a in self.abilities
        )
