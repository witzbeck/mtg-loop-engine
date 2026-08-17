"""Witness-in / proof-out verifier (no search)."""

from __future__ import annotations

import hashlib
import json
import subprocess
from typing import Any

from mtg_loop_engine.config import EngineConfig
from mtg_loop_engine.proofs.models import (
    LoopProof,
    LoopWitness,
    RecurrenceResult,
    VersionIdentity,
)
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.enums import (
    ComparisonOp,
    ProofKind,
    SemanticCoverage,
    VerificationStatus,
)
from mtg_loop_engine.state.game import GameState


def _git_sha() -> str | None:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            or None
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def check_recurrence(
    before: GameState, after: GameState, witness: LoopWitness
) -> RecurrenceResult:
    details: list[str] = []
    ok = True
    for dim in witness.relevant_state.dimensions:
        try:
            b = before.get_path(dim.path)
            a = after.get_path(dim.path)
        except KeyError as exc:
            return RecurrenceResult(ok=False, details=[f"missing path {exc}"])
        if dim.op == ComparisonOp.EXACT:
            expected = dim.value if dim.value is not None else b
            if a != expected:
                ok = False
                details.append(f"{dim.path}: EXACT want {expected} got {a}")
            else:
                details.append(f"{dim.path}: EXACT {a} ok")
        elif dim.op == ComparisonOp.MINIMUM:
            floor = dim.value if dim.value is not None else b
            if not (a >= floor and a >= b):
                # Must be at least the declared minimum and not worse than before
                # when minimum tracks reusable resources that should not shrink below start.
                if a < b:
                    ok = False
                    details.append(f"{dim.path}: MINIMUM regressed {b} -> {a}")
                elif a < floor:
                    ok = False
                    details.append(f"{dim.path}: MINIMUM want >= {floor} got {a}")
                else:
                    details.append(f"{dim.path}: MINIMUM {a} ok")
            else:
                details.append(f"{dim.path}: MINIMUM {a} ok")
        elif dim.op == ComparisonOp.MAXIMUM:
            ceiling = dim.value if dim.value is not None else b
            if a > ceiling:
                ok = False
                details.append(f"{dim.path}: MAXIMUM want <= {ceiling} got {a}")
            else:
                details.append(f"{dim.path}: MAXIMUM {a} ok")
    return RecurrenceResult(ok=ok, details=details)


def check_outputs(before: GameState, after: GameState, witness: LoopWitness) -> list[str]:
    problems: list[str] = []
    if not witness.expected_outputs:
        # Require some productive event increase if outputs declared empty → not a loop
        problems.append("no expected outputs declared")
        return problems
    for out in witness.expected_outputs:
        key = out.type.value
        delta = after.event_counters.get(key, 0) - before.event_counters.get(key, 0)
        if delta < out.delta_per_iteration:
            problems.append(
                f"output {key}: want delta>={out.delta_per_iteration} got {delta}"
            )
    return problems


def proof_hash(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:32]


class Verifier:
    def __init__(self, config: EngineConfig | None = None):
        self.config = config or EngineConfig()

    def verify(self, witness: LoopWitness) -> LoopProof:
        versions = VersionIdentity(
            rules_version=self.config.rules_version,
            semantic_schema_version=self.config.semantic_schema_version,
            engine_version=self.config.engine_version,
            proof_schema_version=self.config.proof_schema_version,
            git_sha=_git_sha(),
        )

        def reject(
            status: VerificationStatus,
            reason: str,
            recurrence: RecurrenceResult | None = None,
            coverage: SemanticCoverage | None = None,
        ) -> LoopProof:
            cov = coverage or witness.semantic_coverage
            body = {
                "witness_id": witness.id,
                "status": status.value,
                "reason": reason,
            }
            return LoopProof(
                kind=ProofKind.VALID,
                witness_id=witness.id,
                essential_cards=witness.essential_cards,
                classification=witness.classification,
                versions=versions,
                assumptions=witness.assumptions,
                prerequisites=witness.prerequisites,
                initial_state=witness.initial_state,
                setup_actions=witness.setup_actions,
                loop_actions=witness.loop_actions,
                recurrence=recurrence or RecurrenceResult(ok=False, details=[reason]),
                output_deltas=[],
                consequences=[],
                status=status,
                rejection_reason=reason,
                semantic_coverage=cov,
                proof_hash=proof_hash(body),
            )

        if not witness.deterministic:
            return reject(VerificationStatus.NONDETERMINISTIC, "witness not deterministic")

        # Fail-closed semantic coverage
        if witness.semantic_coverage == SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF:
            return reject(
                VerificationStatus.UNSUPPORTED_SEMANTICS,
                "partial relevant semantics",
            )
        for card in witness.card_semantics:
            if card.relevant_unsupported():
                return reject(
                    VerificationStatus.UNSUPPORTED_SEMANTICS,
                    f"unsupported on {card.name}",
                    coverage=SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF,
                )

        # Functional external requirements disqualify strict verified two-card loops.
        if witness.classification.functional_external_requirements:
            return reject(
                VerificationStatus.EXTERNAL_FUNCTIONAL_PIECE_REQUIRED,
                "functional external piece required",
            )

        # Essential card count gate
        if (
            witness.classification.essential_card_count
            > self.config.max_essential_cards
        ):
            return reject(
                VerificationStatus.EXTERNAL_FUNCTIONAL_PIECE_REQUIRED,
                "essential_card_count exceeds max_essential_cards",
            )

        semantics = {c.oracle_id: c for c in witness.card_semantics}
        executor = Executor(semantics)
        state = GameState.from_spec(witness.initial_state)

        err = executor.run_sequence(state, witness.setup_actions)
        if err:
            return reject(err.status, err.message)

        before = state.copy()
        err = executor.run_sequence(state, witness.loop_actions)
        if err:
            return reject(err.status, err.message)

        after = state
        recurrence = check_recurrence(before, after, witness)
        if not recurrence.ok:
            return reject(
                VerificationStatus.STATE_NOT_RECURRENT,
                "recurrence failed",
                recurrence=recurrence,
            )

        out_problems = check_outputs(before, after, witness)
        if out_problems:
            return reject(
                VerificationStatus.NOT_A_LOOP,
                "; ".join(out_problems),
                recurrence=recurrence,
            )

        consequences = [o.consequence for o in witness.expected_outputs]
        body = {
            "witness_id": witness.id,
            "status": VerificationStatus.VERIFIED.value,
            "loop": [a.model_dump() for a in witness.loop_actions],
            "outputs": [o.model_dump() for o in witness.expected_outputs],
        }
        return LoopProof(
            kind=ProofKind.VALID,
            witness_id=witness.id,
            essential_cards=witness.essential_cards,
            classification=witness.classification,
            versions=versions,
            assumptions=list(witness.assumptions)
            + [
                "choice_ownership: combo_player_favorable",
                "choice_ownership: opponent_adversarial",
                "deterministic_only",
            ],
            prerequisites=witness.prerequisites,
            initial_state=witness.initial_state,
            setup_actions=witness.setup_actions,
            loop_actions=witness.loop_actions,
            recurrence=recurrence,
            output_deltas=witness.expected_outputs,
            consequences=consequences,
            status=VerificationStatus.VERIFIED,
            rejection_reason=None,
            semantic_coverage=witness.semantic_coverage,
            proof_hash=proof_hash(body),
        )
