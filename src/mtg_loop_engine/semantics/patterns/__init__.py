"""Deterministic Oracle ability patterns for gold_core families."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from mtg_loop_engine.semantics.enums import TriggerEvent
from mtg_loop_engine.semantics.ir import (
    Ability,
    ActivatedAbility,
    AddCounterEffect,
    AddManaEffect,
    ContinuousCostReduction,
    CreateTokenEffect,
    DealDamageEffect,
    GainLifeEffect,
    LoseLifeEffect,
    ManaAmount,
    ManaCost,
    RemoveCounterEffect,
    ReplacementExileInsteadOfGraveyard,
    ReturnToBattlefieldEffect,
    SacrificeCost,
    TapCost,
    TriggeredAbility,
    UntapEffect,
)

PatternFn = Callable[[str, str], Ability | None]


@dataclass(frozen=True)
class Pattern:
    pattern_id: str
    match: PatternFn


_MANA_SYMBOLS = {
    "W": "white",
    "U": "blue",
    "B": "black",
    "R": "red",
    "G": "green",
    "C": "colorless",
}


def _parse_mana_braces(blob: str) -> ManaAmount:
    """Parse sequences like {2}{B}{C}{C} into ManaAmount."""
    amount = ManaAmount()
    for sym in re.findall(r"\{([^}]+)\}", blob):
        if sym.isdigit():
            amount.generic += int(sym)
        elif sym in _MANA_SYMBOLS:
            setattr(
                amount,
                _MANA_SYMBOLS[sym],
                getattr(amount, _MANA_SYMBOLS[sym]) + 1,
            )
        elif sym == "1":
            amount.generic += 1
    return amount


def _ability_id(prefix: str, text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]
    return f"{prefix}-{slug}" if slug else prefix


def pat_tap_add_mana(text: str, name: str) -> Ability | None:
    # {T}: Add {C}{C}{C}. / {T}: Add {B}.
    m = re.match(
        r"^\{T\}: Add ((?:\{[^}]+\})+)\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    amount = _parse_mana_braces(m.group(1))
    return ActivatedAbility(
        ability_id=_ability_id("tap-mana", text),
        costs=[TapCost()],
        effects=[AddManaEffect(amount=amount)],
        is_mana_ability=True,
        uses_stack=False,
    )


def pat_mana_untap_self(text: str, name: str) -> Ability | None:
    # {3}: Untap Basalt Monolith. / {3}: Untap this permanent.
    m = re.match(
        r"^((?:\{[^}]+\})+): Untap (?:this permanent|~|"
        + re.escape(name)
        + r")\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("mana-untap", text),
        costs=[ManaCost(amount=_parse_mana_braces(m.group(1)))],
        effects=[UntapEffect(target="self")],
    )


def pat_cost_reduction(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^Activated abilities (?:of creatures )?you control cost \{(\d+)\} less to activate\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        # Training Grounds wording variant
        m = re.match(
            r"^Activated abilities you control cost \{(\d+)\} less to activate\.?$",
            text,
            re.IGNORECASE,
        )
    if not m:
        return None
    return ContinuousCostReduction(
        ability_id=_ability_id("cost-reduce", text),
        reduce_generic=int(m.group(1)),
    )


def pat_etb_untap_target(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^Whenever a creature enters(?: the battlefield)?(?: under your control)?, "
        r"untap target permanent\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("etb-untap", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="creature",
        effects=[UntapEffect(target="target_permanent")],
    )


def pat_tap_create_token(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^\{T\}: Create (?:a|one)(?: (\d+)/(\d+))? (.+?) creature token\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    power = int(m.group(1) or 1)
    toughness = int(m.group(2) or 1)
    token_name = m.group(3).strip()
    return ActivatedAbility(
        ability_id=_ability_id("tap-token", text),
        costs=[TapCost()],
        effects=[
            CreateTokenEffect(
                name=token_name, power=power, toughness=toughness, quantity=1
            )
        ],
    )


def pat_tap_create_token_untap(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^\{T\}: Create (?:a|one)(?: (\d+)/(\d+))? (.+?) creature token\. Untap (~|this permanent|"
        + re.escape(name)
        + r")\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    power = int(m.group(1) or 1)
    toughness = int(m.group(2) or 1)
    return ActivatedAbility(
        ability_id=_ability_id("tap-token-untap", text),
        costs=[TapCost()],
        effects=[
            CreateTokenEffect(
                name=m.group(3).strip(),
                power=power,
                toughness=toughness,
                quantity=1,
            ),
            UntapEffect(target="self"),
        ],
    )


def pat_sac_creature_add_mana(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^Sacrifice a creature: Add ((?:\{[^}]+\})+)\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("sac-mana", text),
        costs=[SacrificeCost(selector="creature_controlled")],
        effects=[AddManaEffect(amount=_parse_mana_braces(m.group(1)))],
        is_mana_ability=True,
        uses_stack=False,
    )


def pat_sac_self(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^Sacrifice (~|this permanent|" + re.escape(name) + r"):\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        m = re.match(r"^Sacrifice this creature\.?$", text, re.IGNORECASE)
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("sac-self", text),
        costs=[SacrificeCost(selector="self")],
        effects=[],
    )


def pat_sac_creature_outlet(text: str, name: str) -> Ability | None:
    # Sacrifice a creature: Scry 1. — scry unsupported; model as empty effects outlet
    m = re.match(
        r"^Sacrifice a creature: (Scry \d+)\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    # Treat scry as unsupported side text but keep sac outlet usable for death loops:
    # We intentionally compile the sac cost with empty effects and mark via note in compiler.
    return ActivatedAbility(
        ability_id=_ability_id("sac-outlet", text),
        costs=[SacrificeCost(selector="creature_controlled")],
        effects=[],
    )


def pat_return_from_gy(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^((?:\{[^}]+\})+): Return (~|this (?:card|permanent|creature)|"
        + re.escape(name)
        + r") from your graveyard to the battlefield\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("gy-return", text),
        costs=[ManaCost(amount=_parse_mana_braces(m.group(1)))],
        effects=[ReturnToBattlefieldEffect()],
    )


def pat_dies_return_self(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^Whenever (~|this (?:card|permanent|creature)|"
        + re.escape(name)
        + r") dies, return it to the battlefield(?: tapped)?\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("dies-return", text),
        event=TriggerEvent.DIES,
        filter="self",
        effects=[ReturnToBattlefieldEffect()],
    )


def pat_dies_lose_life(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^Whenever (?:a|another) creature dies, "
        r"(?:each opponent loses|target opponent loses) (\d+) life\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("dies-drain", text),
        event=TriggerEvent.DIES,
        filter="creature",
        effects=[LoseLifeEffect(amount=int(m.group(1)), who="opponent")],
    )


def pat_etb_damage(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^Whenever a creature enters(?: the battlefield)?(?: under your control)?, "
        r"(?:~|"
        + re.escape(name)
        + r"|it) deals (\d+) damage to (?:each|target) opponent\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        m = re.match(
            r"^Whenever a creature (?:you control )?enters(?: the battlefield)?, "
            r"(?:~|"
            + re.escape(name)
            + r") deals (\d+) damage to each opponent\.?$",
            text,
            re.IGNORECASE,
        )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("etb-damage", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="creature",
        effects=[DealDamageEffect(amount=int(m.group(1)))],
    )


def pat_etb_gain_life(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^Whenever (?:a|another) creature enters(?: the battlefield)?, you gain (\d+) life\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("etb-life", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="creature",
        effects=[GainLifeEffect(amount=int(m.group(1)))],
    )


def pat_remove_counter_damage(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^Remove a \+1/\+1 counter from (~|this permanent|"
        + re.escape(name)
        + r"): (~|it|"
        + re.escape(name)
        + r") deals 1 damage to any target\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        # Simplified gold wording
        m = re.match(
            r"^Remove a \+1/\+1 counter from (~|this permanent): "
            r"It deals 1 damage to (?:any target|target opponent)\.?$",
            text,
            re.IGNORECASE,
        )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("counter-ping", text),
        costs=[],
        effects=[
            RemoveCounterEffect(counter_type="p1p1", quantity=1),
            DealDamageEffect(amount=1, target="opponent"),
        ],
    )


def pat_put_p1p1_counter(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^(?:\{0\}: )?Put a \+1/\+1 counter on target (?:creature|permanent)\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("put-counter", text),
        costs=[],
        effects=[
            AddCounterEffect(
                counter_type="p1p1", quantity=1, target="target_permanent"
            )
        ],
    )


def pat_exile_instead_of_gy(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^If a creature would die, exile it instead\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        m = re.match(
            r"^If a card (?:or token )?would be put into a graveyard from anywhere, "
            r"exile it instead\.?$",
            text,
            re.IGNORECASE,
        )
    if not m:
        return None
    return ReplacementExileInsteadOfGraveyard(
        ability_id=_ability_id("exile-on-death", text),
    )


def pat_tap_sac_token_make_two(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^\{T\}, Sacrifice a creature token: Create (?:two|2)(?: (\d+)/(\d+))? "
        r"(.+?) creature tokens?\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    power = int(m.group(1) or 1)
    toughness = int(m.group(2) or 1)
    return ActivatedAbility(
        ability_id=_ability_id("breed", text),
        costs=[TapCost(), SacrificeCost(selector="token_creature_controlled")],
        effects=[
            CreateTokenEffect(
                name=m.group(3).strip(),
                power=power,
                toughness=toughness,
                quantity=2,
            )
        ],
    )


# Order matters: more specific patterns first.
PATTERNS: list[Pattern] = [
    Pattern("tap_create_token_untap", pat_tap_create_token_untap),
    Pattern("tap_sac_token_make_two", pat_tap_sac_token_make_two),
    Pattern("tap_create_token", pat_tap_create_token),
    Pattern("tap_add_mana", pat_tap_add_mana),
    Pattern("mana_untap_self", pat_mana_untap_self),
    Pattern("cost_reduction", pat_cost_reduction),
    Pattern("etb_untap_target", pat_etb_untap_target),
    Pattern("sac_creature_add_mana", pat_sac_creature_add_mana),
    Pattern("sac_creature_outlet", pat_sac_creature_outlet),
    Pattern("sac_self", pat_sac_self),
    Pattern("return_from_gy", pat_return_from_gy),
    Pattern("dies_return_self", pat_dies_return_self),
    Pattern("dies_lose_life", pat_dies_lose_life),
    Pattern("etb_damage", pat_etb_damage),
    Pattern("etb_gain_life", pat_etb_gain_life),
    Pattern("remove_counter_damage", pat_remove_counter_damage),
    Pattern("put_p1p1_counter", pat_put_p1p1_counter),
    Pattern("exile_instead_of_gy", pat_exile_instead_of_gy),
]


def try_match(text: str, name: str) -> tuple[str, Ability] | None:
    normalized = " ".join(text.split()).strip()
    if not normalized:
        return None
    for pattern in PATTERNS:
        ability = pattern.match(normalized, name)
        if ability is not None:
            return pattern.pattern_id, ability
    return None
