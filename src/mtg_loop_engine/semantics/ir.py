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
    # "Add one mana of any color" — spendable as W/U/B/R/G when paying.
    any_color: int = 0

    def total(self) -> int:
        return (
            self.white
            + self.blue
            + self.black
            + self.red
            + self.green
            + self.colorless
            + self.generic
            + self.any_color
        )


class TapCost(BaseModel):
    kind: Literal["tap"] = "tap"
    # When False, tap `step.target` (enchanted host) instead of the activating permanent.
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


class AddCounterCost(BaseModel):
    """Pay by putting counters on self (Devoted Druid)."""

    kind: Literal["add_counter"] = "add_counter"
    counter_type: str = "m1m1"
    quantity: int = 1
    target: Literal["self"] = "self"


Cost = Annotated[
    TapCost | ManaCost | SacrificeCost | AddCounterCost,
    Field(discriminator="kind"),
]


class AddManaEffect(BaseModel):
    kind: Literal["add_mana"] = "add_mana"
    amount: ManaAmount = Field(default_factory=ManaAmount)
    # When set, add that many of the named pool instead of `amount`
    # (e.g. "{T}: Add an amount of {G} equal to this creature's power").
    equal_to_source_power: Literal[
        None, "green", "any_color", "colorless"
    ] = None
    # Gyre Sage class: "{T}: Add {G} for each +1/+1 counter on this creature."
    equal_to_source_p1p1_counters: Literal[
        None, "green", "any_color", "colorless"
    ] = None


class UntapEffect(BaseModel):
    kind: Literal["untap"] = "untap"
    target: Literal["self", "target_permanent", "all_creatures"] = "self"


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
    target: Literal["self", "target_permanent", "target_other_creature"] = "self"


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
    # When True, use the pending trigger's recorded amount (Exquisite Blood class).
    amount_from_trigger: bool = False


class DrawEffect(BaseModel):
    kind: Literal["draw"] = "draw"
    amount: int = 1


class LoseLifeEffect(BaseModel):
    kind: Literal["lose_life"] = "lose_life"
    amount: int = 1
    who: Literal["opponent", "you"] = "opponent"
    amount_from_trigger: bool = False


class MillEffect(BaseModel):
    kind: Literal["mill"] = "mill"
    amount: int = 1
    who: Literal["opponent", "you"] = "opponent"


class MoveToZoneEffect(BaseModel):
    kind: Literal["move_to_zone"] = "move_to_zone"
    zone: Zone
    target: Literal["self"] = "self"


class GrantLifelinkEffect(BaseModel):
    """Grant lifelink to another creature (Heliod-class paid activation).

    Closed-loop model: no EOT cleanup — lifelink persists for the witness.
    """

    kind: Literal["grant_lifelink"] = "grant_lifelink"
    target: Literal["target_other_creature"] = "target_other_creature"


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
    | DrawEffect
    | LoseLifeEffect
    | MillEffect
    | MoveToZoneEffect
    | GrantLifelinkEffect,
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
    # Cast-from-GY style gates (Gravecrawler): need a Zombie on battlefield.
    requires_zombie: bool = False


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
    # Zirda: ignore mana abilities; leave at least one mana in the cost.
    exclude_mana_abilities: bool = False
    min_mana_remaining: int = 0
    supported: bool = True


class ReplacementExileInsteadOfGraveyard(BaseModel):
    """Simple replacement: if a creature would die, exile it instead."""

    kind: Literal["replacement_exile_on_death"] = "replacement_exile_on_death"
    ability_id: str
    applies_to: Literal["creatures_you_control"] = "creatures_you_control"
    supported: bool = True


class ReplacementReduceM1M1Counters(BaseModel):
    """Vizier of Remedies: reduce -1/-1 puts by one (may reduce to zero)."""

    kind: Literal["replacement_reduce_m1m1"] = "replacement_reduce_m1m1"
    ability_id: str
    reduce_by: int = 1
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
    | ReplacementReduceM1M1Counters
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
