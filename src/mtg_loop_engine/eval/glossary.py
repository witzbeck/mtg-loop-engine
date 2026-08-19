"""MTG jargon definitions for the tutorial workbench.

Each entry is a (term, definition) pair. Definitions are kept to one or two
sentences — enough for a novice to understand the term in context.
"""

from __future__ import annotations

# Ordered list so the glossary renders alphabetically in the UI.
GLOSSARY: list[tuple[str, str]] = [
    (
        "Activate / activated ability",
        "Pay the cost listed before the colon (e.g. {T}, {2}, sacrifice a creature) "
        "to put the ability on the stack. Anyone can activate an ability they control "
        "at instant speed unless the card says otherwise.",
    ),
    (
        "Battlefield",
        "The zone where permanents (creatures, artifacts, enchantments, lands, planeswalkers) "
        "live once they've resolved. 'In play' is the old term for this.",
    ),
    (
        "Cast / spell",
        "Playing a card from your hand by paying its mana cost. Cards on the stack "
        "(before they resolve) are called spells.",
    ),
    (
        "Dies",
        "A creature or planeswalker 'dies' when it moves from the battlefield to the "
        "graveyard, usually because its toughness reached 0 or it was sacrificed.",
    ),
    (
        "ETB (enters-the-battlefield trigger)",
        "An ability that fires automatically when a permanent enters the battlefield. "
        "Example: 'When ~ enters, create a 1/1 token.'",
    ),
    (
        "Graveyard",
        "The discard pile. Cards go here when spells resolve, creatures die, or "
        "permanents are sacrificed. Many loops recur cards from the graveyard.",
    ),
    (
        "Mana ability",
        "A special fast ability that adds mana to your mana pool. It does NOT use the "
        "stack and cannot be responded to. Tapping a land or Basalt Monolith for mana "
        "is a mana ability.",
    ),
    (
        "Mana pool",
        "The temporary store of mana you've produced during a turn. Unused mana "
        "disappears at the end of each step and phase.",
    ),
    (
        "Sacrifice",
        "Put a permanent you control directly into the graveyard as a cost or effect. "
        "Sacrificing cannot be prevented by indestructible.",
    ),
    (
        "Stack",
        "The zone where spells and non-mana abilities wait to resolve. Players may "
        "respond to each item before it resolves (last-in, first-out).",
    ),
    (
        "Tap / {T}",
        "Turn a permanent sideways to indicate it has been used. Most permanents can "
        "only be tapped once per turn (they 'have summoning sickness' if newly placed).",
    ),
    (
        "Trigger / triggered ability",
        "An ability that fires automatically when a specific event occurs — e.g. "
        "'whenever a creature dies' or 'at the beginning of your upkeep'. Unlike "
        "activated abilities, you don't pay a cost; it just happens.",
    ),
    (
        "Untap / {Q}",
        "Return a tapped permanent to its upright position. Lands and creatures untap "
        "at the start of your untap step each turn, but some abilities untap permanents "
        "at other times.",
    ),
    (
        "Zone",
        "MTG tracks where each card is: library, hand, battlefield, graveyard, stack, "
        "exile, or command zone. Abilities often care about which zone a card is in.",
    ),
]

GLOSSARY_DICT: dict[str, str] = dict(GLOSSARY)
