"""M5 E59: Buyback / Kicker cast riders as proof-irrelevant."""

from mtg_loop_engine.semantics.compiler import compile_oracle_text, split_oracle_abilities
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    mana_cost = _parse_mana_braces(row.mana_cost) if row.mana_cost else None
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=mana_cost,
        mana_value=row.mana_value,
    )


def test_e59_cards_complete():
    for key in ("Searing Touch", "Clockspinning", "Sprout Swarm"):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_buyback_reminder_splits_from_effect():
    parts = split_oracle_abilities(
        "Buyback {4} (You may pay an additional {4} as you cast this spell. "
        "If you do, put this card into your hand as it resolves.) "
        "Searing Touch deals 1 damage to any target."
    )
    assert parts[0].startswith("Buyback")
    assert parts[1].startswith("Searing Touch deals")
