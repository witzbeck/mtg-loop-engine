"""Capability signatures extracted from semantic IR."""

from __future__ import annotations

from pydantic import BaseModel, Field

from mtg_loop_engine.semantics.enums import TriggerEvent
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    AddCounterEffect,
    AddManaEffect,
    CardSemantics,
    ContinuousCostReduction,
    CreateTokenEffect,
    DealDamageEffect,
    GainLifeEffect,
    LoseLifeEffect,
    ManaCost,
    RemoveCounterEffect,
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


def extract_capabilities(card: CardSemantics) -> CardCapabilities:
    caps = CardCapabilities(oracle_id=card.oracle_id, name=card.name)
    for ab in card.abilities:
        if not getattr(ab, "supported", True):
            continue
        if isinstance(ab, ContinuousCostReduction):
            caps.modifies.add("reduce_activation_cost")
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
        elif isinstance(effect, UntapEffect):
            caps.produces.add("untap")
        elif isinstance(effect, CreateTokenEffect):
            caps.produces.add("token")
            caps.produces.add("etb")
        elif isinstance(effect, AddCounterEffect):
            caps.produces.add("add_counter")
        elif isinstance(effect, DealDamageEffect):
            caps.produces.add("damage")
        elif isinstance(effect, GainLifeEffect):
            caps.produces.add("life_gain")
        elif isinstance(effect, LoseLifeEffect):
            caps.produces.add("life_loss")
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
    if "mana" in left.requires and "reduce_activation_cost" in right.modifies:
        reasons.append("cost_reduce")
    if "mana" in left.requires and "mana" in right.produces:
        reasons.append("mana_pay")
    if "dies" in right.triggers_on and left.requires & {"sac_creature", "sac_self"}:
        reasons.append("dies_payoff")
    return reasons
