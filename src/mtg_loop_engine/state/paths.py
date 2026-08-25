"""Allowed ``LoopRelevantState`` path grammar (matches ``GameState.get_path``).

Structural validation only — a grammatically valid path may still miss at
runtime (unknown permanent id) and yield ``STATE_NOT_RECURRENT``.
"""

from __future__ import annotations

from mtg_loop_engine.semantics.enums import Zone

# ManaAmount field names addressable via mana.<color>.
MANA_PATH_COLORS: frozenset[str] = frozenset(
    {
        "white",
        "blue",
        "black",
        "red",
        "green",
        "colorless",
        "generic",
        "any_color",
    }
)

LIFE_WHO: frozenset[str] = frozenset({"you", "opponent"})

COUNT_KINDS: frozenset[str] = frozenset(
    {"creature_tokens", "creatures", "artifacts"}
)

ZONE_PATH_VALUES: frozenset[str] = frozenset(z.value for z in Zone)

# Human-readable grammar for docs / rejection reasons.
STATE_PATH_GRAMMAR = """\
mana.<white|blue|black|red|green|colorless|generic|any_color>
events.<key>
life.<you|opponent>
permanents.<id>.zone|tapped|summoning_sick
permanents.<id>.counters.<type>
permanents.<id>.once_per_turn_used.<ability_id>
pending_triggers.count
count.<zone>.<creature_tokens|creatures|artifacts>\
"""


def is_valid_state_path(path: str) -> bool:
    """Return True iff ``path`` matches the grammar ``GameState.get_path`` supports."""
    if not path or ".." in path or path.startswith(".") or path.endswith("."):
        return False
    parts = path.split(".")
    head = parts[0]
    if head == "mana":
        return len(parts) == 2 and parts[1] in MANA_PATH_COLORS
    if head == "events":
        return len(parts) == 2 and bool(parts[1])
    if head == "life":
        return len(parts) == 2 and parts[1] in LIFE_WHO
    if head == "permanents":
        if len(parts) < 3 or not parts[1]:
            return False
        attr = parts[2]
        if attr in {"zone", "tapped", "summoning_sick"}:
            return len(parts) == 3
        if attr == "counters":
            return len(parts) == 4 and bool(parts[3])
        if attr == "once_per_turn_used":
            return len(parts) == 4 and bool(parts[3])
        return False
    if head == "pending_triggers":
        return len(parts) == 2 and parts[1] == "count"
    if head == "count":
        return (
            len(parts) == 3
            and parts[1] in ZONE_PATH_VALUES
            and parts[2] in COUNT_KINDS
        )
    return False


def state_path_error(path: str) -> str | None:
    """None if valid; otherwise a short rejection detail."""
    if is_valid_state_path(path):
        return None
    return f"invalid state path {path!r} (allowed: {STATE_PATH_GRAMMAR.splitlines()[0]}…)"
