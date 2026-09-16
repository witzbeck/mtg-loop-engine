"""Semantic IR: abilities, costs, effects, and card-level semantics."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from mtg_loop_engine.semantics.enums import (
    ManaScaleKind,
    SemanticCoverage,
    TriggerEvent,
    Zone,
)


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
    # Host permanent kind when ``source_self`` is False (Gond creature vs Nest land).
    host: Literal["creature", "land"] = "creature"


class ManaCost(BaseModel):
    kind: Literal["mana"] = "mana"
    amount: ManaAmount = Field(default_factory=ManaAmount)


class HybridManaCost(BaseModel):
    """Pay one mana of either listed color ({B/G} class). Combo-player tries in order."""

    kind: Literal["hybrid_mana"] = "hybrid_mana"
    colors: tuple[str, str]


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


class RemoveCounterCost(BaseModel):
    """Pay by removing counters from a controlled creature (Quillspike class)."""

    kind: Literal["remove_counter_cost"] = "remove_counter_cost"
    counter_type: str = "m1m1"
    quantity: int = 1
    selector: Literal["creature_controlled"] = "creature_controlled"


class UntapSymbolCost(BaseModel):
    """Pay {Q} by untapping the activating permanent or equipped host."""

    kind: Literal["untap_symbol"] = "untap_symbol"
    # When False, untap ``step.target`` (equipped/enchanted host) instead of actor.
    source_self: bool = True


class TapCreatureCost(BaseModel):
    """Earthcraft / Supportive Parents: tap untapped creature(s) you control."""

    kind: Literal["tap_creature"] = "tap_creature"
    # Prefer non-source creatures; explorer/executor auto-pick when step has no fodder id.
    allow_source: bool = False
    # Supportive Parents: tap two untapped creatures.
    quantity: int = 1


class PayLifeCost(BaseModel):
    """Pay N life (Aetherflux Reservoir class)."""

    kind: Literal["pay_life"] = "pay_life"
    amount: int


Cost = Annotated[
    TapCost
    | ManaCost
    | HybridManaCost
    | SacrificeCost
    | AddCounterCost
    | RemoveCounterCost
    | UntapSymbolCost
    | TapCreatureCost
    | PayLifeCost,
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
    # Scaled tap mana (Circle / Priest / Bloom Tender class).
    # Also Mana Echoes ETB → colorless × sharing creature type (trigger subject).
    mana_scale: ManaScaleKind | None = None
    scale_color: Literal[
        "white", "blue", "black", "red", "green", "any_color", "colorless"
    ] = "green"
    # Metalworker: each hand artifact adds this many of scale_color (usually 2×{C}).
    scale_multiplier: int = 1
    # Omen Hawker: mana may only pay activated abilities (not casts).
    spend_only: Literal[None, "activate_abilities"] = None


class UntapEffect(BaseModel):
    kind: Literal["untap"] = "untap"
    target: Literal[
        "self",
        "target_permanent",
        "trigger_subject",
        "target_basic_land",
        "target_land",
        "controlled_lands",
        "all_creatures",
    ] = ("self")
    # Peregrine Drake / Argothian Elder: untap up to N lands (None = all controlled lands).
    quantity: int | None = None


class TapEffect(BaseModel):
    kind: Literal["tap"] = "tap"
    target: Literal["self", "target_permanent"] = "self"


class CreateTokenEffect(BaseModel):
    kind: Literal["create_token"] = "create_token"
    name: str = "Token"
    power: int = 1
    toughness: int = 1
    quantity: int = 1
    # When set, create that many tokens equal to controlled creatures with this
    # subtype (Squirrel Girl X = Squirrels; token names infer subtype).
    quantity_equal_to_controlled_subtype: str | None = None
    is_creature: bool = True
    is_artifact: bool = False
    treasure: bool = False


class AddCounterEffect(BaseModel):
    kind: Literal["add_counter"] = "add_counter"
    counter_type: str = "p1p1"
    quantity: int = 1
    target: Literal[
        "self",
        "target_permanent",
        "target_other_creature",
        "enchanted_creature",
        "each_controlled_creature",
    ] = "self"
    # When True, use the pending trigger's recorded amount (Sunbond / Light of Promise).
    amount_from_trigger: bool = False


class RemoveCounterEffect(BaseModel):
    kind: Literal["remove_counter"] = "remove_counter"
    counter_type: str = "p1p1"
    quantity: int = 1
    target: Literal["self"] = "self"


class ReturnFromGraveyardToHandEffect(BaseModel):
    """Eternal Witness / Archaeomancer: GY → hand."""

    kind: Literal["return_gy_to_hand"] = "return_gy_to_hand"
    selector: Literal[
        "any",
        "instant_or_sorcery",
        "creature",
        "artifact",
        "artifact_mv_leq_1",
    ] = "any"


class ReturnToBattlefieldEffect(BaseModel):
    kind: Literal["return_to_battlefield"] = "return_to_battlefield"
    target: Literal["self"] = "self"


class DealDamageEffect(BaseModel):
    kind: Literal["deal_damage"] = "deal_damage"
    amount: int = 1
    target: Literal["opponent", "any_target", "each_player"] = "opponent"
    # When True, use the pending trigger's recorded amount (Shalai / "that much").
    amount_from_trigger: bool = False
    # Murderous Redcap: damage = source effective power.
    equal_to_source_power: bool = False
    # Fanatic of Mogis: damage = devotion to a color.
    equal_to_devotion: Literal[None, "white", "blue", "black", "red", "green"] = None
    equal_to_sacrificed_power: bool = False


class GainLifeEffect(BaseModel):
    kind: Literal["gain_life"] = "gain_life"
    amount: int = 1
    # When True, use the pending trigger's recorded amount (Exquisite Blood class).
    amount_from_trigger: bool = False
    # Aetherflux: gain 1 life per spell cast this turn (uses events.cast counter).
    equal_to_spells_cast_this_turn: bool = False


class DrawEffect(BaseModel):
    kind: Literal["draw"] = "draw"
    amount: int = 1
    # Edgar: draw for each artifact you control.
    equal_to_controlled_artifacts: bool = False


class LoseLifeEffect(BaseModel):
    kind: Literal["lose_life"] = "lose_life"
    amount: int = 1
    who: Literal["opponent", "you"] = "opponent"
    amount_from_trigger: bool = False
    # Shard-class: lose ceil(current_life / 2); amount recorded for following gains.
    half_life_rounded_up: bool = False
    # Gray Merchant: lose/gain equal to devotion.
    equal_to_devotion: Literal[None, "white", "blue", "black", "red", "green"] = None


class MillEffect(BaseModel):
    kind: Literal["mill"] = "mill"
    amount: int = 1
    who: Literal["opponent", "you"] = "opponent"
    # Traumatize / Fleet Swallower: mill ⌊/⌈ half library⌋ instead of fixed amount.
    half_library: Literal[None, "up", "down"] = None
    # Altar of Dementia: mill = sacrificed creature's power.
    amount_from_sacrificed_power: bool = False
    # Keening Stone: mill = cards in that player's graveyard (opponent GY count).
    amount_from_opponent_graveyard: bool = False
    amount_from_trigger: bool = False


class MoveToZoneEffect(BaseModel):
    kind: Literal["move_to_zone"] = "move_to_zone"
    zone: Zone
    # controlled_creature: bounce a creature you control (ETB Lion/Drake class).
    # controlled_creature_green_or_white: Fleetfoot Panther color filter.
    # controlled_permanent: Dream Stalker — any permanent you control.
    # controlled_nonland: Ancestral Statue — nonland you control.
    # other_controlled_creature: Temur — another creature you control (not source).
    # other_controlled_sharing_type: Cloudstone — another permanent sharing a
    #   permanent type with the trigger subject.
    # target_nonland: bounce any nonland permanent (Knack/Helix grant).
    # target_permanent: any permanent (Tidespout).
    target: Literal[
        "self",
        "controlled_creature",
        "controlled_creature_green_or_white",
        "controlled_permanent",
        "controlled_nonland",
        "other_controlled_creature",
        "other_controlled_sharing_type",
        "target_nonland",
        "target_permanent",
        "trigger_subject",
    ] = "self"


class GrantLifelinkEffect(BaseModel):
    """Grant lifelink to another creature (Heliod-class paid activation).

    Closed-loop model: no EOT cleanup — lifelink persists for the witness.
    """

    kind: Literal["grant_lifelink"] = "grant_lifelink"
    target: Literal["target_other_creature"] = "target_other_creature"


class GrantTapBounceNonlandEffect(BaseModel):
    """Banishing Knack / Retraction Helix: grant {T}: bounce nonland (persists for witness)."""

    kind: Literal["grant_tap_bounce_nonland"] = "grant_tap_bounce_nonland"
    target: Literal["target_creature"] = "target_creature"


Effect = Annotated[
    AddManaEffect
    | UntapEffect
    | TapEffect
    | CreateTokenEffect
    | AddCounterEffect
    | RemoveCounterEffect
    | ReturnFromGraveyardToHandEffect
    | ReturnToBattlefieldEffect
    | DealDamageEffect
    | GainLifeEffect
    | DrawEffect
    | LoseLifeEffect
    | MillEffect
    | MoveToZoneEffect
    | GrantLifelinkEffect
    | GrantTapBounceNonlandEffect,
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
    # Mox Opal metalcraft: ≥3 controlled artifacts on the battlefield.
    requires_metalcraft: bool = False
    # Fanatic ferocious: controlled creature with effective power ≥ N.
    requires_controlled_power_at_least: int | None = None


class TriggeredAbility(BaseModel):
    kind: Literal["triggered"] = "triggered"
    ability_id: str
    event: TriggerEvent
    # Optional filter: only tokens, only controlled creatures, etc.
    filter: Literal[
        "any",
        "creature",
        "token_creature",
        "self",
        "controlled_creature",
        "controlled_nonartifact",
        "other_controlled_creature",
        "other_controlled_human",
        "other_controlled_green",
        "other_controlled_nontoken_creature",
        "controlled_nontoken_creature",
        "other_controlled_black_creature",
        "cast_creature",
        "cast_noncreature",
        "cast_colorless",
        "cast_red",
        "cast_artifact",
    ] = "any"
    effects: list[Effect] = Field(default_factory=list)
    intervening_if: str | None = None
    supported: bool = True


class ContinuousCostReduction(BaseModel):
    kind: Literal["continuous_cost_reduction"] = "continuous_cost_reduction"
    ability_id: str
    reduce_generic: int = 1
    applies_to: Literal[
        "activated_abilities_you_control",
        "enchanted_artifact_activated",
    ] = "activated_abilities_you_control"
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


class ReplacementAmplifyP1P1Counters(BaseModel):
    """Kami / Hardened Scales: +1/+1 puts become that many plus one."""

    kind: Literal["replacement_amplify_p1p1"] = "replacement_amplify_p1p1"
    ability_id: str
    plus: int = 1
    applies_to: Literal["permanents_you_control", "creatures_you_control"] = (
        "permanents_you_control"
    )
    supported: bool = True


class ReplacementMultiplyTapMana(BaseModel):
    """Mana Reflection / Nyxbloom class: multiply mana from tapping permanents."""

    kind: Literal["replacement_multiply_tap_mana"] = "replacement_multiply_tap_mana"
    ability_id: str
    multiplier: Literal[2, 3] = 2
    supported: bool = True


class ReplacementDoubleTokens(BaseModel):
    """Parallel Lives / Anointed Procession: create twice as many tokens."""

    kind: Literal["replacement_double_tokens"] = "replacement_double_tokens"
    ability_id: str
    multiplier: int = 2
    supported: bool = True


class ReplacementDoubleMill(BaseModel):
    """Bruvac: if an opponent would mill, they mill twice that many instead."""

    kind: Literal["replacement_double_mill"] = "replacement_double_mill"
    ability_id: str
    multiplier: int = 2
    supported: bool = True


class GrantActivatedAbility(BaseModel):
    """Cryptolith Rite / Basal Sliver: grant an activated ability to matching hosts."""

    kind: Literal["grant_activated"] = "grant_activated"
    ability_id: str
    host_filter: Literal[
        "creatures_you_control",
        "slivers_you_control",
        "white_creatures_you_control",
    ] = "creatures_you_control"
    costs: list[Cost] = Field(default_factory=list)
    effects: list[Effect] = Field(default_factory=list)
    is_mana_ability: bool = False
    uses_stack: bool = True
    supported: bool = True


class FreeCastCreaturesByManaValue(BaseModel):
    """Aluren: cast creatures with mana value ≤ N without paying mana."""

    kind: Literal["free_cast_creatures_by_mv"] = "free_cast_creatures_by_mv"
    ability_id: str
    max_mana_value: int = 3
    supported: bool = True


class InstantGrantTapBounce(BaseModel):
    """Banishing Knack / Retraction Helix Instant: setup grants tap-bounce (witness-persistent)."""

    kind: Literal["instant_grant_tap_bounce"] = "instant_grant_tap_bounce"
    ability_id: str
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
    | ReplacementAmplifyP1P1Counters
    | ReplacementMultiplyTapMana
    | ReplacementDoubleTokens
    | ReplacementDoubleMill
    | GrantActivatedAbility
    | FreeCastCreaturesByManaValue
    | InstantGrantTapBounce
    | ProofIrrelevantStatic,
    Field(discriminator="kind"),
]


class CardSemantics(BaseModel):
    oracle_id: str
    name: str
    types: list[str] = Field(default_factory=list)
    # Scryfall WUBRG color letters (e.g. ["G"]); empty = colorless.
    colors: list[str] = Field(default_factory=list)
    mana_cost: ManaAmount = Field(default_factory=ManaAmount)
    mana_value: int = 0
    abilities: list[Ability] = Field(default_factory=list)
    unsupported_fragments: list[str] = Field(default_factory=list)
    coverage: SemanticCoverage = SemanticCoverage.COMPLETE

    def relevant_unsupported(self) -> bool:
        return self.coverage == SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF or any(
            not getattr(a, "supported", True) for a in self.abilities
        )
