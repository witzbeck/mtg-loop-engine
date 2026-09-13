"""Verify corpus witnesses (Oracle gold and physics fixtures)."""

from __future__ import annotations

import click

from mtg_loop_engine.corpus import (
    all_gold_core,
    gold_extended_catalog,
    hard_negatives,
    physics_all_positives,
    physics_hard_negatives,
)
from mtg_loop_engine.verify.verifier import Verifier


def _verify_gold() -> int:
    v = Verifier()
    failures = 0
    positives = all_gold_core()
    if not positives:
        click.echo("gold_core positives: 0 (Oracle promotions pending)")
    for w in positives:
        proof = v.verify(w)
        ok = proof.status.value == "verified"
        click.echo(f"{w.id}: {proof.status.value} hash={proof.proof_hash}")
        if not ok:
            failures += 1
            click.echo(f"  reason: {proof.rejection_reason}")
    for w in hard_negatives():
        proof = v.verify(w)
        expected = w.expected_status.value if w.expected_status else None
        match = expected is None or proof.status == w.expected_status
        click.echo(f"{w.id}: {proof.status.value} (expected {expected}) ok={match}")
        if not match:
            failures += 1
    return 1 if failures else 0


def _verify_physics() -> int:
    v = Verifier()
    failures = 0
    for w in physics_all_positives():
        proof = v.verify(w)
        ok = proof.status.value == "verified"
        click.echo(f"{w.id}: {proof.status.value} hash={proof.proof_hash}")
        if not ok:
            failures += 1
            click.echo(f"  reason: {proof.rejection_reason}")
    for w in physics_hard_negatives():
        proof = v.verify(w)
        expected = w.expected_status.value if w.expected_status else None
        match = expected is None or proof.status == w.expected_status
        click.echo(f"{w.id}: {proof.status.value} (expected {expected}) ok={match}")
        if not match:
            failures += 1
    for w in gold_extended_catalog()[:3]:
        proof = v.verify(w)
        click.echo(f"{w.id}: {proof.status.value}")
    return 1 if failures else 0


def register(cli: click.Group) -> None:
    @cli.command(
        "verify-gold",
        help="Run Oracle-exact gold_core positives + Oracle hard negatives",
    )
    def verify_gold() -> None:
        """Verify Oracle-exact gold_core positives and Oracle hard negatives."""
        raise SystemExit(_verify_gold())

    @cli.command(
        "verify-physics",
        help="Run synthetic/divergent physics fixtures + physics hard negatives",
    )
    def verify_physics() -> None:
        """Verify synthetic/divergent physics fixtures (not precision-eligible)."""
        raise SystemExit(_verify_physics())
