"""Deterministic Oracle text → semantic IR compiler."""

from __future__ import annotations

import re

from mtg_loop_engine.semantics.coverage import CompileReport, FragmentResult
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.ir import CardSemantics, ManaAmount
from mtg_loop_engine.semantics.patterns import try_match


def split_oracle_abilities(oracle_text: str) -> list[str]:
    """Split Oracle text into ability clauses.

    Uses blank lines and newline boundaries; joins soft line wraps that don't
    start a new ability ({, Whenever, When, At, If, Enchant, Equip, etc.).
    """
    if not oracle_text or not oracle_text.strip():
        return []
    # Normalize Windows newlines; keep paragraph splits.
    text = oracle_text.replace("\r\n", "\n").strip()
    raw_lines = [ln.strip() for ln in text.split("\n")]
    clauses: list[str] = []
    buf = ""
    _kw = (
        r"Flying|Flash|Haste|Vigilance|Trample|Lifelink|Deathtouch|Reach|Defender|"
        r"Menace|Hexproof|Shroud|Indestructible|First strike|Double strike|"
        r"Infect(?: \([^)]+\))?|Indestructible(?: \([^)]+\))?|Ward(?: \([^)]+\))?"
    )
    keyword_line = re.compile(
        rf"^(?:{_kw})(?:, (?:{_kw}))*$",
        re.IGNORECASE,
    )
    ability_start = re.compile(
        r"^(\{|"
        r"Whenever |When |At the beginning |If |You may cast |"
        r"Until end of turn, |"
        r"As long as |"
        r"During your turn, |"
        r"Abilities you |"
        r"Enchantments you |"
        r"Colorless creatures |"
        r"Creatures you |"
        r"Creature spells |"
        r"Spells you cast |"
        r"Other |"
        r"You have |"
        r"Equipped |"
        r"Enchanted |Enchant |Equip |Flashback |Kicker |"
        r"Sacrifice |Remove a |"
        r"Pay |"
        r"Players |"
        r"Your opponents |"
        r"Opponents |"
        r"Damage can't |"
        r"All damage |"
        r"Discard |"
        r"Cycling |Partner |"
        r"Persist |"
        r"Activated abilities |"
        r"Protection |"
        r"Put a |"
        r"Morph |"
        r"Eternalize |"
        r"Unearth |"
        r"Cascade |Convoke |Delve |"
        r"Flying |Flash |Haste |Vigilance |Trample |Lifelink |Deathtouch |Reach |"
        r"Defender |Menace |Hexproof |Shroud |First strike |Double strike |Infect |"
        r"Indestructible |"
        r"Umbra armor |Warp |Annihilator |"
        # Ability words / named abilities (incl. ALL CAPS, ?, ! — Marvel style)
        r".{1,60}? — )"
    )
    # Same-line ability joins (Animar cast trigger + cost reduction).
    secondary_split = re.compile(
        r"(?<=\.) (?="
        r"Creature spells you cast |"
        r"Spells you cast |"
        r"Activated abilities |"
        r"Whenever |When |At the beginning |"
        r"During your turn, |"
        r"Protection "
        r")",
        re.IGNORECASE,
    )
    for line in raw_lines:
        if not line:
            if buf:
                clauses.append(buf.strip())
                buf = ""
            continue
        if buf and (ability_start.match(line) or keyword_line.match(line)):
            clauses.append(buf.strip())
            buf = line
        elif not buf:
            buf = line
        elif keyword_line.match(buf):
            # Keyword lines are complete abilities; do not soft-wrap the next clause.
            clauses.append(buf.strip())
            buf = line
        else:
            buf = f"{buf} {line}"
    if buf:
        clauses.append(buf.strip())
    out: list[str] = []
    for clause in clauses:
        out.extend(p.strip() for p in secondary_split.split(clause) if p.strip())
    return out


def compile_oracle_text(
    *,
    oracle_id: str,
    name: str,
    oracle_text: str,
    types: list[str] | None = None,
    colors: list[str] | None = None,
    mana_cost: ManaAmount | None = None,
    mana_value: int | None = None,
    treat_unsupported_as_relevant: bool = True,
) -> CompileReport:
    """Compile Oracle text into CardSemantics with explicit coverage.

    Unmatched fragments are unsupported. By default they mark coverage as
    PARTIAL_RELEVANT_TO_PROOF (fail-closed for verification). Callers that
    know unused clauses are irrelevant may pass treat_unsupported_as_relevant=False.
    """
    fragments: list[FragmentResult] = []
    abilities = []
    unsupported: list[str] = []

    # Empty Oracle must not silently count as COMPLETE (common for unresolved DFCs).
    if not (oracle_text or "").strip():
        unsupported = ["(empty oracle text)"]
        coverage = (
            SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF
            if treat_unsupported_as_relevant
            else SemanticCoverage.PARTIAL_IRRELEVANT_TO_PROOF
        )
        semantics = CardSemantics(
            oracle_id=oracle_id,
            name=name,
            types=types or [],
            colors=list(colors or []),
            mana_cost=(mana_cost or ManaAmount()).model_copy(deep=True),
            mana_value=int(mana_value if mana_value is not None else (mana_cost or ManaAmount()).total()),
            abilities=[],
            unsupported_fragments=unsupported,
            coverage=coverage,
        )
        return CompileReport(
            oracle_id=oracle_id,
            name=name,
            fragments=[
                FragmentResult(
                    text="(empty oracle text)",
                    supported=False,
                    note="missing oracle text",
                )
            ],
            semantics=semantics,
            coverage=coverage,
        )

    for clause in split_oracle_abilities(oracle_text):
        matched = try_match(clause, name)
        if matched is None:
            unsupported.append(clause)
            fragments.append(
                FragmentResult(
                    text=clause,
                    supported=False,
                    note="no deterministic pattern matched",
                )
            )
            continue
        pattern_id, ability = matched
        abilities.append(ability)
        fragments.append(
            FragmentResult(
                text=clause,
                supported=True,
                pattern_id=pattern_id,
                ability=ability,
            )
        )

    if not unsupported:
        coverage = SemanticCoverage.COMPLETE
    elif treat_unsupported_as_relevant:
        coverage = SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF
    else:
        coverage = SemanticCoverage.PARTIAL_IRRELEVANT_TO_PROOF

    cost = (mana_cost or ManaAmount()).model_copy(deep=True)
    mv = int(mana_value if mana_value is not None else cost.total())
    semantics = CardSemantics(
        oracle_id=oracle_id,
        name=name,
        types=types or [],
        colors=list(colors or []),
        mana_cost=cost,
        mana_value=mv,
        abilities=abilities,
        unsupported_fragments=unsupported,
        coverage=coverage,
    )
    return CompileReport(
        oracle_id=oracle_id,
        name=name,
        fragments=fragments,
        semantics=semantics,
        coverage=coverage,
    )
