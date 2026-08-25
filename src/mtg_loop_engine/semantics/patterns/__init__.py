"""Deterministic Oracle ability patterns for gold_core families."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from mtg_loop_engine.semantics.enums import TriggerEvent
from mtg_loop_engine.semantics.ir import (
    Ability,
    ActivatedAbility,
    AddCounterCost,
    AddCounterEffect,
    AddManaEffect,
    ContinuousCostReduction,
    CreateTokenEffect,
    DealDamageEffect,
    DrawEffect,
    GainLifeEffect,
    LoseLifeEffect,
    ManaAmount,
    ManaCost,
    RemoveCounterEffect,
    ReplacementExileInsteadOfGraveyard,
    ReplacementReduceM1M1Counters,
    ProofIrrelevantStatic,
    ReturnToBattlefieldEffect,
    SacrificeCost,
    TapCost,
    TapEffect,
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


def _parse_activation_costs(cost_blob: str) -> list | None:
    """Parse '{2}, {T}' / '{T}' / '{3}' style activation cost prefixes."""
    parts = [p.strip() for p in cost_blob.split(",") if p.strip()]
    if not parts:
        return None
    costs: list = []
    for part in parts:
        if re.fullmatch(r"\{T\}", part, flags=re.IGNORECASE):
            costs.append(TapCost())
        elif re.fullmatch(r"(?:\{[^}]+\})+", part):
            costs.append(ManaCost(amount=_parse_mana_braces(part)))
        else:
            return None
    return costs


def pat_tap_add_mana(text: str, name: str) -> Ability | None:
    # {T}: Add {C}{C}{C}. / {T}: Add {B}.
    m = re.match(
        r"^\{T\}: Add ((?:\{[^}]+\})+)\.?$",
        text,
        re.IGNORECASE,
    )
    if m:
        amount = _parse_mana_braces(m.group(1))
        return ActivatedAbility(
            ability_id=_ability_id("tap-mana", text),
            costs=[TapCost()],
            effects=[AddManaEffect(amount=amount)],
            is_mana_ability=True,
            uses_stack=False,
        )
    # {T}: Add one mana of any color.
    m_any = re.match(
        r"^\{T\}: Add one mana of any color(?: to your mana pool)?\.?$",
        text,
        re.IGNORECASE,
    )
    if m_any:
        return ActivatedAbility(
            ability_id=_ability_id("tap-mana-any", text),
            costs=[TapCost()],
            effects=[AddManaEffect(amount=ManaAmount(any_color=1))],
            is_mana_ability=True,
            uses_stack=False,
        )
    # {T}: Add an amount of {G} equal to this creature's power. (Viridian Joiner)
    m_pow = re.match(
        r"^\{T\}: Add an amount of \{([GC])\} equal to "
        r"(?:this creature's|its|~'s|"
        + re.escape(name)
        + r"'s) power\.?$",
        text,
        re.IGNORECASE,
    )
    if m_pow:
        color = "green" if m_pow.group(1).upper() == "G" else "colorless"
        return ActivatedAbility(
            ability_id=_ability_id("tap-mana-power", text),
            costs=[TapCost()],
            effects=[AddManaEffect(equal_to_source_power=color)],  # type: ignore[arg-type]
            is_mana_ability=True,
            uses_stack=False,
        )
    # {T}: Add X mana of any one color, where X is this creature's power.
    m_x = re.match(
        r"^\{T\}: Add X mana of any one color, where X is "
        r"(?:this creature's|its|~'s|"
        + re.escape(name)
        + r"'s) power\.?$",
        text,
        re.IGNORECASE,
    )
    if m_x:
        return ActivatedAbility(
            ability_id=_ability_id("tap-mana-power-any", text),
            costs=[TapCost()],
            effects=[AddManaEffect(equal_to_source_power="any_color")],
            is_mana_ability=True,
            uses_stack=False,
        )
    # Gyre Sage: {T}: Add {G} for each +1/+1 counter on this creature.
    m_ctr = re.match(
        r"^\{T\}: Add \{([GC])\} for each \+1/\+1 counter on "
        r"(?:this creature|~|"
        + re.escape(name)
        + r")\.?$",
        text,
        re.IGNORECASE,
    )
    if m_ctr:
        color = "green" if m_ctr.group(1).upper() == "G" else "colorless"
        return ActivatedAbility(
            ability_id=_ability_id("tap-mana-p1p1", text),
            costs=[TapCost()],
            effects=[AddManaEffect(equal_to_source_p1p1_counters=color)],  # type: ignore[arg-type]
            is_mana_ability=True,
            uses_stack=False,
        )
    return None


def pat_mana_untap_self(text: str, name: str) -> Ability | None:
    # {3}: Untap Basalt Monolith. / {1}: Untap this artifact.
    m = re.match(
        r"^((?:\{[^}]+\})+): Untap (?:this (?:permanent|artifact|creature)|~|"
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


def pat_mana_untap_enchanted(text: str, name: str) -> Ability | None:
    """Freed / Pemmin's class: pay mana to untap the enchanted creature.

    Attachment is not modeled; explorer treats this as untap target_permanent
    (combo player chooses the host), same as gold ETB-untap targeting.
    """
    m = re.match(
        r"^((?:\{[^}]+\})+): Untap enchanted creature\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("mana-untap-enchanted", text),
        costs=[ManaCost(amount=_parse_mana_braces(m.group(1)))],
        effects=[UntapEffect(target="target_permanent")],
    )


def pat_mana_tap_enchanted(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^((?:\{[^}]+\})+): Tap enchanted creature\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("mana-tap-enchanted", text),
        costs=[ManaCost(amount=_parse_mana_braces(m.group(1)))],
        effects=[TapEffect(target="target_permanent")],
    )


def pat_mana_tap_gain_life(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^((?:\{[^}]+\}(?:,\s*)?)+): You gain (\d+) life\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    costs = _parse_activation_costs(m.group(1).rstrip(", "))
    if not costs:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("tap-gain-life", text),
        costs=costs,
        effects=[GainLifeEffect(amount=int(m.group(2)))],
    )


def pat_mana_tap_untap_target(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^((?:\{[^}]+\}(?:,\s*)?)+): Untap target (?:artifact or )?creature\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    costs = _parse_activation_costs(m.group(1).rstrip(", "))
    if not costs:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("tap-untap-target", text),
        costs=costs,
        effects=[UntapEffect(target="target_permanent")],
    )


def pat_mana_tap_tap_target(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^((?:\{[^}]+\}(?:,\s*)?)+): Tap target creature\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    costs = _parse_activation_costs(m.group(1).rstrip(", "))
    if not costs:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("tap-tap-target", text),
        costs=costs,
        effects=[TapEffect(target="target_permanent")],
    )


def pat_mana_tap_draw(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^((?:\{[^}]+\}(?:,\s*)?)+): Draw (?:a card|(\d+) cards?)\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    costs = _parse_activation_costs(m.group(1).rstrip(", "))
    if not costs:
        return None
    amount = int(m.group(2)) if m.group(2) else 1
    return ActivatedAbility(
        ability_id=_ability_id("tap-draw", text),
        costs=costs,
        effects=[DrawEffect(amount=amount)],
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


def pat_cant_block_this_turn(text: str, name: str) -> Ability | None:
    """Compile Zirda-style can't-block grant (not used by gold loops)."""
    m = re.match(
        r"^\{(\d+)\}, \{T\}: Target creature can't block this turn\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("cant-block", text),
        costs=[
            ManaCost(amount=ManaAmount(generic=int(m.group(1)))),
            TapCost(),
        ],
        effects=[],
    )


def pat_zirda_cost_reduction(text: str, name: str) -> Ability | None:
    """Zirda: non-mana activated abilities cost {N} less; floor one mana."""
    m = re.match(
        r"^Abilities you activate that aren't mana abilities cost \{(\d+)\} less to activate\.?"
        r"(?:\s+This effect can't reduce the mana (?:in that cost|an ability costs to activate) "
        r"to less than one mana\.?)?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ContinuousCostReduction(
        ability_id=_ability_id("zirda-cost-reduce", text),
        reduce_generic=int(m.group(1)),
        exclude_mana_abilities=True,
        min_mana_remaining=1,
    )


def pat_put_m1m1_untap_self(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^Put a -1/-1 counter on (?:this creature|~|"
        + re.escape(name)
        + r"): Untap (?:this creature|~|"
        + re.escape(name)
        + r")\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("m1m1-untap", text),
        costs=[AddCounterCost(counter_type="m1m1", quantity=1)],
        effects=[UntapEffect(target="self")],
    )


def pat_vizier_m1m1_replacement(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^If one or more -1/-1 counters would be put on a creature you control, "
        r"that many -1/-1 counters minus one are put on it instead\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ReplacementReduceM1M1Counters(
        ability_id=_ability_id("vizier-m1m1", text),
        reduce_by=1,
    )

    """Zirda: non-mana activated abilities cost {N} less; floor one mana."""
    m = re.match(
        r"^Abilities you activate that aren't mana abilities cost \{(\d+)\} less to activate\.?"
        r"(?:\s+This effect can't reduce the mana (?:in that cost|an ability costs to activate) "
        r"to less than one mana\.?)?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ContinuousCostReduction(
        ability_id=_ability_id("zirda-cost-reduce", text),
        reduce_generic=int(m.group(1)),
        exclude_mana_abilities=True,
        min_mana_remaining=1,
    )


def pat_etb_untap_target(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^Whenever a creature enters(?: the battlefield)?(?: under your control)?, "
        r"untap target permanent\.?$",
        text,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("etb-untap", text),
            event=TriggerEvent.ENTER_BATTLEFIELD,
            filter="creature",
            effects=[UntapEffect(target="target_permanent")],
        )
    # Intruder Alarm (current Oracle): Whenever a creature enters, untap all creatures.
    m_all = re.match(
        r"^Whenever a creature enters(?: the battlefield)?, untap all creatures\.?$",
        text,
        re.IGNORECASE,
    )
    if m_all:
        return TriggeredAbility(
            ability_id=_ability_id("etb-untap-all", text),
            event=TriggerEvent.ENTER_BATTLEFIELD,
            filter="creature",
            effects=[UntapEffect(target="all_creatures")],
        )
    # Village Bell-Ringer: When this creature enters, untap all creatures you control.
    m_self_all = re.match(
        r"^When (?:this creature|~|"
        + re.escape(name)
        + r") enters(?: the battlefield)?, "
        r"untap all creatures(?: you control)?\.?$",
        text,
        re.IGNORECASE,
    )
    if m_self_all:
        return TriggeredAbility(
            ability_id=_ability_id("etb-self-untap-all", text),
            event=TriggerEvent.ENTER_BATTLEFIELD,
            filter="self",
            effects=[UntapEffect(target="all_creatures")],
        )
    # Pestermite: When this creature enters, you may tap or untap target permanent.
    # Combo-player favorable: model as untap (frozen choice ownership).
    m_may = re.match(
        r"^When (?:this creature|~|"
        + re.escape(name)
        + r") enters(?: the battlefield)?, "
        r"you may tap or untap target permanent\.?$",
        text,
        re.IGNORECASE,
    )
    if m_may:
        return TriggeredAbility(
            ability_id=_ability_id("etb-may-untap-target", text),
            event=TriggerEvent.ENTER_BATTLEFIELD,
            filter="self",
            effects=[UntapEffect(target="target_permanent")],
        )
    # Midnight Guard: Whenever another creature enters, untap this creature.
    m_self = re.match(
        r"^Whenever another creature enters(?: the battlefield)?, "
        r"untap (?:this creature|~|"
        + re.escape(name)
        + r")\.?$",
        text,
        re.IGNORECASE,
    )
    if not m_self:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("etb-untap-self", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="creature",
        effects=[UntapEffect(target="self")],
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


def pat_enchanted_tap_create_token(text: str, name: str) -> Ability | None:
    """Presence of Gond class: enchanted creature has {T}: create token.

    Land hosts (Squirrel Nest) stay unsupported until land seeds exist.
    """
    m = re.match(
        r'^Enchanted creature has '
        r'"\{T\}: Create (?:a|one)(?: (\d+)/(\d+))? (.+?) creature token\."\.?$',
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    power = int(m.group(1) or 1)
    toughness = int(m.group(2) or 1)
    return ActivatedAbility(
        ability_id=_ability_id("enchanted-tap-token", text),
        costs=[TapCost(source_self=False)],
        effects=[
            CreateTokenEffect(
                name=m.group(3).strip(),
                power=power,
                toughness=toughness,
                quantity=1,
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
        r"^Sacrifice a creature: Add one mana of any color(?: to your mana pool)?\.?$",
        text,
        re.IGNORECASE,
    )
    if m:
        return ActivatedAbility(
            ability_id=_ability_id("sac-mana-any", text),
            costs=[SacrificeCost(selector="creature_controlled")],
            effects=[AddManaEffect(amount=ManaAmount(any_color=1))],
            is_mana_ability=True,
            uses_stack=False,
        )
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
        + r") from your graveyard to the battlefield(?: tapped)?"
        r"(?:\. You may cast "
        + re.escape(name)
        + r" only from your graveyard)?"
        r"(?:\. Activate only as a sorcery)?\.?$",
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


def pat_gain_life_opponent_loses_that_much(text: str, name: str) -> Ability | None:
    """Vito / Sanguine Bond: whenever you gain life, opponent loses that much."""
    m = re.match(
        r"^Whenever you gain life, "
        r"(?:target opponent|each opponent) loses that much life\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("gain-life-drain", text),
        event=TriggerEvent.GAIN_LIFE,
        filter="any",
        effects=[LoseLifeEffect(who="opponent", amount_from_trigger=True)],
    )


def pat_gain_life_opponent_loses_fixed(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^Whenever you gain life, each opponent loses (\d+) life\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("gain-life-drain-fixed", text),
        event=TriggerEvent.GAIN_LIFE,
        filter="any",
        effects=[LoseLifeEffect(amount=int(m.group(1)), who="opponent")],
    )


def pat_opponent_lose_life_you_gain_that_much(text: str, name: str) -> Ability | None:
    """Exquisite Blood / Bloodthirsty Conqueror."""
    m = re.match(
        r"^Whenever an opponent loses life, you gain that much life\.?"
        r"(?:\s*\([^)]*\))?\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("loss-to-gain", text),
        event=TriggerEvent.OPPONENT_LOSE_LIFE,
        filter="any",
        effects=[GainLifeEffect(amount_from_trigger=True)],
    )


def pat_etb_damage(text: str, name: str) -> Ability | None:
    """Creature ETB → fixed damage to opponent (Impact Tremors / Purphoros class)."""
    # Optional ability word ("Alliance — ") and trailing reminder text.
    cleaned = re.sub(r"^[A-Za-z][A-Za-z' ]*—\s*", "", text.strip())
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", cleaned).strip().rstrip(".")
    name_alts = [re.escape(name)]
    short = name.split(",")[0].strip()
    if short and short.casefold() != name.casefold():
        name_alts.append(re.escape(short))
    front = name.split("//")[0].strip()
    if front and front.casefold() not in {name.casefold(), short.casefold()}:
        name_alts.append(re.escape(front))
    source = (
        r"(?:~|"
        + "|".join(name_alts)
        + r"|it|this (?:creature|enchantment|permanent))"
    )
    m = re.match(
        r"^Whenever (?:a|another) creature(?: you control)? "
        r"enters(?: the battlefield)?(?: under your control)?, "
        + source
        + r" deals (\d+) damage to (?:each|target) opponent$",
        cleaned,
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
        r"^Whenever (?:a|another) creature(?: you control)? "
        r"enters(?: the battlefield)?, you gain (\d+) life\.?$",
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


def pat_gain_life_put_p1p1_target(text: str, name: str) -> Ability | None:
    """Heliod: Whenever you gain life, put +1/+1 on target creature/enchantment."""
    m = re.match(
        r"^Whenever you gain life, put a \+1/\+1 counter on target "
        r"(?:creature or enchantment|creature) you control\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("gain-life-p1p1", text),
        event=TriggerEvent.GAIN_LIFE,
        filter="any",
        effects=[
            AddCounterEffect(
                counter_type="p1p1",
                quantity=1,
                target="target_permanent",
            )
        ],
    )


def pat_gain_life_untap_self(text: str, name: str) -> Ability | None:
    """Famished Paladin: Whenever you gain life, untap this creature."""
    m = re.match(
        r"^Whenever you gain life, untap (?:this creature|~|"
        + re.escape(name)
        + r")\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("gain-life-untap-self", text),
        event=TriggerEvent.GAIN_LIFE,
        filter="any",
        effects=[UntapEffect(target="self")],
    )


def pat_mana_put_p1p1_self(text: str, name: str) -> Ability | None:
    """Walking Ballista: {N}: Put a +1/+1 counter on this creature."""
    m = re.match(
        r"^\{(\d+)\}: Put a \+1/\+1 counter on (?:this creature|~|"
        + re.escape(name)
        + r")\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("mana-put-p1p1", text),
        costs=[ManaCost(amount=ManaAmount(generic=int(m.group(1))))],
        effects=[
            AddCounterEffect(counter_type="p1p1", quantity=1, target="self")
        ],
    )


def pat_etb_with_counters_irrelevant(text: str, name: str) -> Ability | None:
    """X-counter ETB (Ballista/Triskelion): seed counters instead of casting X."""
    m = re.match(
        r"^This creature enters(?: the battlefield)? with "
        r"(?:X|three|\d+) \+1/\+1 counters? on it\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return _proof_irrelevant(text.strip().rstrip("."))


def pat_grant_lifelink_activated(text: str, name: str) -> Ability | None:
    """Heliod: {cost}: Another target creature gains lifelink until end of turn.

    Modeled as proof-irrelevant activation text; explore uses seed_grant_lifelink.
    """
    m = re.match(
        r"^(?:\{[^}]+\})+: Another target creature gains lifelink "
        r"until end of turn\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return _proof_irrelevant(text.strip().rstrip("."))


def pat_remove_counter_damage(text: str, name: str) -> Ability | None:
    m = re.match(
        r"^Remove a \+1/\+1 counter from (~|this permanent|this creature|"
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
            r"^Remove a \+1/\+1 counter from (~|this permanent|this creature): "
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
            # any_target: explorer defaults to opponent (Heliod); self-ping for undying.
            DealDamageEffect(amount=1, target="any_target"),
        ],
    )


def pat_etb_create_food(text: str, name: str) -> Ability | None:
    """Rosie ETB: When NAME enters, create a Food token."""
    short = name.split(" of ")[0].strip() if " of " in name else name
    name_alt = "|".join(
        re.escape(n) for n in dict.fromkeys([name, short, "this creature", "~"])
    )
    m = re.match(
        rf"^When (?:{name_alt}) enters(?: the battlefield)?, create a Food token\.?"
        rf"(?: \([^)]*\))?\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("etb-food", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="self",
        effects=[
            CreateTokenEffect(
                name="Food",
                power=0,
                toughness=0,
                quantity=1,
                is_creature=False,
                is_artifact=True,
            )
        ],
    )


def pat_create_token_put_p1p1_other(text: str, name: str) -> Ability | None:
    """Rosie: Whenever you create a token, put +1/+1 on another creature you control."""
    short = name.split(" of ")[0].strip() if " of " in name else name
    name_alt = "|".join(re.escape(n) for n in dict.fromkeys([name, short]))
    m = re.match(
        rf"^Whenever you create a token, put a \+1/\+1 counter on target creature "
        rf"you control other than (?:{name_alt})\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("create-token-p1p1", text),
        event=TriggerEvent.CREATE_TOKEN,
        filter="any",
        effects=[
            AddCounterEffect(
                counter_type="p1p1",
                quantity=1,
                target="target_other_creature",
            )
        ],
    )


def pat_counters_put_may_create_token(text: str, name: str) -> Ability | None:
    """Scurry Oak: when +1/+1 counters are put on this, may create a token."""
    short = name.split(" of ")[0].strip() if " of " in name else name
    name_alt = "|".join(
        re.escape(n) for n in dict.fromkeys([name, short, "this creature", "~"])
    )
    m = re.match(
        rf"^Whenever one or more \+1/\+1 counters are put on (?:{name_alt}), "
        rf"(?:you may )?create (?:a|one)(?: (\d+)/(\d+))? "
        rf"(?:(?:white|blue|black|red|green|colorless) )?"
        rf"(.+?) creature token\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    power = int(m.group(1) or 1)
    toughness = int(m.group(2) or 1)
    token_name = m.group(3).strip()
    # Combo-player-favorable: treat optional create as mandatory.
    return TriggeredAbility(
        ability_id=_ability_id("counters-create-token", text),
        event=TriggerEvent.COUNTER_ADDED,
        filter="self",
        effects=[
            CreateTokenEffect(
                name=token_name,
                power=power,
                toughness=toughness,
                quantity=1,
            )
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


_KEYWORD_ABILITIES = frozenset(
    {
        "flying",
        "flash",
        "haste",
        "vigilance",
        "trample",
        "lifelink",
        "deathtouch",
        "reach",
        "defender",
        "menace",
        "hexproof",
        "shroud",
        "first strike",
        "double strike",
        "indestructible",
        "ward",
    }
)


def _proof_irrelevant(text: str) -> ProofIrrelevantStatic:
    return ProofIrrelevantStatic(
        ability_id=_ability_id("proof-irrelevant", text),
        clause=text,
    )


def pat_cast_from_gy_if_zombie(text: str, name: str) -> Ability | None:
    """Gravecrawler-shaped: cast from GY while controlling a Zombie.

    Modeled as an activated GY→battlefield return. Mana cost is {B} for this
    curriculum family (Gravecrawler CMC); broaden deliberately with tests later.
    """
    m = re.match(
        r"^You may cast (?:this card|~|"
        + re.escape(name)
        + r") from your graveyard as long as you control a Zombie\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("cast-gy-zombie", text),
        costs=[ManaCost(amount=ManaAmount(black=1))],
        effects=[ReturnToBattlefieldEffect()],
        requires_zombie=True,
    )


def pat_proof_irrelevant_static(text: str, name: str) -> Ability | None:
    """Match Oracle clauses that do not participate in modeled loop proofs."""
    clause = text.strip().rstrip(".")
    if not clause:
        return None

    lowered = clause.lower()
    if lowered in _KEYWORD_ABILITIES:
        return _proof_irrelevant(clause)

    # Companion reminder / ability word block.
    if re.match(r"^Companion\b", clause, re.IGNORECASE):
        return _proof_irrelevant(clause)

    # Temporary "can't block" grant (Zirda activated effect as static leftover — skip activated).
    if re.match(
        r"^Target creature can't block this turn\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    words = [part.strip().lower().rstrip(",.") for part in clause.split() if part.strip()]
    if words and all(word in _KEYWORD_ABILITIES for word in words):
        return _proof_irrelevant(clause)

    # Keyword + reminder text (e.g. Lifelink (...)).
    kw_alt = "|".join(re.escape(k) for k in sorted(_KEYWORD_ABILITIES, key=len, reverse=True))
    if re.match(rf"^(?:{kw_alt})(?: \([^)]+\))?$", clause, re.IGNORECASE):
        return _proof_irrelevant(clause)

    if re.match(r"^Ward \{[^}]+\}(?: \([^)]+\))?$", clause, re.IGNORECASE):
        return _proof_irrelevant(clause)

    # Enchant line alone — not joined granted abilities ("Enchanted … has …").
    if re.match(r"^Enchant (?:target )?[A-Za-z][A-Za-z\s]*\.?$", clause, re.IGNORECASE):
        return _proof_irrelevant(clause)

    if re.match(r"^Equip (?:\{[^}]+\})+(?: \([^)]+\))?$", clause, re.IGNORECASE):
        return _proof_irrelevant(clause)

    if re.match(
        r"^Morph (?:\{[^}]+\})+(?: \([^)]+\))?\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^Umbra armor(?: \([^)]+\))?\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^Flash(?: \([^)]+\))?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^Devoid(?: \([^)]+\))?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^This land enters(?: the battlefield)? tapped\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^Evolve(?: \([^)]+\))?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^As this enchantment enters(?: the battlefield)?, choose a creature type\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^(?:\{[^}]+\})+: Creatures you control gain .+ until end of turn\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^(?:\{[^}]+\})+: Creatures you control get [+-]\d+/[+-]\d+ "
        r"until end of turn\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    # Static anthem (Warleader's Call): not modeled loop physics.
    if re.match(
        r"^Creatures you control get [+-]\d+/[+-]\d+\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    # Fateful hour / conditional life anthem (Thraben Doomsayer).
    if re.match(
        r"^(?:[A-Z][a-z]+(?: [a-z]+)? — )?"
        r"As long as you have \d+ or less life, "
        r"other creatures you control get [+-]\d+/[+-]\d+\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    # Theros god devotion (joined with Indestructible on one Scryfall line).
    if re.match(
        r"^Indestructible(?:\s+As long as your devotion to \w+ is less than \w+, "
        r".+ isn't a creature)?\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^As long as your devotion to \w+ is less than \w+, .+ isn't a creature\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^Creatures with power \d+ or less can't block "
        + re.escape(name)
        + r"(?:\.)?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^You may cast " + re.escape(name) + r" only from your graveyard\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(r"^This creature can't block\.?$", clause, re.IGNORECASE):
        return _proof_irrelevant(clause)

    if re.match(
        r"^This creature can't be blocked by creatures with power \d+ or less\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(r"^Activate only as a sorcery\.?$", clause, re.IGNORECASE):
        return _proof_irrelevant(clause)

    if re.match(
        r"^This (?:artifact|creature|permanent) doesn't untap during your untap step\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^Creatures don't untap during their controllers' untap steps\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(r"^You have no maximum hand size\.?$", clause, re.IGNORECASE):
        return _proof_irrelevant(clause)

    # Enchanted-creature keyword/pump riders (Pemmin's Aura class): not modeled
    # loop physics; keep them out of legal_steps so they do not drain mana.
    if re.match(
        r"^(?:\{[^}]+\})+: Enchanted creature gains .+ until end of turn\.?"
        r"(?:\s*\([^)]*\))?\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^(?:\{[^}]+\})+: Enchanted creature gets .+ until end of turn\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    return None


# Order matters: more specific patterns first; proof-irrelevant static last.
PATTERNS: list[Pattern] = [
    Pattern("tap_create_token_untap", pat_tap_create_token_untap),
    Pattern("tap_sac_token_make_two", pat_tap_sac_token_make_two),
    Pattern("enchanted_tap_create_token", pat_enchanted_tap_create_token),
    Pattern("tap_create_token", pat_tap_create_token),
    Pattern("tap_add_mana", pat_tap_add_mana),
    Pattern("mana_untap_enchanted", pat_mana_untap_enchanted),
    Pattern("mana_tap_enchanted", pat_mana_tap_enchanted),
    Pattern("mana_tap_gain_life", pat_mana_tap_gain_life),
    Pattern("mana_tap_untap_target", pat_mana_tap_untap_target),
    Pattern("mana_tap_tap_target", pat_mana_tap_tap_target),
    Pattern("mana_tap_draw", pat_mana_tap_draw),
    Pattern("mana_untap_self", pat_mana_untap_self),
    Pattern("cost_reduction", pat_cost_reduction),
    Pattern("zirda_cost_reduction", pat_zirda_cost_reduction),
    Pattern("cant_block_this_turn", pat_cant_block_this_turn),
    Pattern("put_m1m1_untap_self", pat_put_m1m1_untap_self),
    Pattern("vizier_m1m1_replacement", pat_vizier_m1m1_replacement),
    Pattern("etb_create_food", pat_etb_create_food),
    Pattern("create_token_put_p1p1_other", pat_create_token_put_p1p1_other),
    Pattern("counters_put_may_create_token", pat_counters_put_may_create_token),
    Pattern("etb_untap_target", pat_etb_untap_target),
    Pattern("sac_creature_add_mana", pat_sac_creature_add_mana),
    Pattern("sac_creature_outlet", pat_sac_creature_outlet),
    Pattern("sac_self", pat_sac_self),
    Pattern("return_from_gy", pat_return_from_gy),
    Pattern("cast_from_gy_if_zombie", pat_cast_from_gy_if_zombie),
    Pattern("dies_return_self", pat_dies_return_self),
    Pattern("dies_lose_life", pat_dies_lose_life),
    Pattern("gain_life_opponent_loses_that_much", pat_gain_life_opponent_loses_that_much),
    Pattern("gain_life_opponent_loses_fixed", pat_gain_life_opponent_loses_fixed),
    Pattern("opponent_lose_life_you_gain_that_much", pat_opponent_lose_life_you_gain_that_much),
    Pattern("etb_damage", pat_etb_damage),
    Pattern("etb_gain_life", pat_etb_gain_life),
    Pattern("gain_life_put_p1p1_target", pat_gain_life_put_p1p1_target),
    Pattern("gain_life_untap_self", pat_gain_life_untap_self),
    Pattern("mana_put_p1p1_self", pat_mana_put_p1p1_self),
    Pattern("etb_with_counters_irrelevant", pat_etb_with_counters_irrelevant),
    Pattern("grant_lifelink_activated", pat_grant_lifelink_activated),
    Pattern("remove_counter_damage", pat_remove_counter_damage),
    Pattern("put_p1p1_counter", pat_put_p1p1_counter),
    Pattern("exile_instead_of_gy", pat_exile_instead_of_gy),
    Pattern("proof_irrelevant_static", pat_proof_irrelevant_static),
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
