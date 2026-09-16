"""Deterministic Oracle ability patterns for gold_core families."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from mtg_loop_engine.semantics.enums import TriggerEvent, Zone
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
    FreeCastCreaturesByManaValue,
    GainLifeEffect,
    GrantLifelinkEffect,
    HybridManaCost,
    InstantGrantTapBounce,
    LoseLifeEffect,
    ManaAmount,
    ManaCost,
    PayLifeCost,
    BounceControlledCost,
    DiscardCost,
    MillEffect,
    MoveToZoneEffect,
    ProliferateEffect,
    RemoveCounterCost,
    RemoveCounterEffect,
    ReplacementAmplifyP1P1Counters,
    ReplacementDoubleTokens,
    ReplacementDoubleMill,
    ReplacementDoubleCounters,
    ReplacementDoubleLifeGain,
    ReplacementDoubleOpponentLifeLoss,
    ReplacementDoubleDraw,
    StaticCantGainLife,
    GrantActivatedAbility,
    ReplacementExileInsteadOfGraveyard,
    ReplacementMultiplyTapMana,
    ReplacementReduceM1M1Counters,
    ProofIrrelevantStatic,
    ReturnFromGraveyardToHandEffect,
    ReturnToBattlefieldEffect,
    SacrificeCost,
    TapCost,
    TapCreatureCost,
    TapArtifactCost,
    TapEffect,
    TriggeredAbility,
    UntapEffect,
    UntapSymbolCost,
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
    # Astral Cornucopia / Everflowing: {T}: Add {C} / any color for each charge counter.
    m_charge_c = re.match(
        r"^\{T\}: Add \{C\} for each charge counter on "
        r"(?:this artifact|~|"
        + re.escape(name)
        + r")\.?$",
        text,
        re.IGNORECASE,
    )
    if m_charge_c:
        return ActivatedAbility(
            ability_id=_ability_id("tap-mana-charge-c", text),
            costs=[TapCost()],
            effects=[AddManaEffect(equal_to_source_charge_counters="colorless")],
            is_mana_ability=True,
            uses_stack=False,
        )
    m_charge_any = re.match(
        r"^\{T\}: Choose a color\. Add one mana of that color for each charge "
        r"counter on (?:this artifact|~|"
        + re.escape(name)
        + r")\.?$",
        text,
        re.IGNORECASE,
    )
    if m_charge_any:
        return ActivatedAbility(
            ability_id=_ability_id("tap-mana-charge-any", text),
            costs=[TapCost()],
            effects=[AddManaEffect(equal_to_source_charge_counters="any_color")],
            is_mana_ability=True,
            uses_stack=False,
        )
    # M5 slice 9 — scaled tap mana (path-a).
    from mtg_loop_engine.semantics.enums import ManaScaleKind

    scaled_patterns: tuple[tuple[str, ManaScaleKind, str], ...] = (
        (
            r"^\{T\}: Add \{G\} for each creature you control\.?$",
            ManaScaleKind.CONTROLLED_CREATURES,
            "green",
        ),
        (
            r"^\{T\}: Add \{G\} for each Elf on the battlefield\.?$",
            ManaScaleKind.BATTLEFIELD_ELF,
            "green",
        ),
        (
            r"^\{T\}: Add X mana of any one color, where X is the number of "
            r"Elves on the battlefield\.?$",
            ManaScaleKind.BATTLEFIELD_ELF,
            "any_color",
        ),
        (
            r"^\{T\}: Add \{G\} for each Elf you control\.?$",
            ManaScaleKind.CONTROLLED_ELF,
            "green",
        ),
        (
            r"^\{T\}: Add \{G\} for each creature you control with defender\.?$",
            ManaScaleKind.CONTROLLED_DEFENDERS,
            "green",
        ),
        (
            r"^\{T\}: Add X mana of any one color, where X is the number of "
            r"enchantments you control\.?$",
            ManaScaleKind.CONTROLLED_ENCHANTMENTS,
            "any_color",
        ),
        (
            r"^\{T\}: Add X mana in any combination of colors, where X is the "
            r"number of creatures you control with defender\.?$",
            ManaScaleKind.CONTROLLED_DEFENDERS,
            "any_color",
        ),
        (
            r"^\{T\}: Add an amount of \{G\} equal to your devotion to green\."
            r"(?: \(Each \{G\} in the mana costs of permanents you control counts "
            r"toward your devotion to green\.\))?\.?$",
            ManaScaleKind.DEVOTION_GREEN,
            "green",
        ),
        (
            r"^Vivid — \{T\}: For each color among permanents you control, "
            r"add one mana of that color\.?$",
            ManaScaleKind.VIVID_PERMANENT_COLORS,
            "green",
        ),
    )
    for pattern, scale, color in scaled_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return ActivatedAbility(
                ability_id=_ability_id(f"tap-mana-scale-{scale.value}", text),
                costs=[TapCost()],
                effects=[
                    AddManaEffect(mana_scale=scale, scale_color=color)  # type: ignore[arg-type]
                ],
                is_mana_ability=True,
                uses_stack=False,
            )
    # M5 E01 — Metalcraft / Ferocious gated tap-mana; spend-only; hand-artifact scale.
    m_metalcraft = re.match(
        r"^(?:Metalcraft — )?\{T\}: Add one mana of any color\. "
        r"Activate only if you control three or more artifacts\.?$",
        text,
        re.IGNORECASE,
    )
    if m_metalcraft:
        return ActivatedAbility(
            ability_id=_ability_id("tap-mana-metalcraft", text),
            costs=[TapCost()],
            effects=[AddManaEffect(amount=ManaAmount(any_color=1))],
            is_mana_ability=True,
            uses_stack=False,
            requires_metalcraft=True,
        )
    m_ferocious = re.match(
        r"^(?:Ferocious — )?\{T\}: Add ((?:\{[^}]+\})+)\. "
        r"Activate only if you control a creature with power (\d+) or greater\.?$",
        text,
        re.IGNORECASE,
    )
    if m_ferocious:
        amount = _parse_mana_braces(m_ferocious.group(1))
        return ActivatedAbility(
            ability_id=_ability_id("tap-mana-ferocious", text),
            costs=[TapCost()],
            effects=[AddManaEffect(amount=amount)],
            is_mana_ability=True,
            uses_stack=False,
            requires_controlled_power_at_least=int(m_ferocious.group(2)),
        )
    m_spend = re.match(
        r"^\{T\}: Add ((?:\{[^}]+\})+)\. "
        r"Spend this mana only to activate abilities\.?$",
        text,
        re.IGNORECASE,
    )
    if m_spend:
        amount = _parse_mana_braces(m_spend.group(1))
        return ActivatedAbility(
            ability_id=_ability_id("tap-mana-activate-only", text),
            costs=[TapCost()],
            effects=[
                AddManaEffect(amount=amount, spend_only="activate_abilities")
            ],
            is_mana_ability=True,
            uses_stack=False,
        )
    m_metalworker = re.match(
        r"^\{T\}: Reveal any number of artifact cards in your hand\. "
        r"Add \{C\}\{C\} for each card revealed this way\.?$",
        text,
        re.IGNORECASE,
    )
    if m_metalworker:
        return ActivatedAbility(
            ability_id=_ability_id("tap-mana-hand-artifacts", text),
            costs=[TapCost()],
            effects=[
                AddManaEffect(
                    mana_scale=ManaScaleKind.HAND_ARTIFACTS,
                    scale_color="colorless",
                    scale_multiplier=2,
                )
            ],
            is_mana_ability=True,
            uses_stack=False,
        )
    return None


def pat_tap_two_creatures_add_mana(text: str, name: str) -> Ability | None:
    """Supportive Parents: Tap two untapped creatures you control: Add any color."""
    m = re.match(
        r"^Tap two untapped creatures you control: "
        r"Add one mana of any color\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("tap-two-add-mana", text),
        costs=[TapCreatureCost(allow_source=True, quantity=2)],
        effects=[AddManaEffect(amount=ManaAmount(any_color=1))],
        is_mana_ability=True,
        uses_stack=False,
    )


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
        r"^((?:\{[^}]+\}(?:,\s*)?)+): Draw (?:a card|(\d+) cards?|"
        r"(one|two|three|four|five|six|seven) cards?)\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    costs = _parse_activation_costs(m.group(1).rstrip(", "))
    if not costs:
        return None
    if m.group(2):
        amount = int(m.group(2))
    elif m.group(3):
        amount = _parse_count_word(m.group(3)) or 1
    else:
        amount = 1
    return ActivatedAbility(
        ability_id=_ability_id("tap-draw", text),
        costs=costs,
        effects=[DrawEffect(amount=amount)],
    )


def pat_tap_creature_subtype_draw(text: str, name: str) -> Ability | None:
    """Azami: tap an untapped Wizard you control: draw a card."""
    m = re.match(
        r"^Tap an untapped ([A-Za-z][A-Za-z '-]*) you control: Draw a card\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    subtype = m.group(1).strip()
    return ActivatedAbility(
        ability_id=_ability_id("tap-subtype-draw", text),
        costs=[TapCreatureCost(subtype=subtype, allow_source=True)],
        effects=[DrawEffect(amount=1)],
    )


def pat_tap_each_player_draw(text: str, name: str) -> Ability | None:
    """Temple Bell / Kwain (draw half): {T}: each player draws a card → you draw 1."""
    m = re.match(
        r"^\{T\}: Each player(?: may)? draw(?:s)? a card"
        r"(?:, then each player who drew a card this way gains 1 life)?\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("tap-each-draw", text),
        costs=[TapCost()],
        effects=[DrawEffect(amount=1)],
    )



def pat_untap_target_artifact(text: str, name: str) -> Ability | None:
    """Filigree Sages: {N}{U}: untap target artifact."""
    m = re.match(
        r"^((?:\{[^}]+\})+): Untap target artifact\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("untap-artifact", text),
        costs=[ManaCost(amount=_parse_mana_braces(m.group(1)))],
        effects=[UntapEffect(target="target_artifact")],
    )


def pat_remove_charge_add_mana(text: str, name: str) -> Ability | None:
    """Druids' Repository: Remove a charge counter: Add one mana of any color."""
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", text.strip()).strip()
    m = re.match(
        r"^Remove a charge counter from (?:this (?:enchantment|artifact)|~|"
        + re.escape(name)
        + r"): Add one mana of any color\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("remove-charge-mana", text),
        costs=[RemoveCounterCost(counter_type="charge", quantity=1, selector="self")],
        effects=[AddManaEffect(amount=ManaAmount(any_color=1))],
        is_mana_ability=True,
        uses_stack=False,
    )


def pat_attacks_untap_lands(text: str, name: str) -> Ability | None:
    """Bear Umbra grant / self: attacks → untap all lands you control."""
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", text.strip()).strip()
    # Aura grant form
    m_grant = re.match(
        r'^Enchanted creature gets [+-]\d+/[+-]\d+ and has '
        r'"Whenever this creature attacks, untap all lands you control\."\.?$',
        cleaned,
        re.IGNORECASE,
    )
    if m_grant:
        return TriggeredAbility(
            ability_id=_ability_id("attacks-untap-lands", text),
            event=TriggerEvent.ATTACKS,
            filter="controlled_creature",
            effects=[UntapEffect(target="controlled_lands")],
        )
    m_self = re.match(
        r"^Whenever (?:this creature|~|"
        + re.escape(name)
        + r") attacks, untap all lands(?: you control)?\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m_self:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("attacks-untap-lands-self", text),
        event=TriggerEvent.ATTACKS,
        filter="self",
        effects=[UntapEffect(target="controlled_lands")],
    )


def pat_attacks_damage_attacker(text: str, name: str) -> Ability | None:
    """Caltrops: Whenever a creature attacks, this deals N damage to it."""
    cleaned = _strip_ability_word(text)
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", cleaned).strip()
    short = name.split(",")[0].strip()
    name_alt = "|".join(
        re.escape(n) for n in dict.fromkeys([name, short, "this artifact", "~", "it"])
    )
    m = re.match(
        rf"^Whenever a creature attacks, (?:{name_alt}) deals (\d+) damage to it\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("attacks-damage-attacker", text),
        event=TriggerEvent.ATTACKS,
        filter="creature",
        effects=[
            DealDamageEffect(amount=int(m.group(1)), target="trigger_subject")
        ],
    )


def pat_attacks_draw(text: str, name: str) -> Ability | None:
    """Self-attacks → draw a card."""
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", text.strip()).strip()
    short = name.split(",")[0].strip()
    name_alt = "|".join(
        re.escape(n) for n in dict.fromkeys([name, short, "this creature", "~"])
    )
    m = re.match(
        rf"^Whenever (?:{name_alt}) attacks, draw a card\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("attacks-draw", text),
        event=TriggerEvent.ATTACKS,
        filter="self",
        effects=[DrawEffect(amount=1)],
    )


def pat_attacks_put_charge(text: str, name: str) -> Ability | None:
    """Druids' Repository: Whenever a creature you control attacks, put a charge counter."""
    cleaned = _strip_ability_word(text)
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", cleaned).strip()
    m = re.match(
        r"^Whenever a creature you control attacks, "
        r"put a charge counter on (?:this (?:enchantment|artifact)|~|"
        + re.escape(name)
        + r")\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("attacks-put-charge", text),
        event=TriggerEvent.ATTACKS,
        filter="controlled_creature",
        effects=[AddCounterEffect(counter_type="charge", quantity=1, target="self")],
    )


def pat_tap_put_charge_target_artifact(text: str, name: str) -> Ability | None:
    """Coretapper: {T}: Put a charge counter on target artifact."""
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", text.strip()).strip()
    m = re.match(
        r"^\{T\}: Put a charge counter on target artifact\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("tap-put-charge", text),
        costs=[TapCost()],
        effects=[
            AddCounterEffect(
                counter_type="charge", quantity=1, target="target_permanent"
            )
        ],
    )


def pat_sac_put_charge_target_artifact(text: str, name: str) -> Ability | None:
    """Coretapper: Sacrifice this creature: Put two charge counters on target artifact."""
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", text.strip()).strip()
    m = re.match(
        r"^Sacrifice (?:this creature|~|"
        + re.escape(name)
        + r"): Put (?:a|one|two|(\d+)) charge counters? on target artifact\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    raw = m.group(1)
    qty = int(raw) if raw else (2 if "two" in cleaned.casefold() else 1)
    return ActivatedAbility(
        ability_id=_ability_id("sac-put-charge", text),
        costs=[SacrificeCost(selector="self")],
        effects=[
            AddCounterEffect(
                counter_type="charge", quantity=qty, target="target_permanent"
            )
        ],
    )


def pat_tap_copy_creature_haste(text: str, name: str) -> Ability | None:
    """Kiki-Jiki: {T}: create token copy of target nonlegendary creature with haste."""
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", text.strip()).strip()
    # Drop end-step sacrifice rider (combo-favorable deferred).
    cleaned = re.sub(
        r"\s*Sacrifice it at the beginning of the next end step\.?$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\s*Exile that token at the beginning of the next end step\.?$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    m = re.match(
        r"^\{T\}: Create a token that's a copy of target nonlegendary creature "
        r"you control(?:, except it has haste)?\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("tap-copy-haste", text),
        costs=[TapCost()],
        effects=[CreateTokenEffect(copy_target=True, haste=True)],
    )


def pat_splinter_twin_grant(text: str, name: str) -> Ability | None:
    """Splinter Twin: enchanted creature has Kiki tap-copy."""
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", text.strip()).strip()
    m = re.match(
        r'^Enchanted creature has "\{T\}: Create a token that\'s a copy of this '
        r'creature, except it has haste\. Exile that token at the beginning of '
        r'the next end step\."\.?$',
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        # Alternate wording without exile rider on grant text
        m = re.match(
            r'^Enchanted creature has "\{T\}: Create a token that\'s a copy of '
            r'this creature, except it has haste\."\.?$',
            cleaned,
            re.IGNORECASE,
        )
    if not m:
        return None
    return GrantActivatedAbility(
        ability_id=_ability_id("grant-twin-copy", text),
        host_filter="enchanted_creature",
        costs=[TapCost()],
        effects=[CreateTokenEffect(copy_target=True, haste=True)],
    )


def pat_adapt(text: str, name: str) -> Ability | None:
    """Adapt N: if no +1/+1 counters, put N +1/+1 counters."""
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", text.strip()).strip()
    m = re.match(
        r"^((?:\{[^}]+\})+): Adapt (\d+)\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("adapt", text),
        costs=[ManaCost(amount=_parse_mana_braces(m.group(1)))],
        effects=[
            AddCounterEffect(
                counter_type="p1p1",
                quantity=int(m.group(2)),
                target="self",
                only_if_none=True,
            )
        ],
    )


def pat_p1p1_put_draw_discard(text: str, name: str) -> Ability | None:
    """Benthic Biomancer: +1/+1 put on this → draw then discard."""
    cleaned = _strip_ability_word(text)
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", cleaned).strip()
    short = name.split(",")[0].strip()
    name_alt = "|".join(
        re.escape(n) for n in dict.fromkeys([name, short, "this creature", "~"])
    )
    m = re.match(
        rf"^Whenever one or more \+1/\+1 counters are put on (?:{name_alt}), "
        rf"draw a card, then discard a card\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("p1p1-draw-discard", text),
        event=TriggerEvent.COUNTER_ADDED,
        filter="self",
        effects=[DrawEffect(amount=1)],  # discard abstracted as hand_you later optional
    )


def pat_p1p1_put_create_eldrazi_spawn(text: str, name: str) -> Ability | None:
    """Basking Broodscale: +1/+1 put → may create Eldrazi Spawn."""
    cleaned = _strip_ability_word(text)
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", cleaned).strip()
    short = name.split(",")[0].strip()
    name_alt = "|".join(
        re.escape(n) for n in dict.fromkeys([name, short, "this creature", "~"])
    )
    m = re.match(
        rf"^Whenever one or more \+1/\+1 counters are put on (?:{name_alt}), "
        rf"you may create a 0/1 colorless Eldrazi Spawn creature token"
        rf"(?: with .+)?\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("p1p1-eldrazi-spawn", text),
        event=TriggerEvent.COUNTER_ADDED,
        filter="self",
        effects=[
            CreateTokenEffect(
                name="Eldrazi Spawn",
                power=0,
                toughness=1,
                quantity=1,
                is_creature=True,
            )
        ],
    )


def pat_discard_untap_target(text: str, name: str) -> Ability | None:
    """Mind Over Matter: Discard a card: may tap or untap target permanent."""
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", text.strip()).strip()
    m = re.match(
        r"^Discard a card: You may tap or untap target "
        r"(?:artifact, creature, or land|permanent)\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("discard-untap", text),
        costs=[DiscardCost()],
        effects=[UntapEffect(target="target_permanent")],
    )


def pat_discard_add_mana(text: str, name: str) -> Ability | None:
    """Skirge Familiar: Discard a card: Add {B} (or other single brace)."""
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", text.strip()).strip()
    m = re.match(
        r"^Discard a card: Add ((?:\{[^}]+\})+)\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("discard-mana", text),
        costs=[DiscardCost()],
        effects=[AddManaEffect(amount=_parse_mana_braces(m.group(1)))],
    )


def pat_discard_trigger_damage(text: str, name: str) -> Ability | None:
    """Glint-Horn: Whenever you discard a card, deal N to each/target opponent."""
    cleaned = _strip_ability_word(text)
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", cleaned).strip()
    short = name.split(",")[0].strip()
    name_alt = "|".join(
        re.escape(n) for n in dict.fromkeys([name, short, "this creature", "~"])
    )
    m = re.match(
        rf"^Whenever you discard a card, (?:{name_alt}) deals (\d+) damage to "
        rf"(?:each|target) opponent\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("discard-damage", text),
        event=TriggerEvent.DISCARD,
        filter="any",
        effects=[DealDamageEffect(amount=int(m.group(1)), target="opponent")],
    )


def pat_discard_draw(text: str, name: str) -> Ability | None:
    """Glint-Horn: mana + discard → draw (attacking restriction ignored for combo)."""
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", text.strip()).strip()
    m = re.match(
        r"^((?:\{[^}]+\})+), Discard a card: Draw a card"
        r"(?:\. Activate only if this creature is attacking)?\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("discard-draw", text),
        costs=[
            ManaCost(amount=_parse_mana_braces(m.group(1))),
            DiscardCost(),
        ],
        effects=[DrawEffect(amount=1)],
    )


def pat_etb_untap_artifact_or_creature(text: str, name: str) -> Ability | None:
    """Corridor Monitor: ETB untap target artifact or creature you control."""
    m = re.match(
        r"^When (?:this creature|~|"
        + re.escape(name)
        + r") enters(?: the battlefield)?, "
        r"untap target artifact or creature you control\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("etb-untap-artifact-creature", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="self",
        effects=[UntapEffect(target="target_permanent")],
    )


def pat_tap_artifacts_untap_artifact(text: str, name: str) -> Ability | None:
    """Clock of Omens: tap two untapped artifacts: untap target artifact."""
    m = re.match(
        r"^Tap (one|two|three|\d+) untapped artifacts? you control: "
        r"Untap target artifact\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    qty = _parse_count_word(m.group(1)) or 1
    return ActivatedAbility(
        ability_id=_ability_id("tap-artifacts-untap", text),
        costs=[TapArtifactCost(quantity=qty, allow_source=True)],
        effects=[UntapEffect(target="target_artifact")],
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


def pat_power_artifact_cost_reduction(text: str, name: str) -> Ability | None:
    """Power Artifact: enchanted artifact activated abilities cost {N} less; floor 1."""
    m = re.match(
        r"^Enchanted artifact's activated abilities cost \{(\d+)\} less to activate\.?"
        r"(?:\s+This effect can't reduce the mana in that cost to less than one mana\.?)?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ContinuousCostReduction(
        ability_id=_ability_id("power-artifact-reduce", text),
        reduce_generic=int(m.group(1)),
        applies_to="enchanted_artifact_activated",
        min_mana_remaining=1,
    )


def pat_untap_mill_controller(text: str, name: str) -> Ability | None:
    """Mesmeric Orb: whenever a permanent becomes untapped, its controller mills."""
    m = re.match(
        r"^Whenever a permanent becomes untapped, "
        r"that permanent's controller mills (?:a card|(\d+) cards?)\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    amount = int(m.group(1)) if m.group(1) else 1
    return TriggeredAbility(
        ability_id=_ability_id("untap-mill", text),
        event=TriggerEvent.UNTAP,
        filter="any",
        effects=[MillEffect(amount=amount, who="you")],
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


def pat_replacement_multiply_tap_mana(text: str, name: str) -> Ability | None:
    """Mana Reflection / Nyxbloom: tap-for-mana produces 2× or 3×."""
    m = re.match(
        r"^If you tap a permanent for mana, it produces (twice|three times) "
        r"as much of that mana instead\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    multiplier = 2 if m.group(1).casefold() == "twice" else 3
    return ReplacementMultiplyTapMana(
        ability_id=_ability_id("multiply-tap-mana", text),
        multiplier=multiplier,
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


def pat_amplify_p1p1_replacement(text: str, name: str) -> Ability | None:
    """Kami (permanent) / Hardened Scales (creature): +1/+1 put amplify."""
    m = re.match(
        r"^If one or more \+1/\+1 counters would be put on a "
        r"(permanent|creature) you control, that many plus one \+1/\+1 counters "
        r"are put on that \1 instead\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    applies = (
        "creatures_you_control"
        if m.group(1).casefold() == "creature"
        else "permanents_you_control"
    )
    return ReplacementAmplifyP1P1Counters(
        ability_id=_ability_id("amplify-p1p1", text),
        plus=1,
        applies_to=applies,  # type: ignore[arg-type]
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
    # Hyrax Tower Scout: When this creature enters, untap target creature.
    m_hyrax = re.match(
        r"^When (?:this creature|~|"
        + re.escape(name)
        + r") enters(?: the battlefield)?, "
        r"untap target creature\.?$",
        text,
        re.IGNORECASE,
    )
    if m_hyrax:
        return TriggeredAbility(
            ability_id=_ability_id("etb-untap-target-creature", text),
            event=TriggerEvent.ENTER_BATTLEFIELD,
            filter="self",
            effects=[UntapEffect(target="target_creature")],
        )
    # Blasting Station: Whenever a creature enters, you may untap this artifact.
    m_may_self_art = re.match(
        r"^Whenever a creature enters(?: the battlefield)?, "
        r"you may untap (?:this artifact|~|"
        + re.escape(name)
        + r")\.?$",
        text,
        re.IGNORECASE,
    )
    if m_may_self_art:
        return TriggeredAbility(
            ability_id=_ability_id("etb-may-untap-self-artifact", text),
            event=TriggerEvent.ENTER_BATTLEFIELD,
            filter="creature",
            effects=[UntapEffect(target="self")],
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
    if m_self:
        return TriggeredAbility(
            ability_id=_ability_id("etb-untap-self", text),
            event=TriggerEvent.ENTER_BATTLEFIELD,
            filter="creature",
            effects=[UntapEffect(target="self")],
        )
    # Variant without "another" / with "you may".
    m_may_self = re.match(
        r"^Whenever (?:a|another) creature enters(?: the battlefield)?, "
        r"(?:you may )?untap (?:this creature|~|"
        + re.escape(name)
        + r")\.?$",
        text,
        re.IGNORECASE,
    )
    if not m_may_self:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("etb-untap-self", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="creature",
        effects=[UntapEffect(target="self")],
    )


def pat_warstorm_etb_power_damage(text: str, name: str) -> Ability | None:
    """Warstorm Surge: controlled creature ETB → it deals damage = its power."""
    cleaned = _strip_ability_word(text)
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", cleaned).strip()
    m = re.match(
        r"^Whenever a creature you control enters(?: the battlefield)?, "
        r"it deals damage equal to its power to any target\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("warstorm-etb-power", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="controlled_creature",
        effects=[
            DealDamageEffect(
                equal_to_trigger_subject_power=True, target="any_target"
            )
        ],
    )


def pat_landfall_create_token(text: str, name: str) -> Ability | None:
    """Sporemound-class: landfall → create a P/T … token."""
    cleaned = _strip_ability_word(text)
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", cleaned).strip()
    m = re.match(
        r"^Whenever a land you control enters(?: the battlefield)?, "
        r"create (?:a|one)(?: (\d+)/(\d+))? (.+?) creature token\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    power = int(m.group(1) or 1)
    toughness = int(m.group(2) or 1)
    token_name = m.group(3).strip()
    return TriggeredAbility(
        ability_id=_ability_id("landfall-create-token", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="controlled_land",
        effects=[
            CreateTokenEffect(
                name=token_name,
                power=power,
                toughness=toughness,
                quantity=1,
                is_creature=True,
            )
        ],
    )


def pat_artifact_etb_p1p1_target(text: str, name: str) -> Ability | None:
    """Yotian Dissident: artifact you control enters → +1/+1 on target creature."""
    cleaned = _strip_ability_word(text)
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", cleaned).strip()
    m = re.match(
        r"^Whenever an artifact you control enters(?: the battlefield)?, "
        r"put a \+1/\+1 counter on target creature you control\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("artifact-etb-p1p1", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="controlled_artifact",
        effects=[
            AddCounterEffect(
                counter_type="p1p1",
                quantity=1,
                target="target_permanent",
            )
        ],
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


def pat_mana_create_token(text: str, name: str) -> Ability | None:
    """Sliver Queen class: {N}: Create a P/T … creature token."""
    m = re.match(
        r"^\{(\d+)\}: Create (?:a|one)(?: (\d+)/(\d+))? (.+?) creature token\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    power = int(m.group(2) or 1)
    toughness = int(m.group(3) or 1)
    token_name = m.group(4).strip()
    return ActivatedAbility(
        ability_id=_ability_id("mana-token", text),
        costs=[ManaCost(amount=ManaAmount(generic=int(m.group(1))))],
        effects=[
            CreateTokenEffect(
                name=token_name, power=power, toughness=toughness, quantity=1
            )
        ],
    )


def pat_mana_untap_create_token(text: str, name: str) -> Ability | None:
    """Patrol Signaler class: {mana}, {Q}: create creature token."""
    m = re.match(
        r"^((?:\{[^}]+\})+), \{Q\}: Create (?:a|one)(?: (\d+)/(\d+))? (.+?) "
        r"creature token\.(?: \(\{Q\} is the untap symbol\.\))?\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    power = int(m.group(2) or 1)
    toughness = int(m.group(3) or 1)
    return ActivatedAbility(
        ability_id=_ability_id("mana-untap-token", text),
        costs=[
            ManaCost(amount=_parse_mana_braces(m.group(1))),
            UntapSymbolCost(source_self=True),
        ],
        effects=[
            CreateTokenEffect(
                name=m.group(4).strip(),
                power=power,
                toughness=toughness,
                quantity=1,
            )
        ],
    )


def pat_hybrid_remove_m1m1_pump(text: str, name: str) -> Ability | None:
    """Quillspike: {B/G}, remove -1/-1 from a creature you control; +N/+N until EOT irrelevant."""
    m = re.match(
        r"^\{([WUBRG])/([WUBRG])\}, Remove a -1/-1 counter from a creature you control: "
        r"This creature gets [+-]\d+/[+-]\d+ until end of turn\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    color_map = {
        "W": "white",
        "U": "blue",
        "B": "black",
        "R": "red",
        "G": "green",
    }
    c1 = color_map[m.group(1).upper()]
    c2 = color_map[m.group(2).upper()]
    if c1 == "green":
        colors = (c1, c2)
    elif c2 == "green":
        colors = (c2, c1)
    else:
        colors = (c1, c2)
    return ActivatedAbility(
        ability_id=_ability_id("hybrid-remove-m1m1", text),
        costs=[
            HybridManaCost(colors=colors),
            RemoveCounterCost(counter_type="m1m1", quantity=1),
        ],
        effects=[],
    )


def pat_equipped_untap_pump(text: str, name: str) -> Ability | None:
    """Umbral Mantle class: equipped creature pays {3}{Q}; +2/+2 is proof-irrelevant."""
    m = re.match(
        r'^Equipped creature has "\{3\}, \{Q\}: This creature gets \+2/\+2 until end of turn\."'
        r"(?: \(\{Q\} is the untap symbol\.\))?\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("equipped-untap-pump", text),
        costs=[
            ManaCost(amount=ManaAmount(generic=3)),
            UntapSymbolCost(source_self=False),
        ],
        effects=[],
    )


def pat_enchanted_tap_create_token(text: str, name: str) -> Ability | None:
    """Presence of Gond / Squirrel Nest: enchanted host has {T}: create token.

    Creature hosts (Gond) and land hosts (Nest) share CreateTokenEffect physics;
    ``TapCost.host`` selects which permanent may pay {T}.
    """
    m = re.match(
        r'^Enchanted (creature|land) has '
        r'"\{T\}: Create (?:a|one)(?: (\d+)/(\d+))? (.+?) creature token\."\.?$',
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    host_raw = m.group(1).casefold()
    host: Literal["creature", "land"] = "land" if host_raw == "land" else "creature"
    power = int(m.group(2) or 1)
    toughness = int(m.group(3) or 1)
    return ActivatedAbility(
        ability_id=_ability_id("enchanted-tap-token", text),
        costs=[TapCost(source_self=False, host=host)],
        effects=[
            CreateTokenEffect(
                name=m.group(4).strip(),
                power=power,
                toughness=toughness,
                quantity=1,
            )
        ],
    )


def pat_enchanted_gain_life_put_that_many_p1p1(text: str, name: str) -> Ability | None:
    """Light of Promise / Sunbond: enchanted creature gains life → that many p1p1."""
    m = re.match(
        r'^Enchanted creature has '
        r'"Whenever you gain life, put that many \+1/\+1 counters on this creature\."\.?$',
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("enchanted-gain-life-p1p1", text),
        event=TriggerEvent.GAIN_LIFE,
        filter="any",
        effects=[
            AddCounterEffect(
                counter_type="p1p1",
                quantity=1,
                target="enchanted_creature",
                amount_from_trigger=True,
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


def pat_dies_gain_life_equal_toughness(text: str, name: str) -> Ability | None:
    """South Wind Avatar: another creature dies → gain life = its toughness."""
    m = re.match(
        r"^Whenever another creature you control dies, "
        r"you gain life equal to its toughness\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("dies-gain-toughness", text),
        event=TriggerEvent.DIES,
        filter="other_controlled_creature",
        effects=[GainLifeEffect(amount_from_trigger=True)],
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


def pat_opponent_lose_life_mill(text: str, name: str) -> Ability | None:
    """Mindcrank class: opponent loses life → mill."""
    m = re.match(
        r"^Whenever an opponent loses life, "
        r"(?:that player )?mills? (?:a |one )?card\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("loss-to-mill", text),
        event=TriggerEvent.OPPONENT_LOSE_LIFE,
        filter="any",
        effects=[MillEffect(amount=1, who="opponent")],
    )


def pat_card_to_opponent_gy_lose_life(text: str, name: str) -> Ability | None:
    """Bloodchief Ascension granted trigger."""
    m = re.match(
        r"^Whenever a card is put into an opponent's graveyard from anywhere, "
        r"that player loses (\d+) life\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("gy-drain", text),
        event=TriggerEvent.CARD_TO_OPPONENT_GRAVEYARD,
        filter="any",
        effects=[LoseLifeEffect(amount=int(m.group(1)), who="opponent")],
    )


def pat_enchantments_have_graveyard_drain(text: str, name: str) -> Ability | None:
    """Static grant: enchantments you control have graveyard-drain trigger."""
    m = re.match(
        r'^Enchantments you control have "(?P<inner>[^"]+)"\.?$',
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return pat_card_to_opponent_gy_lose_life(m.group("inner"), name)


def _strip_ability_word(text: str) -> str:
    """Drop leading ability-word / named-ability prefix (… — )."""
    return re.sub(r"^.+?—\s*", "", text.strip(), count=1)


def pat_cast_bounce_target_permanent(text: str, name: str) -> Ability | None:
    """Tidespout Tyrant: whenever you cast a spell, bounce target permanent."""
    cleaned = _strip_ability_word(text)
    m = re.match(
        r"^Whenever you cast a spell, return target permanent to (?:its|their) owner's hand\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("cast-bounce-permanent", text),
        event=TriggerEvent.CAST,
        filter="any",
        effects=[MoveToZoneEffect(zone=Zone.HAND, target="target_permanent")],
    )


def pat_etb_if_cast_half_life_drain(text: str, name: str) -> Ability | None:
    """Shard of the Nightbringer: ETB if cast → opponent loses half life; you gain that much."""
    cleaned = _strip_ability_word(text)
    m = re.match(
        r"^When (?:this creature|~|"
        + re.escape(name)
        + r") enters(?: the battlefield)?, if you cast it, "
        r"target opponent loses half their life, rounded up\. "
        r"You gain life equal to the life lost this way\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("etb-cast-half-drain", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="self",
        intervening_if="cast",
        effects=[
            LoseLifeEffect(who="opponent", half_life_rounded_up=True),
            GainLifeEffect(amount_from_trigger=True),
        ],
    )


def pat_etb_or_attacks_create_token(text: str, name: str) -> Ability | None:
    """Squirrel Girl: enters or attacks → create token (ETB modeled; attacks not)."""
    cleaned = _strip_ability_word(text)
    short = name.split(",")[0].strip() if "," in name else name
    name_alt = "|".join(
        re.escape(n) for n in dict.fromkeys([name, short, "this creature", "~"])
    )
    m = re.match(
        rf"^Whenever (?:{name_alt}) enters or attacks, "
        rf"create (?:a|one)(?: (\d+)/(\d+))? "
        rf"(?:(?:white|blue|black|red|green|colorless) )?"
        rf"(.+?) creature token\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    power = int(m.group(1) or 1)
    toughness = int(m.group(2) or 1)
    token_name = m.group(3).strip()
    return TriggeredAbility(
        ability_id=_ability_id("etb-create-token", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="self",
        effects=[
            CreateTokenEffect(
                name=token_name, power=power, toughness=toughness, quantity=1
            )
        ],
    )


def pat_mana_create_tokens_equal_subtype(text: str, name: str) -> Ability | None:
    """Squirrel Girl / Krenko: create X tokens equal to controlled subtype count."""
    cleaned = _strip_ability_word(text)
    # {T}: Create X …
    m_tap = re.match(
        r"^\{T\}: Create X(?: (\d+)/(\d+))? "
        r"(?:(?:white|blue|black|red|green|colorless) )?"
        r"(.+?) creature tokens?, where X is the number of (.+?) you control\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m_tap:
        power = int(m_tap.group(1) or 1)
        toughness = int(m_tap.group(2) or 1)
        token_name = m_tap.group(3).strip()
        subtype_phrase = m_tap.group(4).strip()
        if subtype_phrase.casefold() in {
            token_name.casefold(),
            f"{token_name}s".casefold(),
        }:
            subtype = token_name
        else:
            subtype = (
                subtype_phrase.rstrip("s")
                if subtype_phrase.endswith("s")
                else subtype_phrase
            )
        return ActivatedAbility(
            ability_id=_ability_id("tap-tokens-eq-subtype", text),
            costs=[TapCost()],
            effects=[
                CreateTokenEffect(
                    name=token_name,
                    power=power,
                    toughness=toughness,
                    quantity=1,
                    quantity_equal_to_controlled_subtype=subtype,
                )
            ],
            is_mana_ability=False,
            uses_stack=True,
        )
    m = re.match(
        r"^((?:\{[^}]+\})+): Create X(?: (\d+)/(\d+))? "
        r"(?:(?:white|blue|black|red|green|colorless) )?"
        r"(.+?) creature tokens?, where X is the number of (.+?) you control\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    cost = _parse_mana_braces(m.group(1))
    if cost.total() <= 0:
        return None
    power = int(m.group(2) or 1)
    toughness = int(m.group(3) or 1)
    token_name = m.group(4).strip()
    subtype_phrase = m.group(5).strip()
    # Prefer printed token name as subtype when phrase is its English plural.
    if subtype_phrase.casefold() in {
        token_name.casefold(),
        f"{token_name}s".casefold(),
    }:
        subtype = token_name
    else:
        subtype = subtype_phrase.rstrip("s") if subtype_phrase.endswith("s") else subtype_phrase
    return ActivatedAbility(
        ability_id=_ability_id("mana-tokens-eq-subtype", text),
        costs=[ManaCost(amount=cost)],
        effects=[
            CreateTokenEffect(
                name=token_name,
                power=power,
                toughness=toughness,
                quantity=1,
                quantity_equal_to_controlled_subtype=subtype,
            )
        ],
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
    filt = (
        "other_controlled_creature"
        if re.match(r"^Whenever another ", cleaned, re.IGNORECASE)
        else "creature"
    )
    if re.search(r"creature you control", cleaned, re.IGNORECASE) and filt == "creature":
        filt = "controlled_creature"
    return TriggeredAbility(
        ability_id=_ability_id("etb-damage", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter=filt,
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


def pat_gain_life_put_p1p1_each_controlled(text: str, name: str) -> Ability | None:
    """Archangel of Thune: Whenever you gain life, +1/+1 on each creature you control."""
    m = re.match(
        r"^Whenever you gain life, put a \+1/\+1 counter on each creature you control\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("gain-life-p1p1-each", text),
        event=TriggerEvent.GAIN_LIFE,
        filter="any",
        effects=[
            AddCounterEffect(
                counter_type="p1p1",
                quantity=1,
                target="each_controlled_creature",
            )
        ],
    )


def pat_etb_put_p1p1_each_controlled(text: str, name: str) -> Ability | None:
    """Cathars' Crusade: creature you control ETB → +1/+1 on each creature you control."""
    m = re.match(
        r"^Whenever a creature you control enters(?: the battlefield)?, "
        r"put a \+1/\+1 counter on each creature you control\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("etb-p1p1-each", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="controlled_creature",
        effects=[
            AddCounterEffect(
                counter_type="p1p1",
                quantity=1,
                target="each_controlled_creature",
            )
        ],
    )


def pat_etb_other_human_put_p1p1_self(text: str, name: str) -> Ability | None:
    """Heronblade Elite: another Human you control ETB → +1/+1 on this creature."""
    m = re.match(
        r"^Whenever another Human you control enters(?: the battlefield)?, "
        r"put a \+1/\+1 counter on (?:this creature|~|"
        + re.escape(name)
        + r")\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("etb-human-p1p1-self", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="other_controlled_human",
        effects=[
            AddCounterEffect(counter_type="p1p1", quantity=1, target="self")
        ],
    )


def pat_etb_other_green_put_p1p1_target(text: str, name: str) -> Ability | None:
    """Ivy Lane Denizen: another green creature ETB → +1/+1 on target creature."""
    m = re.match(
        r"^Whenever another green creature you control enters(?: the battlefield)?, "
        r"put a \+1/\+1 counter on target creature\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("etb-green-p1p1-target", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="other_controlled_green",
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

    Product path uses this paid activation (setup once). ``seed_grant_lifelink``
    remains a physics stand-in only — quarantined from ORACLE_EXACT VERIFIED.
    """
    m = re.match(
        r"^((?:\{[^}]+\})+): Another target creature gains lifelink "
        r"until end of turn\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("grant-lifelink", text),
        costs=[ManaCost(amount=_parse_mana_braces(m.group(1)))],
        effects=[GrantLifelinkEffect(target="target_other_creature")],
    )


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


def pat_etb_bounce_controlled_creature(text: str, name: str) -> Ability | None:
    """Shrieking Drake / Whitemane Lion: ETB return a controlled creature to hand."""
    m = re.match(
        r"^When (?:this creature|~|"
        + re.escape(name)
        + r") enters(?: the battlefield)?, "
        r"return a creature you control to (?:its|their) owner's hand\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("etb-bounce", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="self",
        effects=[MoveToZoneEffect(zone=Zone.HAND, target="controlled_creature")],
    )


def pat_etb_bounce_controlled_creature_gw(text: str, name: str) -> Ability | None:
    """Fleetfoot Panther: ETB bounce a green or white creature you control."""
    m = re.match(
        r"^When (?:this creature|~|"
        + re.escape(name)
        + r") enters(?: the battlefield)?, "
        r"return a green or white creature you control to (?:its|their) owner's hand\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("etb-bounce-gw", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="self",
        effects=[
            MoveToZoneEffect(
                zone=Zone.HAND, target="controlled_creature_green_or_white"
            )
        ],
    )


def pat_etb_bounce_controlled_permanent(text: str, name: str) -> Ability | None:
    """Dream Stalker: ETB bounce a permanent you control."""
    m = re.match(
        r"^When (?:this creature|~|"
        + re.escape(name)
        + r") enters(?: the battlefield)?, "
        r"return a permanent you control to (?:its|their) owner's hand\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("etb-bounce-perm", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="self",
        effects=[MoveToZoneEffect(zone=Zone.HAND, target="controlled_permanent")],
    )


def pat_etb_bounce_controlled_nonland(text: str, name: str) -> Ability | None:
    """Ancestral Statue: ETB bounce a nonland permanent you control."""
    m = re.match(
        r"^When (?:this creature|~|"
        + re.escape(name)
        + r") enters(?: the battlefield)?, "
        r"return a nonland permanent you control to (?:its|their) owner's hand\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("etb-bounce-nonland", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="self",
        effects=[MoveToZoneEffect(zone=Zone.HAND, target="controlled_nonland")],
    )


def pat_activated_bounce_other_creature(text: str, name: str) -> Ability | None:
    """Temur Sabertooth: paid bounce another creature; indestructible rider is proof-irrelevant."""
    m = re.match(
        r"^((?:\{[^}]+\})+): You may return another creature you control to "
        r"(?:its|their) owner's hand\. If you do, "
        r"(?:this creature|~|"
        + re.escape(name)
        + r") gains indestructible until end of turn\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("activated-bounce-other", text),
        costs=[ManaCost(amount=_parse_mana_braces(m.group(1)))],
        effects=[MoveToZoneEffect(zone=Zone.HAND, target="other_controlled_creature")],
    )


def pat_etb_bounce_sharing_type(text: str, name: str) -> Ability | None:
    """Cloudstone Curio: nonartifact ETB may bounce another permanent sharing a type."""
    m = re.match(
        r"^Whenever a nonartifact permanent you control enters(?: the battlefield)?, "
        r"you may return another permanent you control that shares a permanent type "
        r"with it to (?:its|their) owner's hand\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("etb-bounce-share-type", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="controlled_nonartifact",
        effects=[
            MoveToZoneEffect(zone=Zone.HAND, target="other_controlled_sharing_type")
        ],
    )


def pat_etb_mana_sharing_creature_type(text: str, name: str) -> Ability | None:
    """Mana Echoes: creature ETB → add {C} × controlled creatures sharing a type."""
    from mtg_loop_engine.semantics.enums import ManaScaleKind

    m = re.match(
        r"^Whenever a creature enters(?: the battlefield)?, "
        r"you may add an amount of \{C\} equal to the number of creatures you control "
        r"that share a creature type with it\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("etb-mana-share-type", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="creature",
        effects=[
            AddManaEffect(
                mana_scale=ManaScaleKind.CONTROLLED_SHARING_CREATURE_TYPE,
                scale_color="colorless",
            )
        ],
    )


def pat_earthcraft_tap_untap_basic(text: str, name: str) -> Ability | None:
    """Earthcraft: tap an untapped creature you control: untap target basic land."""
    m = re.match(
        r"^Tap an untapped creature you control: Untap target basic land\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("earthcraft-untap-basic", text),
        costs=[TapCreatureCost()],
        effects=[UntapEffect(target="target_basic_land")],
    )


def pat_aluren_free_cast(text: str, name: str) -> Ability | None:
    """Aluren: cast creatures with mana value ≤ 3 without paying mana."""
    m = re.match(
        r"^Any player may cast creature spells with mana value (\d+) or less "
        r"without paying their mana costs(?: and as though they had flash)?\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return FreeCastCreaturesByManaValue(
        ability_id=_ability_id("free-cast-mv", text),
        max_mana_value=int(m.group(1)),
    )


def pat_instant_grant_tap_bounce(text: str, name: str) -> Ability | None:
    """Banishing Knack / Retraction Helix: Instant grants {T}: bounce nonland."""
    m = re.match(
        r'^Until end of turn, target creature gains '
        r'"\{T\}: Return target nonland permanent to (?:its|their) owner\'s hand\."\.?$',
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return InstantGrantTapBounce(
        ability_id=_ability_id("instant-grant-tap-bounce", text),
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


def pat_counters_put_damage_opponent(text: str, name: str) -> Ability | None:
    """Shalai and Hallar / All Will Be One: counters put → that much damage."""
    short = name.split(",")[0].strip() if "," in name else name
    name_alt = "|".join(
        re.escape(n) for n in dict.fromkeys([name, short, "this creature", "~"])
    )
    m = re.match(
        rf"^Whenever one or more \+1/\+1 counters are put on a creature you control, "
        rf"(?:{name_alt}) deals that much damage to (?:target |each )?opponent\.?$",
        text,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("counters-damage-opponent", text),
            event=TriggerEvent.COUNTER_ADDED,
            filter="controlled_creature",
            effects=[
                DealDamageEffect(amount=1, target="opponent", amount_from_trigger=True)
            ],
        )
    m = re.match(
        r"^Whenever you put one or more counters on a permanent or player, "
        r"(?:this enchantment|~|"
        + re.escape(name)
        + r"|it) deals that much damage to "
        r"(?:target opponent|target opponent, creature an opponent controls, "
        r"or planeswalker an opponent controls)\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("counters-damage-any", text),
        event=TriggerEvent.COUNTER_ADDED,
        filter="any",
        effects=[
            DealDamageEffect(amount=1, target="opponent", amount_from_trigger=True)
        ],
    )


def pat_m1m1_put_create_token(text: str, name: str) -> Ability | None:
    """Flourishing Defenses: -1/-1 put → create token."""
    m = re.match(
        r"^Whenever a -1/-1 counter is put on a creature, "
        r"(?:you may )?create a (\d+)/(\d+) "
        r"(?:(?:white|blue|black|red|green|colorless) )?"
        r"(.+?) creature token\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("m1m1-put-token", text),
        event=TriggerEvent.COUNTER_ADDED,
        filter="creature",
        effects=[
            CreateTokenEffect(
                name=m.group(3).strip(),
                power=int(m.group(1)),
                toughness=int(m.group(2)),
                quantity=1,
                is_creature=True,
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








def _parse_count_word(raw: str) -> int | None:
    raw = (raw or "").strip().lower()
    if raw.isdigit():
        return int(raw)
    return {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
    }.get(raw)









def pat_etb_return_from_gy_to_hand(text: str, name: str) -> Ability | None:
    """Eternal Witness / Archaeomancer: ETB return from GY to hand."""
    cleaned = _strip_ability_word(text)
    short = name.split(",")[0].strip()
    name_alt = "|".join(
        re.escape(n) for n in dict.fromkeys([name, short, "this creature", "~"])
    )
    m = re.match(
        rf"^When (?:{name_alt}) enters(?: the battlefield)?, "
        rf"(?:you may )?return target card from your graveyard to your hand\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("etb-witness", text),
            event=TriggerEvent.ENTER_BATTLEFIELD,
            filter="self",
            effects=[ReturnFromGraveyardToHandEffect(selector="any")],
        )
    m = re.match(
        rf"^When (?:{name_alt}) enters(?: the battlefield)?, "
        rf"return target instant or sorcery card from your graveyard to your hand\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("etb-archaeomancer", text),
            event=TriggerEvent.ENTER_BATTLEFIELD,
            filter="self",
            effects=[ReturnFromGraveyardToHandEffect(selector="instant_or_sorcery")],
        )
    return None


def pat_gy_to_hand_activated(text: str, name: str) -> Ability | None:
    """Auriok Salvagers: paid return artifact MV≤1 from GY to hand."""
    m = re.match(
        r"^((?:\{[^}]+\})+): Return target artifact card with mana value 1 or less "
        r"from your graveyard to your hand\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("salvagers", text),
        costs=[ManaCost(amount=_parse_mana_braces(m.group(1)))],
        effects=[ReturnFromGraveyardToHandEffect(selector="artifact_mv_leq_1")],
        uses_stack=True,
        is_mana_ability=False,
    )


def pat_dies_to_hand(text: str, name: str) -> Ability | None:
    """Enduring Renewal: creature BF→GY → hand."""
    m = re.match(
        r"^Whenever a creature is put into your graveyard from the battlefield, "
        r"return it to your hand\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("renewal", text),
        event=TriggerEvent.DIES,
        filter="controlled_creature",
        effects=[MoveToZoneEffect(zone=Zone.HAND, target="trigger_subject")],
    )


def pat_scaled_mill(text: str, name: str) -> Ability | None:
    """E17: GY-count mill, life-loss mill, Bruvac double mill."""
    cleaned = _strip_ability_word(text)
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", cleaned).strip()

    m = re.match(
        r"^\{(\d+)\}, \{T\}: Target player mills X cards, where X is the number of cards in that player's graveyard\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return ActivatedAbility(
            ability_id=_ability_id("keening-mill", text),
            costs=[
                ManaCost(amount=ManaAmount(generic=int(m.group(1)))),
                TapCost(),
            ],
            effects=[MillEffect(who="opponent", amount_from_opponent_graveyard=True)],
            uses_stack=True,
            is_mana_ability=False,
        )

    m = re.match(
        r"^Whenever an opponent loses life, that player mills that many cards\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("mindcrank-mill", text),
            event=TriggerEvent.OPPONENT_LOSE_LIFE,
            filter="any",
            effects=[MillEffect(who="opponent", amount_from_trigger=True)],
        )

    m = re.match(
        r"^If an opponent would mill one or more cards, they mill twice that many cards instead\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return ReplacementDoubleMill(
            ability_id=_ability_id("bruvac-double-mill", text),
            multiplier=2,
        )

    return None


def pat_sac_outlet_payoffs(text: str, name: str) -> Ability | None:
    """E16: sac outlet → damage / mill / mana / draw."""
    cleaned = _strip_ability_word(text)
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", cleaned).strip()
    short = name.split(",")[0].strip()
    name_alt = "|".join(re.escape(n) for n in dict.fromkeys([name, short, "this creature", "this artifact", "this enchantment", "~"]))

    m = re.match(
        rf"^Sacrifice a creature: (?:{name_alt}) deals (\d+) damage to any target\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return ActivatedAbility(
            ability_id=_ability_id("sac-dmg", text),
            costs=[SacrificeCost(selector="creature_controlled")],
            effects=[DealDamageEffect(amount=int(m.group(1)), target="any_target")],
            uses_stack=True,
            is_mana_ability=False,
        )

    m = re.match(
        r"^\{T\}, Sacrifice a creature: (?:"
        + name_alt
        + r") deals (\d+) damage to any target\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return ActivatedAbility(
            ability_id=_ability_id("tap-sac-dmg", text),
            costs=[TapCost(), SacrificeCost(selector="creature_controlled")],
            effects=[DealDamageEffect(amount=int(m.group(1)), target="any_target")],
            uses_stack=True,
            is_mana_ability=False,
        )

    m = re.match(
        r"^Sacrifice a creature: Target player mills cards equal to the sacrificed creature's power\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return ActivatedAbility(
            ability_id=_ability_id("sac-mill-power", text),
            costs=[SacrificeCost(selector="creature_controlled")],
            effects=[MillEffect(who="opponent", amount_from_sacrificed_power=True)],
            uses_stack=True,
            is_mana_ability=False,
        )

    m = re.match(
        rf"^Sacrifice (?:this creature|{name_alt}): Add ((?:\{{[^}}]+\}})+)\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return ActivatedAbility(
            ability_id=_ability_id("sac-self-mana", text),
            costs=[SacrificeCost(selector="self")],
            effects=[AddManaEffect(amount=_parse_mana_braces(m.group(1)))],
            is_mana_ability=True,
            uses_stack=False,
        )

    m = re.match(
        r"^\{T\}, Sacrifice another black creature: Draw a card\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return ActivatedAbility(
            ability_id=_ability_id("tap-sac-black-draw", text),
            costs=[TapCost(), SacrificeCost(selector="creature_controlled")],
            effects=[DrawEffect(amount=1)],
            uses_stack=True,
            is_mana_ability=False,
        )

    return None


def pat_dies_trigger_payoffs(text: str, name: str) -> Ability | None:
    """E14: dies → treasure / untap / spirit / drain."""
    cleaned = _strip_ability_word(text)
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", cleaned).strip()
    short = name.split(",")[0].strip()
    name_alt = "|".join(
        re.escape(n) for n in dict.fromkeys([name, short, "this creature", "~"])
    )

    m = re.match(
        r"^Whenever another creature you control dies, create a [Tt]reasure token\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("dies-treasure", text),
            event=TriggerEvent.DIES,
            filter="other_controlled_creature",
            effects=[
                CreateTokenEffect(
                    name="Treasure",
                    power=0,
                    toughness=0,
                    quantity=1,
                    is_creature=False,
                    is_artifact=True,
                    treasure=True,
                )
            ],
        )

    m = re.match(
        rf"^Whenever a creature dies, untap (?:{name_alt})\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("dies-untap-self", text),
            event=TriggerEvent.DIES,
            filter="creature",
            effects=[UntapEffect(target="self")],
        )

    m = re.match(
        r"^Whenever another black creature you control dies, "
        r"create a 1/1 white Spirit creature token with flying\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("dies-spirit", text),
            event=TriggerEvent.DIES,
            filter="other_controlled_black_creature",
            effects=[
                CreateTokenEffect(
                    name="Spirit",
                    power=1,
                    toughness=1,
                    quantity=1,
                    is_creature=True,
                )
            ],
        )

    m = re.match(
        rf"^Whenever (?:this creature or another creature|{name_alt} or another creature) dies, "
        rf"target player loses (\d+) life and you gain (\d+) life\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("dies-artist", text),
            event=TriggerEvent.DIES,
            filter="creature",
            effects=[
                LoseLifeEffect(who="opponent", amount=int(m.group(1))),
                GainLifeEffect(amount=int(m.group(2))),
            ],
        )

    m = re.match(
        r"^Whenever this creature or another nontoken creature you control dies, "
        r"you may create a 0/1 colorless Eldrazi Spawn creature token\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("dies-spawn", text),
            event=TriggerEvent.DIES,
            filter="controlled_nontoken_creature",
            effects=[
                CreateTokenEffect(
                    name="Eldrazi Spawn",
                    power=0,
                    toughness=1,
                    quantity=1,
                    is_creature=True,
                )
            ],
        )

    return None


def pat_self_etb_scaled(text: str, name: str) -> Ability | None:
    """E13a: self-ETB damage/life/draw scaled by power, devotion, or artifacts."""
    cleaned = _strip_ability_word(text)
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", cleaned).strip()
    short = name.split(",")[0].strip()
    name_alt = "|".join(
        re.escape(n) for n in dict.fromkeys([name, short, "this creature", "it", "~"])
    )

    m = re.match(
        rf"^When (?:{name_alt}) enters(?: the battlefield)?, "
        rf"(?:{name_alt}) deals damage equal to its power to any target\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("etb-power-damage", text),
            event=TriggerEvent.ENTER_BATTLEFIELD,
            filter="self",
            effects=[DealDamageEffect(equal_to_source_power=True, target="any_target")],
        )

    m = re.match(
        rf"^When (?:{name_alt}) enters(?: the battlefield)?, "
        rf"(?:{name_alt}) deals damage to each opponent equal to your devotion to red\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("etb-devotion-red-damage", text),
            event=TriggerEvent.ENTER_BATTLEFIELD,
            filter="self",
            effects=[DealDamageEffect(equal_to_devotion="red", target="opponent")],
        )

    m = re.match(
        rf"^When (?:{name_alt}) enters(?: the battlefield)?, "
        rf"each opponent loses X life, where X is your devotion to black\. "
        rf"You gain life equal to the life lost this way\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("etb-gary", text),
            event=TriggerEvent.ENTER_BATTLEFIELD,
            filter="self",
            effects=[
                LoseLifeEffect(who="opponent", equal_to_devotion="black"),
                GainLifeEffect(amount_from_trigger=True),
            ],
        )

    m = re.match(
        rf"^When (?:{name_alt}) enters(?: the battlefield)?, "
        rf"draw a card for each artifact you control\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("etb-draw-artifacts", text),
            event=TriggerEvent.ENTER_BATTLEFIELD,
            filter="self",
            effects=[DrawEffect(equal_to_controlled_artifacts=True)],
        )

    return None


def pat_cast_trigger_effects(text: str, name: str) -> Ability | None:
    """E12: parameterized whenever-you-cast → mana / life / counters / damage."""
    cleaned = _strip_ability_word(text)
    short = name.split(",")[0].strip()
    name_alt = "|".join(re.escape(n) for n in dict.fromkeys([name, short, "this creature", "~"]))

    m = re.match(
        r"^Whenever you cast a spell, add \{R\}\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("cast-add-r", text),
            event=TriggerEvent.CAST,
            filter="any",
            effects=[AddManaEffect(amount=ManaAmount(red=1))],
        )

    m = re.match(
        r"^Whenever you cast a colorless spell, you gain (\d+) life\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("cast-colorless-life", text),
            event=TriggerEvent.CAST,
            filter="cast_colorless",
            effects=[GainLifeEffect(amount=int(m.group(1)))],
        )

    m = re.match(
        rf"^Whenever you cast a creature spell, put a \+1/\+1 counter on (?:{name_alt})\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("cast-creature-p1p1", text),
            event=TriggerEvent.CAST,
            filter="cast_creature",
            effects=[AddCounterEffect(counter_type="p1p1", quantity=1, target="self")],
        )

    m = re.match(
        r"^Whenever you cast a red spell, if (?:this creature|~) has fewer than three \+1/\+1 counters on it, put a \+1/\+1 counter on (?:this creature|it|~)\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("cast-red-p1p1-cap3", text),
            event=TriggerEvent.CAST,
            filter="cast_red",
            intervening_if="fewer_than_three_p1p1",
            effects=[AddCounterEffect(counter_type="p1p1", quantity=1, target="self")],
        )

    m = re.match(
        rf"^Whenever you cast a noncreature spell, put a \+1/\+1 counter on (?:{name_alt}) and it deals (\d+) damage to each opponent\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("cast-noncreature-p1p1-dmg", text),
            event=TriggerEvent.CAST,
            filter="cast_noncreature",
            effects=[
                AddCounterEffect(counter_type="p1p1", quantity=1, target="self"),
                DealDamageEffect(amount=int(m.group(1)), target="opponent"),
            ],
        )

    m = re.match(
        r"^Whenever you cast an instant or sorcery spell, (?:this creature|~) deals (\d+) damage to each opponent\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        # Instant/sorcery casts are not yet in cast_from_hand; keep pattern for COMPLETE
        # of cards whose other clauses are covered, and for future cast ops.
        return TriggeredAbility(
            ability_id=_ability_id("cast-instant-dmg", text),
            event=TriggerEvent.CAST,
            filter="cast_noncreature",
            effects=[DealDamageEffect(amount=int(m.group(1)), target="opponent")],
        )

    return None


def pat_scaled_mana_remainders(text: str, name: str) -> Ability | None:
    """E11: swamp-count / greatest power-toughness / drawn / entered-this-turn mana."""
    from mtg_loop_engine.semantics.enums import ManaScaleKind

    cleaned = _strip_ability_word(text)
    # Magus of the Coffers
    m = re.match(
        r"^\{(\d+)\}, \{T\}: Add \{B\} for each Swamp you control\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return ActivatedAbility(
            ability_id=_ability_id("swamp-mana", text),
            costs=[
                ManaCost(amount=ManaAmount(generic=int(m.group(1)))),
                TapCost(),
            ],
            effects=[
                AddManaEffect(
                    mana_scale=ManaScaleKind.CONTROLLED_SWAMPS,
                    scale_color="black",
                )
            ],
            is_mana_ability=True,
            uses_stack=False,
        )
    # Bighorner / Legend: greatest power → G or any
    m = re.match(
        r"^\{T\}: Add an amount of \{G\} equal to the greatest power among creatures you control\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return ActivatedAbility(
            ability_id=_ability_id("greatest-power-g", text),
            costs=[TapCost()],
            effects=[
                AddManaEffect(
                    mana_scale=ManaScaleKind.GREATEST_POWER_CONTROLLED,
                    scale_color="green",
                )
            ],
            is_mana_ability=True,
            uses_stack=False,
        )
    m = re.match(
        r"^\{T\}: Add X mana of any one color, where X is the greatest power among creatures you control\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return ActivatedAbility(
            ability_id=_ability_id("greatest-power-any", text),
            costs=[TapCost()],
            effects=[
                AddManaEffect(
                    mana_scale=ManaScaleKind.GREATEST_POWER_CONTROLLED,
                    scale_color="any_color",
                )
            ],
            is_mana_ability=True,
            uses_stack=False,
        )
    m = re.match(
        r"^\{G\}, \{T\}: Add X mana in any combination of colors, where X is the greatest power among creatures you control\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        # Model as any_color pool equal to greatest power (combo-favorable).
        return ActivatedAbility(
            ability_id=_ability_id("selvala-power", text),
            costs=[ManaCost(amount=ManaAmount(green=1)), TapCost()],
            effects=[
                AddManaEffect(
                    mana_scale=ManaScaleKind.GREATEST_POWER_CONTROLLED,
                    scale_color="any_color",
                )
            ],
            is_mana_ability=True,
            uses_stack=False,
        )
    m = re.match(
        r"^\{T\}: Add X mana of any one color, where X is the greatest toughness among other creatures you control\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return ActivatedAbility(
            ability_id=_ability_id("greatest-tough-other", text),
            costs=[TapCost()],
            effects=[
                AddManaEffect(
                    mana_scale=ManaScaleKind.GREATEST_TOUGHNESS_OTHER,
                    scale_color="any_color",
                )
            ],
            is_mana_ability=True,
            uses_stack=False,
        )
    m = re.match(
        r"^\{T\}: Add \{C\} for each card you've drawn this turn\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return ActivatedAbility(
            ability_id=_ability_id("drawn-mana", text),
            costs=[TapCost()],
            effects=[
                AddManaEffect(
                    mana_scale=ManaScaleKind.CARDS_DRAWN_THIS_TURN,
                    scale_color="colorless",
                )
            ],
            is_mana_ability=True,
            uses_stack=False,
        )
    m = re.match(
        r"^\{T\}: Add an amount of \{R\} equal to the greatest power among creatures you control that entered this turn\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if m:
        return ActivatedAbility(
            ability_id=_ability_id("entered-power-r", text),
            costs=[TapCost()],
            effects=[
                AddManaEffect(
                    mana_scale=ManaScaleKind.GREATEST_POWER_ENTERED_THIS_TURN,
                    scale_color="red",
                )
            ],
            is_mana_ability=True,
            uses_stack=False,
        )
    return None


def pat_etb_untap_up_to_lands(text: str, name: str) -> Ability | None:
    """Palinchron / Peregrine Drake / Cloud of Faeries: ETB untap up to N lands."""
    cleaned = _strip_ability_word(text)
    short = name.split(",")[0].strip()
    name_alt = "|".join(
        re.escape(n) for n in dict.fromkeys([name, short, "this creature", "~"])
    )
    m = re.match(
        rf"^When (?:{name_alt}) enters(?: the battlefield)?, "
        rf"untap up to (\d+|one|two|three|four|five|six|seven) lands?\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    qty = _parse_count_word(m.group(1))
    if qty is None:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("etb-untap-lands", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="self",
        effects=[UntapEffect(target="controlled_lands", quantity=qty)],
    )


def pat_tap_untap_n_lands(text: str, name: str) -> Ability | None:
    """Argothian Elder / Ley Weaver: {T}: Untap two target lands."""
    m = re.match(
        r"^\{T\}: Untap (?:up to )?(\d+|one|two|three|four|five|six|seven) target lands?\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    qty = _parse_count_word(m.group(1))
    if qty is None:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("tap-untap-lands", text),
        costs=[TapCost()],
        effects=[UntapEffect(target="controlled_lands", quantity=qty)],
        uses_stack=False,
        is_mana_ability=False,
    )


def pat_tap_untap_target_land(text: str, name: str) -> Ability | None:
    """Krosan Restorer: {T}: Untap target land."""
    m = re.match(r"^\{T\}: Untap target land\.?$", text, re.IGNORECASE)
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("tap-untap-land", text),
        costs=[TapCost()],
        effects=[UntapEffect(target="controlled_lands", quantity=1)],
        uses_stack=False,
        is_mana_ability=False,
    )


def pat_bounce_self_activated(text: str, name: str) -> Ability | None:
    """Palinchron: paid return self to hand."""
    short = name.split(",")[0].strip()
    name_alt = "|".join(
        re.escape(n) for n in dict.fromkeys([name, short, "this creature", "~"])
    )
    m = re.match(
        rf"^(\{{[^}}]+\}}(?:\{{[^}}]+\}})*): Return (?:{name_alt}) to (?:its|their) owner's hand\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    amount = _parse_mana_braces(m.group(1))
    return ActivatedAbility(
        ability_id=_ability_id("bounce-self", text),
        costs=[ManaCost(amount=amount)],
        effects=[MoveToZoneEffect(zone=Zone.HAND, target="self")],
        uses_stack=True,
        is_mana_ability=False,
    )


def pat_cast_gain_life_per_spell(text: str, name: str) -> Ability | None:
    """Aetherflux: cast → gain 1 life per spell cast this turn."""
    cleaned = _strip_ability_word(text)
    m = re.match(
        r"^Whenever you cast a spell, you gain 1 life for each spell you've cast this turn\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("cast-life-per-spell", text),
        event=TriggerEvent.CAST,
        filter="any",
        effects=[GainLifeEffect(equal_to_spells_cast_this_turn=True)],
    )


def pat_pay_life_damage(text: str, name: str) -> Ability | None:
    """Aetherflux: Pay N life: deals N damage to any target."""
    cleaned = _strip_ability_word(text)
    m = re.match(
        r"^Pay (\d+) life: (?:This (?:artifact|creature)|~|"
        + re.escape(name)
        + r"|Aetherflux Reservoir) deals (\d+) damage to any target\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    pay = int(m.group(1))
    dmg = int(m.group(2))
    return ActivatedAbility(
        ability_id=_ability_id("pay-life-damage", text),
        costs=[PayLifeCost(amount=pay)],
        effects=[DealDamageEffect(amount=dmg, target="any_target")],
        uses_stack=True,
        is_mana_ability=False,
    )


def pat_attacks_half_mill(text: str, name: str) -> Ability | None:
    """Fleet Swallower / Terisian: attacks → mill half library."""
    short = name.split(",")[0].strip()
    name_alt = "|".join(
        re.escape(n) for n in dict.fromkeys([name, short, "this creature", "~"])
    )
    m = re.match(
        rf"^Whenever (?:{name_alt}|this creature) attacks, "
        rf"(?:target player|defending player) mills half their library, "
        rf"rounded (up|down)\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("attacks-half-mill", text),
        event=TriggerEvent.ATTACKS,
        filter="self",
        effects=[
            MillEffect(who="opponent", half_library=m.group(1).lower())  # type: ignore[arg-type]
        ],
    )


def pat_spell_half_mill(text: str, name: str) -> Ability | None:
    """Traumatize-class spell text compiled as a once-style activated stand-in is out of scope;
    match only the mill clause for permanent-attached wordings / curriculum sorcery bodies.
    """
    m = re.match(
        r"^(?:Target player|Target opponent) mills half their library, rounded (up|down)\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    # Model as activated {0} for curriculum COMPLETE of the mill clause alone.
    return ActivatedAbility(
        ability_id=_ability_id("half-mill", text),
        costs=[],
        effects=[
            MillEffect(who="opponent", half_library=m.group(1).lower())  # type: ignore[arg-type]
        ],
        uses_stack=True,
        is_mana_ability=False,
        once_per_turn=True,
    )


def pat_grant_activated(text: str, name: str) -> Ability | None:
    """Cryptolith Rite / Basal Sliver / Resplendent Mentor grants."""
    m = re.match(
        r'^Creatures you control have "\{T\}: Add one mana of any color\."?$',
        text,
        re.IGNORECASE,
    )
    if m:
        return GrantActivatedAbility(
            ability_id=_ability_id("grant-tap-any-mana", text),
            host_filter="creatures_you_control",
            costs=[TapCost()],
            effects=[AddManaEffect(amount=ManaAmount(any_color=1))],
            is_mana_ability=True,
            uses_stack=False,
        )
    m = re.match(
        r'^All [Ss]livers have "Sacrifice this permanent: Add ((?:\{[^}]+\})+)\."?$',
        text,
        re.IGNORECASE,
    )
    if m:
        amount = _parse_mana_braces(m.group(1))
        return GrantActivatedAbility(
            ability_id=_ability_id("grant-sac-mana", text),
            host_filter="slivers_you_control",
            costs=[SacrificeCost(selector="self")],
            effects=[AddManaEffect(amount=amount)],
            is_mana_ability=True,
            uses_stack=False,
        )
    m = re.match(
        r'^White creatures you control have "\{T\}: You gain (\d+) life\."?$',
        text,
        re.IGNORECASE,
    )
    if m:
        return GrantActivatedAbility(
            ability_id=_ability_id("grant-tap-gain-life", text),
            host_filter="white_creatures_you_control",
            costs=[TapCost()],
            effects=[GainLifeEffect(amount=int(m.group(1)))],
            is_mana_ability=False,
            uses_stack=True,
        )
    return None


def pat_draw_trigger_effect(text: str, name: str) -> Ability | None:
    """Whenever you draw a card → damage / life / mill / counters / lose life."""
    short = name.split(",")[0].strip()
    name_alt = "|".join(
        re.escape(n) for n in dict.fromkeys([name, short, "this creature", "~"])
    )
    m = re.match(
        rf"^Whenever you draw a card, (?:{name_alt}) deals (\d+) damage to any target\.?$",
        text,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("draw-damage", text),
            event=TriggerEvent.DRAW,
            filter="any",
            effects=[DealDamageEffect(amount=int(m.group(1)), target="any_target")],
        )
    m = re.match(
        r"^Whenever you draw a card, you gain (\d+) life\.?$",
        text,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("draw-gain-life", text),
            event=TriggerEvent.DRAW,
            filter="any",
            effects=[GainLifeEffect(amount=int(m.group(1)))],
        )
    m = re.match(
        r"^Whenever you draw a card, each opponent loses (\d+) life\.?$",
        text,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("draw-opp-lose-life", text),
            event=TriggerEvent.DRAW,
            filter="any",
            effects=[LoseLifeEffect(who="opponent", amount=int(m.group(1)))],
        )
    m = re.match(
        r"^Whenever you draw a card, target opponent loses (\d+) life and you gain (\d+) life\.?$",
        text,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("draw-drain", text),
            event=TriggerEvent.DRAW,
            filter="any",
            effects=[
                LoseLifeEffect(who="opponent", amount=int(m.group(1))),
                GainLifeEffect(amount=int(m.group(2))),
            ],
        )
    m = re.match(
        r"^Whenever you draw a card, each opponent mills (?:(\d+)|two|three) cards?\.?$",
        text,
        re.IGNORECASE,
    )
    if m:
        raw = (m.group(1) or "").lower()
        if raw.isdigit():
            amt = int(raw)
        elif "three" in text.lower():
            amt = 3
        else:
            amt = 2
        return TriggeredAbility(
            ability_id=_ability_id("draw-mill", text),
            event=TriggerEvent.DRAW,
            filter="any",
            effects=[MillEffect(amount=amt, who="opponent")],
        )
    m = re.match(
        rf"^Whenever you draw a card, put a \+1/\+1 counter on (?:{name_alt})(?: and you gain (\d+) life)?\.?$",
        text,
        re.IGNORECASE,
    )
    if m:
        effects: list = [AddCounterEffect(counter_type="p1p1", quantity=1, target="self")]
        if m.group(1):
            effects.append(GainLifeEffect(amount=int(m.group(1))))
        return TriggeredAbility(
            ability_id=_ability_id("draw-p1p1-self", text),
            event=TriggerEvent.DRAW,
            filter="any",
            effects=effects,
        )
    m = re.match(
        r"^Whenever you draw a card, put a \+1/\+1 counter on target creature(?: you control)?\.?$",
        text,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("draw-p1p1", text),
            event=TriggerEvent.DRAW,
            filter="any",
            effects=[
                AddCounterEffect(
                    counter_type="p1p1", quantity=1, target="target_other_creature"
                )
            ],
        )
    return None


def pat_curiosity_draw(text: str, name: str) -> Ability | None:
    """Curiosity family: enchanted creature damages opponent → may draw."""
    m = re.match(
        r"^Whenever enchanted creature deals damage to an opponent, "
        r"you may draw a card\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("curiosity-draw", text),
        event=TriggerEvent.DAMAGE_OPPONENT,
        filter="controlled_creature",
        effects=[DrawEffect(amount=1)],
    )


def pat_damage_opponent_create_treasures(text: str, name: str) -> Ability | None:
    """Old Gnawbone / Grim Hireling: damage opponent → Treasure(s)."""
    m = re.match(
        r"^Whenever a creature you control deals combat damage to a player, "
        r"create that many Treasure tokens\.?$",
        text,
        re.IGNORECASE,
    )
    if m:
        return TriggeredAbility(
            ability_id=_ability_id("combat-damage-treasures", text),
            event=TriggerEvent.DAMAGE_OPPONENT,
            filter="controlled_creature",
            effects=[
                CreateTokenEffect(
                    name="Treasure",
                    power=0,
                    toughness=0,
                    quantity=1,
                    quantity_from_trigger=True,
                    is_creature=False,
                    is_artifact=True,
                    treasure=True,
                )
            ],
        )
    m = re.match(
        r"^Whenever one or more creatures you control deal combat damage to a player, "
        r"create (two|one|\d+) Treasure tokens?\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    qty = _parse_count_word(m.group(1)) or 1
    return TriggeredAbility(
        ability_id=_ability_id("combat-damage-fixed-treasures", text),
        event=TriggerEvent.DAMAGE_OPPONENT,
        filter="controlled_creature",
        effects=[
            CreateTokenEffect(
                name="Treasure",
                power=0,
                toughness=0,
                quantity=qty,
                is_creature=False,
                is_artifact=True,
                treasure=True,
            )
        ],
    )


def pat_dealt_damage_create_treasures(text: str, name: str) -> Ability | None:
    """Smaug: noncombat damage → that many Treasures."""
    short = name.split(",")[0].strip()
    first = short.split()[0]
    name_alt = "|".join(
        re.escape(n) for n in dict.fromkeys([name, short, first, "this creature", "~"])
    )
    m = re.match(
        rf"^Whenever (?:{name_alt}) is dealt noncombat damage, "
        rf"create that many Treasure tokens\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("dealt-damage-treasures", text),
        event=TriggerEvent.DEALT_DAMAGE,
        filter="self",
        effects=[
            CreateTokenEffect(
                name="Treasure",
                power=0,
                toughness=0,
                quantity=1,
                quantity_from_trigger=True,
                is_creature=False,
                is_artifact=True,
                treasure=True,
            )
        ],
    )


def pat_dealt_damage_reflect(text: str, name: str) -> Ability | None:
    """Spitemare / Reckoner class: dealt damage → that much damage elsewhere."""
    short = name.split("//")[0].strip()
    short = short.split(",")[0].strip()
    name_alt = "|".join(
        re.escape(n) for n in dict.fromkeys([name, short, "this creature", "~"])
    )
    m = re.match(
        rf"^(?:Enrage — )?Whenever (?:{name_alt}|this creature) is dealt damage, "
        rf"(?:it|(?:{name_alt})) deals that much damage to "
        rf"(any target|target opponent|each player|each opponent)\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    dest = m.group(m.lastindex).lower()
    if dest in {"any target"}:
        target = "any_target"
    elif dest in {"each player"}:
        target = "each_player"
    else:
        target = "opponent"
    return TriggeredAbility(
        ability_id=_ability_id("dealt-damage-reflect", text),
        event=TriggerEvent.DEALT_DAMAGE,
        filter="self",
        effects=[
            DealDamageEffect(amount=1, target=target, amount_from_trigger=True)  # type: ignore[arg-type]
        ],
    )


def pat_dealt_damage_gain_life(text: str, name: str) -> Ability | None:
    """Metropolis Reformer: dealt damage → gain that much life."""
    short = name.split(",")[0].strip()
    name_alt = "|".join(
        re.escape(n) for n in dict.fromkeys([name, short, "this creature", "~"])
    )
    m = re.match(
        rf"^Whenever (?:{name_alt}|this creature) is dealt damage, "
        rf"you gain that much life\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("dealt-damage-gain-life", text),
        event=TriggerEvent.DEALT_DAMAGE,
        filter="self",
        effects=[GainLifeEffect(amount=1, amount_from_trigger=True)],
    )


def pat_replacement_double_tokens(text: str, name: str) -> Ability | None:
    """Parallel Lives / Anointed Procession / Primal Vigor token half."""
    m = re.match(
        r"^If an effect would create one or more tokens under your control, "
        r"it creates twice that many of those tokens instead\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        m = re.match(
            r"^If one or more tokens would be created, "
            r"twice that many of those tokens are created instead\.?$",
            text,
            re.IGNORECASE,
        )
    if not m:
        m = re.match(
            r"^If one or more tokens would be created under your control, "
            r"twice that many of those tokens are created instead\.?$",
            text,
            re.IGNORECASE,
        )
    if not m:
        return None
    return ReplacementDoubleTokens(
        ability_id=_ability_id("double-tokens", text),
        multiplier=2,
    )


def pat_etb_create_eldrazi_tokens(text: str, name: str) -> Ability | None:
    """Brood Monitor / Emrakul's Hatcher: ETB create N Eldrazi Spawn/Scion."""
    m = re.match(
        r"^When (?:this creature|~|"
        + re.escape(name)
        + r") enters(?: the battlefield)?, create "
        r"(one|two|three|\d+) "
        r"(\d+)/(\d+) colorless Eldrazi (Spawn|Scion) creature tokens?\.?"
        r"(?: They have \"[^\"]+\"\.?)?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    qty = _parse_count_word(m.group(1))
    if qty is None:
        return None
    kind = m.group(4).title()
    return TriggeredAbility(
        ability_id=_ability_id("etb-eldrazi-tokens", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="self",
        effects=[
            CreateTokenEffect(
                name=f"Eldrazi {kind}",
                power=int(m.group(2)),
                toughness=int(m.group(3)),
                quantity=qty,
                is_creature=True,
            )
        ],
    )


def pat_mana_create_eldrazi_tokens(text: str, name: str) -> Ability | None:
    """Spawnsire: {N}: create two Eldrazi Spawn."""
    m = re.match(
        r"^\{(\d+)\}: Create (one|two|three|\d+) "
        r"(\d+)/(\d+) colorless Eldrazi (Spawn|Scion) creature tokens?\.?"
        r"(?: They have \"[^\"]+\"\.?)?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    qty = _parse_count_word(m.group(2))
    if qty is None:
        return None
    kind = m.group(5).title()
    return ActivatedAbility(
        ability_id=_ability_id("mana-eldrazi-tokens", text),
        costs=[ManaCost(amount=ManaAmount(generic=int(m.group(1))))],
        effects=[
            CreateTokenEffect(
                name=f"Eldrazi {kind}",
                power=int(m.group(3)),
                toughness=int(m.group(4)),
                quantity=qty,
                is_creature=True,
            )
        ],
    )


def pat_enchantment_etb_create_cat(text: str, name: str) -> Ability | None:
    """Ajani's Chosen: enchantment ETB → 2/2 Cat (Aura attach rider ignored)."""
    m = re.match(
        r"^Whenever an enchantment you control enters(?: the battlefield)?, "
        r"create a (\d+)/(\d+) white Cat creature token\.?"
        r"(?: If that enchantment is an Aura,.*)?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("enchantment-etb-cat", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="controlled_enchantment",
        effects=[
            CreateTokenEffect(
                name="Cat",
                power=int(m.group(1)),
                toughness=int(m.group(2)),
                quantity=1,
                is_creature=True,
            )
        ],
    )


def pat_replacement_double_counters(text: str, name: str) -> Ability | None:
    """Doubling Season (all counters) / Primal Vigor (+1/+1 only)."""
    m = re.match(
        r"^If an effect would put one or more counters on a permanent you control, "
        r"it puts twice that many of those counters on that permanent instead\.?$",
        text,
        re.IGNORECASE,
    )
    if m:
        return ReplacementDoubleCounters(
            ability_id=_ability_id("double-counters", text),
            multiplier=2,
            applies_to="permanents_you_control",
            only_p1p1=False,
        )
    m = re.match(
        r"^If one or more \+1/\+1 counters would be put on a "
        r"(permanent|creature)(?: you control)?, "
        r"twice that many \+1/\+1 counters are put on that \1 instead\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    applies = (
        "creatures_you_control"
        if m.group(1).casefold() == "creature"
        else "permanents_you_control"
    )
    return ReplacementDoubleCounters(
        ability_id=_ability_id("double-counters-p1p1", text),
        multiplier=2,
        applies_to=applies,  # type: ignore[arg-type]
        only_p1p1=True,
    )


def pat_replacement_double_life_gain(text: str, name: str) -> Ability | None:
    """Alhammarret's Archive: if you would gain life, gain twice that much instead."""
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", text.strip()).strip()
    m = re.match(
        r"^If you would gain life, you gain twice that much life instead\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ReplacementDoubleLifeGain(
        ability_id=_ability_id("double-life-gain", text),
        multiplier=2,
    )


def pat_replacement_double_opponent_life_loss(text: str, name: str) -> Ability | None:
    """Bloodletter: opponent life loss is doubled (during your turn)."""
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", text.strip()).strip()
    m = re.match(
        r"^If an opponent would lose life(?: during your turn)?, "
        r"they lose twice that much life instead\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ReplacementDoubleOpponentLifeLoss(
        ability_id=_ability_id("double-opp-life-loss", text),
        multiplier=2,
        during_your_turn_only="during your turn" in cleaned.casefold(),
    )


def pat_replacement_double_draw(text: str, name: str) -> Ability | None:
    """Alhammarret's Archive draw half (combo: all draws double)."""
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", text.strip()).strip()
    m = re.match(
        r"^If you would draw a card(?: except the first one you draw in each of "
        r"your draw steps)?, draw two cards instead\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ReplacementDoubleDraw(
        ability_id=_ability_id("double-draw", text),
        multiplier=2,
    )


def pat_static_cant_gain_life(text: str, name: str) -> Ability | None:
    """Everlasting Torment / Archfiend / Grievous Wound can't-gain statics."""
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", text.strip()).strip()
    m = re.match(
        r"^(Players|Your opponents|Opponents|Enchanted player) can't gain life\.?$",
        cleaned,
        re.IGNORECASE,
    )
    if not m:
        return None
    who_raw = m.group(1).casefold()
    if who_raw.startswith("player"):
        who = "players"
    elif "enchanted" in who_raw:
        who = "opponents"  # combo model: enchanted is the opponent
    else:
        who = "opponents"
    return StaticCantGainLife(
        ability_id=_ability_id("cant-gain-life", text),
        who=who,  # type: ignore[arg-type]
    )


def pat_proliferate_activated(text: str, name: str) -> Ability | None:
    """Viral Drake / Lulu: paid Proliferate."""
    m = re.match(
        r"^((?:\{[^}]+\})+): Proliferate\.?(?: \([^)]*\))?\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("proliferate", text),
        costs=[ManaCost(amount=_parse_mana_braces(m.group(1)))],
        effects=[ProliferateEffect()],
    )


def pat_bounce_cost_untap_creature(text: str, name: str) -> Ability | None:
    """Quirion Ranger / Wirewood Symbiote: bounce Forest/Elf → untap creature."""
    m = re.match(
        r"^Return (?:a|an) (Forest|Elf) you control to (?:its|their) owner's hand: "
        r"Untap target creature\.(?: Activate only once each turn\.)?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    kind = m.group(1).casefold()
    selector = "forest_controlled" if kind == "forest" else "elf_controlled"
    once = "activate only once each turn" in text.casefold()
    return ActivatedAbility(
        ability_id=_ability_id("bounce-cost-untap", text),
        costs=[BounceControlledCost(selector=selector)],  # type: ignore[arg-type]
        effects=[UntapEffect(target="target_permanent")],
        once_per_turn=once,
    )


def pat_bounce_land_create_illusion(text: str, name: str) -> Ability | None:
    """Meloku: {1}, return a land → Illusion token."""
    m = re.match(
        r"^((?:\{[^}]+\})+), Return a land you control to (?:its|their) owner's hand: "
        r"Create a 1/1 blue Illusion creature token with flying\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("bounce-land-token", text),
        costs=[
            ManaCost(amount=_parse_mana_braces(m.group(1))),
            BounceControlledCost(selector="land_controlled"),
        ],
        effects=[
            CreateTokenEffect(
                name="Illusion",
                power=1,
                toughness=1,
                quantity=1,
                is_creature=True,
            )
        ],
    )


def pat_activated_bounce_controlled_creature(text: str, name: str) -> Ability | None:
    """Chulane: {3}, {T}: return target creature you control to hand."""
    m = re.match(
        r"^((?:\{[^}]+\})+), \{T\}: Return target creature you control to "
        r"(?:its|their) owner's hand\.?$",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    return ActivatedAbility(
        ability_id=_ability_id("activated-bounce-controlled", text),
        costs=[ManaCost(amount=_parse_mana_braces(m.group(1))), TapCost()],
        effects=[MoveToZoneEffect(zone=Zone.HAND, target="controlled_creature")],
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

    if re.match(
        r"^At the beginning of each end step\b",
        clause,
        re.IGNORECASE,
    ):
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

    # Infect reminder (Viral Drake): damage-as-counters not modeled; proliferate is.
    if re.match(r"^Infect(?: \([^)]+\))?$", clause, re.IGNORECASE):
        return _proof_irrelevant(clause)
    # Soft-wrap join: "Flying Infect (...)" when Infect lacked a splitter.
    if re.match(
        r"^(?:Flying )?Infect(?: \([^)]+\))?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(r"^Ward \{[^}]+\}(?: \([^)]+\))?$", clause, re.IGNORECASE):
        return _proof_irrelevant(clause)

    if re.match(
        r"^Eternalize (?:\{[^}]+\})+(?: \([^)]*\))?$",
        clause,
        re.IGNORECASE,
    ):
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
        r"^Cycling (?:\{[^}]+\})+(?: \([^)]*\))?\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^Partner(?: \([^)]*\))?\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^Persist(?: \([^)]*\))?\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^Creatures you control have haste\.?(?: \([^)]*\))?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^Until end of turn, you don't lose this mana as steps and phases end\.?",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^Colorless creatures you control get [+-]\d+/[+-]\d+\.?$",
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
        r"^Warp (?:\{[^}]+\})+(?: \([^)]*\))?\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^Annihilator \d+(?: \([^)]*\))?\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^Cast any number of Eldrazi spells from among cards you own outside the game"
        r"(?: without paying their mana costs)?\.?$",
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

    if re.match(
        r"^Other Elf creatures you control get [+-]\d+/[+-]\d+\.?$",
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
        r"^\(Each \{G\} in the mana costs of permanents you control counts "
        r"toward your devotion to green\.\)$",
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


    # E57/E65: static keyword grants that do not participate in modeled proofs.
    if re.match(
        r"^Equipped creature has (?:haste and )?(?:shroud|hexproof|indestructible)"
        r"(?: and (?:haste|shroud|hexproof|indestructible))*"
        r"\.?(?: \([^)]*\))?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^(?:Other )?permanents you control have indestructible\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^You have hexproof\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^Indestructible\.?(?: \([^)]*\))?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^During your turn, commanders you control have indestructible"
        r"\.?(?: \([^)]*\))?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^Myr creatures get [+-]\d+/[+-]\d+\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^This artifact enters with X charge counters on it\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^Whenever you draw a card, .+ gets [+-]\d+/[+-]\d+ until end of turn\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^Discard a card: .+ gains hexproof until end of turn\. Tap it\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^Unearth \{[^}]+\}(?: \([^)]*\))?\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^Damage can't be prevented\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^All damage is dealt as though its source had wither"
        r"\.?(?: \([^)]*\))?\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)

    if re.match(
        r"^Partner(?: \([^)]*\))?\.?$",
        clause,
        re.IGNORECASE,
    ):
        return _proof_irrelevant(clause)


    return None


# Order matters: more specific patterns first; proof-irrelevant static last.
PATTERNS: list[Pattern] = [
    Pattern("tap_create_token_untap", pat_tap_create_token_untap),
    Pattern("tap_sac_token_make_two", pat_tap_sac_token_make_two),
    Pattern("equipped_untap_pump", pat_equipped_untap_pump),
    Pattern("enchanted_tap_create_token", pat_enchanted_tap_create_token),
    Pattern(
        "enchanted_gain_life_put_that_many_p1p1",
        pat_enchanted_gain_life_put_that_many_p1p1,
    ),
    Pattern("tap_create_token", pat_tap_create_token),
    Pattern("mana_untap_create_token", pat_mana_untap_create_token),
    Pattern("cast_bounce_target_permanent", pat_cast_bounce_target_permanent),
    Pattern("etb_if_cast_half_life_drain", pat_etb_if_cast_half_life_drain),
    Pattern("etb_or_attacks_create_token", pat_etb_or_attacks_create_token),
    Pattern("mana_create_tokens_equal_subtype", pat_mana_create_tokens_equal_subtype),
    Pattern("mana_create_token", pat_mana_create_token),
    Pattern("hybrid_remove_m1m1_pump", pat_hybrid_remove_m1m1_pump),
    Pattern("tap_two_creatures_add_mana", pat_tap_two_creatures_add_mana),
    Pattern("etb_return_from_gy_to_hand", pat_etb_return_from_gy_to_hand),
    Pattern("gy_to_hand_activated", pat_gy_to_hand_activated),
    Pattern("dies_to_hand", pat_dies_to_hand),
    Pattern("scaled_mill", pat_scaled_mill),
    Pattern("sac_outlet_payoffs", pat_sac_outlet_payoffs),
    Pattern("dies_trigger_payoffs", pat_dies_trigger_payoffs),
    Pattern("self_etb_scaled", pat_self_etb_scaled),
    Pattern("cast_trigger_effects", pat_cast_trigger_effects),
    Pattern("scaled_mana_remainders", pat_scaled_mana_remainders),
    Pattern("etb_untap_up_to_lands", pat_etb_untap_up_to_lands),
    Pattern("tap_untap_n_lands", pat_tap_untap_n_lands),
    Pattern("tap_untap_target_land", pat_tap_untap_target_land),
    Pattern("bounce_self_activated", pat_bounce_self_activated),
    Pattern("cast_gain_life_per_spell", pat_cast_gain_life_per_spell),
    Pattern("pay_life_damage", pat_pay_life_damage),
    Pattern("attacks_half_mill", pat_attacks_half_mill),
    Pattern("spell_half_mill", pat_spell_half_mill),
    Pattern("grant_activated", pat_grant_activated),
    Pattern("draw_trigger_effect", pat_draw_trigger_effect),
    Pattern("curiosity_draw", pat_curiosity_draw),
    Pattern("damage_opponent_create_treasures", pat_damage_opponent_create_treasures),
    Pattern("dealt_damage_create_treasures", pat_dealt_damage_create_treasures),
    Pattern("dealt_damage_reflect", pat_dealt_damage_reflect),
    Pattern("dealt_damage_gain_life", pat_dealt_damage_gain_life),
    Pattern("replacement_double_tokens", pat_replacement_double_tokens),
    Pattern("etb_create_eldrazi_tokens", pat_etb_create_eldrazi_tokens),
    Pattern("mana_create_eldrazi_tokens", pat_mana_create_eldrazi_tokens),
    Pattern("enchantment_etb_create_cat", pat_enchantment_etb_create_cat),
    Pattern("replacement_double_counters", pat_replacement_double_counters),
    Pattern("replacement_double_life_gain", pat_replacement_double_life_gain),
    Pattern(
        "replacement_double_opponent_life_loss",
        pat_replacement_double_opponent_life_loss,
    ),
    Pattern("replacement_double_draw", pat_replacement_double_draw),
    Pattern("static_cant_gain_life", pat_static_cant_gain_life),
    Pattern("proliferate_activated", pat_proliferate_activated),
    Pattern("bounce_cost_untap_creature", pat_bounce_cost_untap_creature),
    Pattern("bounce_land_create_illusion", pat_bounce_land_create_illusion),
    Pattern(
        "activated_bounce_controlled_creature",
        pat_activated_bounce_controlled_creature,
    ),
    Pattern("tap_add_mana", pat_tap_add_mana),
    Pattern("mana_untap_enchanted", pat_mana_untap_enchanted),
    Pattern("mana_tap_enchanted", pat_mana_tap_enchanted),
    Pattern("mana_tap_gain_life", pat_mana_tap_gain_life),
    Pattern("mana_tap_untap_target", pat_mana_tap_untap_target),
    Pattern("mana_tap_tap_target", pat_mana_tap_tap_target),
    Pattern("mana_tap_draw", pat_mana_tap_draw),
    Pattern("tap_creature_subtype_draw", pat_tap_creature_subtype_draw),
    Pattern("tap_each_player_draw", pat_tap_each_player_draw),
    Pattern("untap_target_artifact", pat_untap_target_artifact),
    Pattern("etb_untap_artifact_or_creature", pat_etb_untap_artifact_or_creature),
    Pattern("discard_untap_target", pat_discard_untap_target),
    Pattern("adapt", pat_adapt),
    Pattern("tap_copy_creature_haste", pat_tap_copy_creature_haste),
    Pattern("splinter_twin_grant", pat_splinter_twin_grant),
    Pattern("p1p1_put_draw_discard", pat_p1p1_put_draw_discard),
    Pattern("p1p1_put_create_eldrazi_spawn", pat_p1p1_put_create_eldrazi_spawn),
    Pattern("discard_add_mana", pat_discard_add_mana),
    Pattern("discard_trigger_damage", pat_discard_trigger_damage),
    Pattern("discard_draw", pat_discard_draw),
    Pattern("remove_charge_add_mana", pat_remove_charge_add_mana),
    Pattern("attacks_put_charge", pat_attacks_put_charge),
    Pattern("attacks_untap_lands", pat_attacks_untap_lands),
    Pattern("attacks_damage_attacker", pat_attacks_damage_attacker),
    Pattern("attacks_draw", pat_attacks_draw),
    Pattern("tap_put_charge_target_artifact", pat_tap_put_charge_target_artifact),
    Pattern("sac_put_charge_target_artifact", pat_sac_put_charge_target_artifact),
    Pattern("tap_artifacts_untap_artifact", pat_tap_artifacts_untap_artifact),
    Pattern("mana_untap_self", pat_mana_untap_self),
    Pattern("cost_reduction", pat_cost_reduction),
    Pattern("zirda_cost_reduction", pat_zirda_cost_reduction),
    Pattern("power_artifact_cost_reduction", pat_power_artifact_cost_reduction),
    Pattern("untap_mill_controller", pat_untap_mill_controller),
    Pattern("cant_block_this_turn", pat_cant_block_this_turn),
    Pattern("put_m1m1_untap_self", pat_put_m1m1_untap_self),
    Pattern("replacement_multiply_tap_mana", pat_replacement_multiply_tap_mana),
    Pattern("vizier_m1m1_replacement", pat_vizier_m1m1_replacement),
    Pattern("amplify_p1p1_replacement", pat_amplify_p1p1_replacement),
    Pattern("etb_create_food", pat_etb_create_food),
    Pattern("etb_bounce_controlled_creature", pat_etb_bounce_controlled_creature),
    Pattern("etb_bounce_controlled_creature_gw", pat_etb_bounce_controlled_creature_gw),
    Pattern("etb_bounce_controlled_permanent", pat_etb_bounce_controlled_permanent),
    Pattern("etb_bounce_controlled_nonland", pat_etb_bounce_controlled_nonland),
    Pattern("activated_bounce_other_creature", pat_activated_bounce_other_creature),
    Pattern("etb_bounce_sharing_type", pat_etb_bounce_sharing_type),
    Pattern("etb_mana_sharing_creature_type", pat_etb_mana_sharing_creature_type),
    Pattern("earthcraft_tap_untap_basic", pat_earthcraft_tap_untap_basic),
    Pattern("aluren_free_cast", pat_aluren_free_cast),
    Pattern("instant_grant_tap_bounce", pat_instant_grant_tap_bounce),
    Pattern("create_token_put_p1p1_other", pat_create_token_put_p1p1_other),
    Pattern("counters_put_damage_opponent", pat_counters_put_damage_opponent),
    Pattern("m1m1_put_create_token", pat_m1m1_put_create_token),
    Pattern("counters_put_may_create_token", pat_counters_put_may_create_token),
    Pattern("etb_untap_target", pat_etb_untap_target),
    Pattern("warstorm_etb_power_damage", pat_warstorm_etb_power_damage),
    Pattern("landfall_create_token", pat_landfall_create_token),
    Pattern("artifact_etb_p1p1_target", pat_artifact_etb_p1p1_target),
    Pattern("sac_creature_add_mana", pat_sac_creature_add_mana),
    Pattern("sac_creature_outlet", pat_sac_creature_outlet),
    Pattern("sac_self", pat_sac_self),
    Pattern("return_from_gy", pat_return_from_gy),
    Pattern("cast_from_gy_if_zombie", pat_cast_from_gy_if_zombie),
    Pattern("dies_return_self", pat_dies_return_self),
    Pattern("dies_lose_life", pat_dies_lose_life),
    Pattern("dies_gain_life_equal_toughness", pat_dies_gain_life_equal_toughness),
    Pattern("gain_life_opponent_loses_that_much", pat_gain_life_opponent_loses_that_much),
    Pattern("gain_life_opponent_loses_fixed", pat_gain_life_opponent_loses_fixed),
    Pattern("opponent_lose_life_you_gain_that_much", pat_opponent_lose_life_you_gain_that_much),
    Pattern("opponent_lose_life_mill", pat_opponent_lose_life_mill),
    Pattern("card_to_opponent_gy_lose_life", pat_card_to_opponent_gy_lose_life),
    Pattern("enchantments_have_graveyard_drain", pat_enchantments_have_graveyard_drain),
    Pattern("etb_damage", pat_etb_damage),
    Pattern("etb_gain_life", pat_etb_gain_life),
    Pattern("gain_life_put_p1p1_each_controlled", pat_gain_life_put_p1p1_each_controlled),
    Pattern("gain_life_put_p1p1_target", pat_gain_life_put_p1p1_target),
    Pattern("etb_put_p1p1_each_controlled", pat_etb_put_p1p1_each_controlled),
    Pattern("etb_other_human_put_p1p1_self", pat_etb_other_human_put_p1p1_self),
    Pattern("etb_other_green_put_p1p1_target", pat_etb_other_green_put_p1p1_target),
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
