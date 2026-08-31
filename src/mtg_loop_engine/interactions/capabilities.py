"""Capability signatures extracted from semantic IR."""

from __future__ import annotations

from pydantic import BaseModel, Field

from mtg_loop_engine.semantics.enums import ManaScaleKind, TriggerEvent
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    AddCounterCost,
    AddCounterEffect,
    AddManaEffect,
    CardSemantics,
    ContinuousCostReduction,
    CreateTokenEffect,
    DealDamageEffect,
    DrawEffect,
    GainLifeEffect,
    LoseLifeEffect,
    ManaCost,
    MillEffect,
    RemoveCounterEffect,
    ReplacementReduceM1M1Counters,
    ReturnToBattlefieldEffect,
    SacrificeCost,
    TapCost,
    TriggeredAbility,
    UntapEffect,
)


class CardCapabilities(BaseModel):
    oracle_id: str
    name: str
    produces: set[str] = Field(default_factory=set)
    requires: set[str] = Field(default_factory=set)
    triggers_on: set[str] = Field(default_factory=set)
    modifies: set[str] = Field(default_factory=set)

    def needs_token_fodder(self) -> bool:
        return "sac_token" in self.requires

    def removes_p1p1(self) -> bool:
        return "remove_counter" in self.requires

    def needs_p1p1_mana_seed(self) -> bool:
        """Tap-for-mana scales with +1/+1 counters (Gyre Sage class)."""
        return "mana_from_p1p1" in self.produces

    def needs_creature_count_mana_seed(self) -> bool:
        return "mana_scale_creature" in self.produces

    def needs_elf_count_mana_seed(self) -> bool:
        return "mana_scale_elf" in self.produces

    def needs_defender_count_mana_seed(self) -> bool:
        return "mana_scale_defender" in self.produces


def extract_capabilities(card: CardSemantics) -> CardCapabilities:
    caps = CardCapabilities(oracle_id=card.oracle_id, name=card.name)
    for ab in card.abilities:
        if not getattr(ab, "supported", True):
            continue
        if isinstance(ab, ContinuousCostReduction):
            caps.modifies.add("reduce_activation_cost")
            continue
        if isinstance(ab, ReplacementReduceM1M1Counters):
            caps.modifies.add("m1m1_put")
            continue
        if isinstance(ab, TriggeredAbility):
            caps.triggers_on.add(ab.event.value)
            _effects(ab.effects, caps)
            if ab.event == TriggerEvent.DIES and any(
                isinstance(e, ReturnToBattlefieldEffect) for e in ab.effects
            ):
                caps.produces.add("dies_return")
            continue
        if isinstance(ab, ActivatedAbility):
            for cost in ab.costs:
                if isinstance(cost, TapCost):
                    caps.requires.add("tap")
                elif isinstance(cost, ManaCost):
                    caps.requires.add("mana")
                elif isinstance(cost, SacrificeCost):
                    caps.requires.add(f"sac_{cost.selector}")
                    if cost.selector == "self":
                        caps.requires.add("sac_self")
                    elif cost.selector == "token_creature_controlled":
                        caps.requires.add("sac_token")
                    else:
                        caps.requires.add("sac_creature")
                elif isinstance(cost, AddCounterCost) and cost.counter_type in {
                    "m1m1",
                    "-1/-1",
                }:
                    caps.requires.add("m1m1_put")
            for effect in ab.effects:
                if isinstance(effect, RemoveCounterEffect):
                    caps.requires.add("remove_counter")
                if isinstance(effect, ReturnToBattlefieldEffect):
                    caps.produces.add("gy_return")
            _effects(ab.effects, caps)
    return caps


def _effects(effects: list, caps: CardCapabilities) -> None:
    for effect in effects:
        if isinstance(effect, AddManaEffect):
            caps.produces.add("mana")
            if effect.equal_to_source_p1p1_counters:
                caps.produces.add("mana_from_p1p1")
            if effect.mana_scale is ManaScaleKind.CONTROLLED_CREATURES:
                caps.produces.add("mana_scale_creature")
            elif effect.mana_scale in {
                ManaScaleKind.CONTROLLED_ELF,
                ManaScaleKind.BATTLEFIELD_ELF,
            }:
                caps.produces.add("mana_scale_elf")
            elif effect.mana_scale is ManaScaleKind.CONTROLLED_DEFENDERS:
                caps.produces.add("mana_scale_defender")
        elif isinstance(effect, UntapEffect):
            caps.produces.add("untap")
        elif isinstance(effect, CreateTokenEffect):
            caps.produces.add("token")
            caps.produces.add("etb")
            caps.produces.add("create_token")
        elif isinstance(effect, AddCounterEffect):
            caps.produces.add("add_counter")
        elif isinstance(effect, DealDamageEffect):
            caps.produces.add("damage")
        elif isinstance(effect, GainLifeEffect):
            caps.produces.add("life_gain")
        elif isinstance(effect, LoseLifeEffect):
            caps.produces.add("life_loss")
        elif isinstance(effect, MillEffect):
            caps.produces.add("mill")
        elif isinstance(effect, DrawEffect):
            caps.produces.add("draw")
        elif isinstance(effect, ReturnToBattlefieldEffect):
            caps.produces.add("etb")


def join_reasons(left: CardCapabilities, right: CardCapabilities) -> list[str]:
    """Why these two signatures might close a loop. Directional (left uses right)."""
    reasons: list[str] = []
    if left.produces & {"etb", "token"} and "enter_battlefield" in right.triggers_on:
        reasons.append("etb_trigger")
    if "tap" in left.requires and "untap" in right.produces:
        reasons.append("tap_untap")
    if left.requires & {"sac_creature", "sac_self", "sac_token"} and (
        right.produces & {"gy_return", "dies_return"}
        or "dies" in right.triggers_on
    ):
        reasons.append("sac_recursion")
    if "remove_counter" in left.requires and "add_counter" in right.produces:
        reasons.append("counter_reload")
    if "create_token" in left.produces and "create_token" in right.triggers_on:
        reasons.append("token_create_trigger")
    if "add_counter" in left.produces and "counter_added" in right.triggers_on:
        reasons.append("counter_added_trigger")
    if "mana" in left.requires and "reduce_activation_cost" in right.modifies:
        reasons.append("cost_reduce")
    if "m1m1_put" in left.requires and "m1m1_put" in right.modifies:
        reasons.append("m1m1_replacement")
    if "mana" in left.requires and "mana" in right.produces:
        reasons.append("mana_pay")
    if "dies" in right.triggers_on and left.requires & {"sac_creature", "sac_self"}:
        reasons.append("dies_payoff")
    if "life_gain" in left.produces and "gain_life" in right.triggers_on:
        reasons.append("life_to_drain")
    if "life_loss" in left.produces and "opponent_lose_life" in right.triggers_on:
        reasons.append("loss_to_gain")
    if "mill" in left.produces and "card_to_opponent_graveyard" in right.triggers_on:
        reasons.append("mill_to_graveyard")
    return reasons
