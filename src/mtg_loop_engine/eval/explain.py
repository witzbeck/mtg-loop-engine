"""Reviewer-facing explanations. JSON/IR is secondary evidence."""

from __future__ import annotations

from mtg_loop_engine.eval.classify import analyze_prerequisites
from mtg_loop_engine.eval.schema import CandidateRecord, PrerequisiteAnalysis
from mtg_loop_engine.proofs.models import LoopProof, LoopWitness
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES


def oracle_text_for(oracle_id: str, fallback: str = "") -> str:
    fixture = GOLD_ORACLE_FIXTURES.get(oracle_id)
    if fixture is not None:
        return fixture.oracle_text
    return fallback


def explain_proof(witness: LoopWitness, proof: LoopProof) -> str:
    analysis = analyze_prerequisites(witness)
    return _render(witness, proof, analysis)


def _render(
    witness: LoopWitness, proof: LoopProof, analysis: PrerequisiteAnalysis
) -> str:
    names = " + ".join(c.name for c in witness.essential_cards)
    lines = [
        f"{names} was accepted as {proof.status.value}.",
        "",
        "Object map (ids in loop steps; not Card 1/Card 2 display order):",
    ]
    for perm in witness.initial_state.permanents:
        zone = perm.zone.value if hasattr(perm.zone, "value") else perm.zone
        lines.append(f"- {perm.object_id}: {perm.name} ({zone})")
    claim = proof.claim_consequence
    claim_val = claim.value if claim is not None else "(none)"
    lines.append("")
    lines.append(f"Claim consequence: {claim_val}")
    if proof.net_state is not None:
        net = proof.net_state
        lines.append(
            "Net per iteration: "
            f"mana={net.mana.model_dump(mode='json')}; "
            f"life_you={net.life_you}; life_opponent={net.life_opponent}; "
            f"tokens={net.creature_tokens}; +1/+1={net.plus_one_counters}"
        )
    lines.append("")
    lines.append("Loop body:")
    if not witness.loop_actions:
        lines.append("- (empty)")
    for i, step in enumerate(witness.loop_actions, start=1):
        target = f" targeting {step.target}" if step.target else ""
        lines.append(
            f"- {i}. {step.op} {step.actor} / {step.ability_id}{target}"
        )
    lines.append("")
    lines.append("Outputs per iteration:")
    if not proof.output_deltas:
        lines.append("- (none recorded)")
    for out in proof.output_deltas:
        lines.append(f"- {out.type.value}: +{out.delta_per_iteration}")
    lines.append("")
    lines.append("Recurrence (LoopRelevantState):")
    if proof.recurrence.details:
        for detail in proof.recurrence.details:
            lines.append(f"- {detail}")
    else:
        lines.append("- (no dimension details)")
    lines.append("")
    lines.append("Starting-state assumptions:")
    for assumption in analysis.assumptions:
        oid = f" ({assumption.object_id})" if assumption.object_id else ""
        lines.append(
            f"- [{assumption.kind.value}] {assumption.description}{oid}"
        )
    lines.append("")
    lines.append("Essential-piece analysis:")
    lines.append(
        f"- participating cards: {analysis.essential_functional_count}; "
        f"strict_two_card={analysis.strict_two_card}"
    )
    for note in analysis.notes:
        lines.append(f"- {note}")
    if analysis.generic_prerequisites:
        lines.append("Generic prerequisites:")
        for item in analysis.generic_prerequisites:
            lines.append(f"- {item}")
    if analysis.functional_external_requirements:
        lines.append("Functional external requirements:")
        for item in analysis.functional_external_requirements:
            lines.append(f"- {item}")
    lines.append("")
    lines.append(
        f"Semantic coverage: {proof.semantic_coverage.value}. "
        f"Proof hash {proof.proof_hash}."
    )
    return "\n".join(lines)


def record_from_hit(
    *,
    witness: LoopWitness,
    proof: LoopProof,
    reasons: list[str],
    corpus: str,
    reference_status,
    engine_version: str = "0.1.0",
    oracle_snapshot_hash: str | None = None,
    spellbook_snapshot_hash: str | None = None,
    oracle_text: dict[str, str] | None = None,
) -> CandidateRecord:
    from mtg_loop_engine.eval.schema import CandidateRecord, ReferenceStatus

    left, right = sorted(witness.essential_cards, key=lambda c: c.oracle_id)
    analysis = analyze_prerequisites(witness)
    texts = oracle_text or {}
    candidate_id = f"{left.oracle_id}__{right.oracle_id}::{proof.proof_hash}"
    status = reference_status or ReferenceStatus.ABSENT_FROM_REFERENCE
    return CandidateRecord(
        candidate_id=candidate_id,
        corpus=corpus,
        left_id=left.oracle_id,
        right_id=right.oracle_id,
        left_name=left.name,
        right_name=right.name,
        left_oracle_text=texts.get(left.oracle_id) or oracle_text_for(left.oracle_id),
        right_oracle_text=texts.get(right.oracle_id) or oracle_text_for(right.oracle_id),
        join_reasons=list(reasons),
        reference_status=status,
        analysis=analysis,
        explanation=explain_proof(witness, proof),
        witness=witness,
        proof=proof,
        engine_version=engine_version,
        oracle_snapshot_hash=oracle_snapshot_hash,
        spellbook_snapshot_hash=spellbook_snapshot_hash,
    )
