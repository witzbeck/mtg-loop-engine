"""Derive claim consequence from recurrence + net state (not witness labels).

Definitions (product contract):

- ``ACCUMULATES``: beneficial net-state dimension increases (mana / life_you /
  creature tokens / +1/+1 counters) while recurrence holds.
- ``REPEATABLE_EVENT``: recurrence holds, a relevant gross event repeats, and
  beneficial net state is zero (no mana/life/token/counter gain; opponent life
  unchanged).
- ``LETHAL``: recurrence holds and net opponent life decreases each iteration —
  arbitrary repeatability implies unbounded life loss. A single-iteration
  ``life_opponent = -1`` without recurrence is not sufficient (recurrence is
  checked before this module runs).

Priority when multiple apply: ``LETHAL`` > ``ACCUMULATES`` > ``REPEATABLE_EVENT``.
"""

from __future__ import annotations

from mtg_loop_engine.proofs.models import NetStateDelta
from mtg_loop_engine.semantics.enums import Consequence

_MANA_COLORS = (
    "white",
    "blue",
    "black",
    "red",
    "green",
    "colorless",
    "generic",
    "any_color",
)

# Categories with mathematical derivation in this module.
DERIVED_CONSEQUENCES: frozenset[Consequence] = frozenset(
    {
        Consequence.ACCUMULATES,
        Consequence.REPEATABLE_EVENT,
        Consequence.LETHAL,
    }
)


def has_beneficial_accumulation(net: NetStateDelta) -> bool:
    """True if any modeled beneficial pool/board dimension increases."""
    if net.life_you > 0 or net.creature_tokens > 0 or net.plus_one_counters > 0:
        return True
    return any(getattr(net.mana, color) > 0 for color in _MANA_COLORS)


def beneficial_net_is_zero(net: NetStateDelta) -> bool:
    """True when no beneficial accumulation and opponent life is unchanged."""
    if net.life_opponent != 0:
        return False
    if net.life_you != 0 or net.creature_tokens != 0 or net.plus_one_counters != 0:
        return False
    return all(getattr(net.mana, color) == 0 for color in _MANA_COLORS)


def derive_claim_consequence(
    net: NetStateDelta,
    *,
    gross_event_ok: bool,
) -> Consequence:
    """Classify the loop claim from net state after recurrence + outputs pass.

    ``gross_event_ok`` is True when expected output deltas were satisfied
    (a relevant gross event repeated this iteration).
    """
    if net.life_opponent < 0:
        return Consequence.LETHAL
    if has_beneficial_accumulation(net):
        return Consequence.ACCUMULATES
    if beneficial_net_is_zero(net) and gross_event_ok:
        return Consequence.REPEATABLE_EVENT
    return Consequence.OTHER


def claim_consequence_mismatch(
    derived: Consequence,
    expected: Consequence | None,
) -> str | None:
    """Return a rejection detail if ``expected`` disagrees with ``derived``.

    When ``expected`` is None, no mismatch (discovery may omit the label).
    When ``expected`` is outside ``DERIVED_CONSEQUENCES``, skip (not yet
    mathematically gated).
    """
    if expected is None:
        return None
    if expected not in DERIVED_CONSEQUENCES:
        return None
    if derived != expected:
        return (
            f"claim consequence mismatch: expected {expected.value} "
            f"derived {derived.value}"
        )
    return None
