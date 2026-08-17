"""Deterministic Oracle text → semantic IR compiler."""

from __future__ import annotations

import re

from mtg_loop_engine.semantics.coverage import CompileReport, FragmentResult
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.ir import CardSemantics
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
    ability_start = re.compile(
        r"^(\{|"
        r"Whenever |When |At the beginning |If |"
        r"Enchant |Equip |Flashback |Kicker |"
        r"Sacrifice |Remove a |"
        r"Activated abilities |"
        r"Put a )"
    )
    for line in raw_lines:
        if not line:
            if buf:
                clauses.append(buf.strip())
                buf = ""
            continue
        if buf and ability_start.match(line):
            clauses.append(buf.strip())
            buf = line
        elif not buf:
            buf = line
        else:
            buf = f"{buf} {line}"
    if buf:
        clauses.append(buf.strip())
    return clauses


def compile_oracle_text(
    *,
    oracle_id: str,
    name: str,
    oracle_text: str,
    types: list[str] | None = None,
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

    semantics = CardSemantics(
        oracle_id=oracle_id,
        name=name,
        types=types or [],
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
