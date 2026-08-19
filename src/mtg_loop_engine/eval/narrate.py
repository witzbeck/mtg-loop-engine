"""Plain-English loop narrative for the adjudication workbench.

Converts raw op-codes and ability IDs into sentences a Magic novice can read.
Does not depend on Streamlit — pure string output.
"""

from __future__ import annotations

import urllib.parse

from mtg_loop_engine.proofs.models import ActionStep, LoopProof, LoopWitness


# ---------------------------------------------------------------------------
# Scryfall image URLs (no API call — browser fetches directly)
# ---------------------------------------------------------------------------

def card_image_url(name: str, version: str = "normal") -> str:
    """Return a Scryfall image URL for a card name.

    Uses the /cards/named endpoint with format=image. The browser fetches
    the image directly; no Scryfall API call is made from Python.
    """
    encoded = urllib.parse.quote(name)
    return (
        f"https://api.scryfall.com/cards/named"
        f"?exact={encoded}&format=image&version={version}"
    )


# ---------------------------------------------------------------------------
# Op-code → human verb
# ---------------------------------------------------------------------------

_OP_VERB: dict[str, str] = {
    # mana
    "TAP_FOR_MANA": "tap for mana",
    "ADD_MANA": "add mana",
    # tap / untap
    "TAP": "tap",
    "UNTAP": "untap",
    # activated abilities
    "ACTIVATE": "activate ability",
    "PAY_MANA": "pay mana cost",
    "SACRIFICE": "sacrifice",
    "SAC": "sacrifice",
    # triggered abilities
    "TRIGGER": "trigger ability",
    "RESOLVE_TRIGGER": "resolve triggered ability",
    # zone movement
    "RETURN_TO_BATTLEFIELD": "return to the battlefield",
    "RETURN_FROM_GRAVEYARD": "return from graveyard",
    "PUT_INTO_GRAVEYARD": "put into graveyard",
    "DIES": "dies",
    # counters
    "ADD_COUNTER": "put a +1/+1 counter on",
    "REMOVE_COUNTER": "remove a counter from",
    # tokens
    "CREATE_TOKEN": "create a token",
    # damage / life
    "DEAL_DAMAGE": "deal damage",
    "LOSE_LIFE": "lose life",
    # generic
    "RESOLVE": "resolve",
}


def _verb(op: str) -> str:
    return _OP_VERB.get(op.upper(), op.lower().replace("_", " "))


def _ability_hint(ability_id: str) -> str:
    """Extract a readable hint from an ability_id like 'basalt-tap-mana'."""
    parts = ability_id.replace("_", "-").split("-")
    # drop the card name prefix (first 1–2 tokens) and keep the rest
    # heuristic: if there are 3+ parts, drop the first; otherwise keep all
    if len(parts) >= 3:
        parts = parts[1:]
    return " ".join(parts)


def _format_step(i: int, step: ActionStep) -> str:
    verb = _verb(step.op)
    actor = step.actor or "?"
    hint = _ability_hint(step.ability_id) if step.ability_id else ""
    target_clause = f" targeting {step.target}" if step.target else ""
    ability_clause = f" ({hint})" if hint else ""
    return f"{i}. {actor.replace('_', ' ').title()}: {verb}{ability_clause}{target_clause}."


# ---------------------------------------------------------------------------
# Output delta → sentence
# ---------------------------------------------------------------------------

def _format_output(out) -> str:  # out: OutputDelta
    type_name = out.type.value.replace("_", " ").lower()
    consequence = out.consequence.value.replace("_", " ").lower()
    return f"+{out.delta_per_iteration} {type_name} per iteration ({consequence})"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def narrate_setup(witness: LoopWitness) -> list[str]:
    """Return one sentence per setup action, or empty list if none."""
    return [_format_step(i, step) for i, step in enumerate(witness.setup_actions or [], start=1)]


def narrate_loop(witness: LoopWitness) -> list[str]:
    """Return one plain-English sentence per loop-body step."""
    if not witness.loop_actions:
        return ["(no loop steps recorded)"]
    return [_format_step(i, step) for i, step in enumerate(witness.loop_actions, start=1)]


def narrate_outputs(proof: LoopProof) -> list[str]:
    """Return one sentence per output delta."""
    if not proof.output_deltas:
        return ["(no outputs recorded)"]
    return [_format_output(out) for out in proof.output_deltas]


def narrate_recurrence(proof: LoopProof) -> list[str]:
    """Return board-state dimensions that must be restored each iteration."""
    if proof.recurrence.details:
        return list(proof.recurrence.details)
    return ["(no recurrence dimensions recorded)"]


def full_narrative(witness: LoopWitness, proof: LoopProof) -> str:
    """Single block of plain-English prose suitable for st.markdown or st.text."""
    names = " + ".join(c.name for c in witness.essential_cards)
    lines: list[str] = [f"**{names}** — loop walkthrough", ""]

    setup = narrate_setup(witness)
    if setup:
        lines.append("**One-time setup:**")
        lines.extend(f"- {s}" for s in setup)
        lines.append("")

    lines.append("**Repeating loop body:**")
    lines.extend(f"- {s}" for s in narrate_loop(witness))
    lines.append("")

    lines.append("**What you get each iteration:**")
    lines.extend(f"- {s}" for s in narrate_outputs(proof))
    lines.append("")

    lines.append("**Board state that must reset each loop:**")
    lines.extend(f"- {s}" for s in narrate_recurrence(proof))

    return "\n".join(lines)
