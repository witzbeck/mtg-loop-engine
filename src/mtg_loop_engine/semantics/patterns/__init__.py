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
    DrawEffect,
    GainLifeEffect,
    LoseLifeEffect,
    ManaAmount,
    ManaCost,
    RemoveCounterEffect,
    ReplacementExileInsteadOfGraveyard,
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
    if not m:
        # {T}: Add one mana of any color.
        m_any = re.match(
            r"^\{T\}: Add one mana of any color(?: to your mana pool)?\.?$",
            text,
            re.IGNORECASE,
        )
        if not m_any:
            return None
        return ActivatedAbility(
            ability_id=_ability_id("tap-mana-any", text),
            costs=[TapCost()],
            effects=[AddManaEffect(amount=ManaAmount(any_color=1))],
            is_mana_ability=True,
            uses_stack=False,
        )
    amount = _parse_mana_braces(m.group(1))
    return ActivatedAbility(
        ability_id=_ability_id("tap-mana", text),
        costs=[TapCost()],
        effects=[AddManaEffect(amount=amount)],
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
        r"^((?:\{[^}]+\}(?:,\s*)?)+): Untap target creature\.?$",
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
    if not m_all:
        return None
    return TriggeredAbility(
        ability_id=_ability_id("etb-untap-all", text),
        event=TriggerEvent.ENTER_BATTLEFIELD,
        filter="creature",
        effects=[UntapEffect(target="all_creatures")],
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

    words = [part.strip().lower() for part in clause.split() if part.strip()]
    if words and all(word in _KEYWORD_ABILITIES for word in words):
        return _proof_irrelevant(clause)

    if re.match(r"^Ward \{[^}]+\}(?: \([^)]+\))?$", clause, re.IGNORECASE):
        return _proof_irrelevant(clause)

    if re.match(r"^Enchant (?:target )?.+$", clause, re.IGNORECASE):
        return _proof_irrelevant(clause)

    if re.match(r"^Equip (?:\{[^}]+\})+(?: \([^)]+\))?$", clause, re.IGNORECASE):
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
    Pattern("etb_untap_target", pat_etb_untap_target),
    Pattern("sac_creature_add_mana", pat_sac_creature_add_mana),
    Pattern("sac_creature_outlet", pat_sac_creature_outlet),
    Pattern("sac_self", pat_sac_self),
    Pattern("return_from_gy", pat_return_from_gy),
    Pattern("cast_from_gy_if_zombie", pat_cast_from_gy_if_zombie),
    Pattern("dies_return_self", pat_dies_return_self),
    Pattern("dies_lose_life", pat_dies_lose_life),
    Pattern("etb_damage", pat_etb_damage),
    Pattern("etb_gain_life", pat_etb_gain_life),
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
