"""M5 E58: Split second (+ one-shot riders as proof-irrelevant)."""

from mtg_loop_engine.semantics.compiler import compile_oracle_text, split_oracle_abilities
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    mana_cost = _parse_mana_braces(row.mana_cost) if row.mana_cost else None
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-').replace(chr(39), '')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=mana_cost,
        mana_value=row.mana_value,
    )


def test_e58_cards_complete():
    for key in ("Angel's Grace", "Legolas's Quick Reflexes"):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.coverage,
            report.semantics.unsupported_fragments,
        )


def test_split_second_reminder_splits_from_effect():
    parts = split_oracle_abilities(
        "Split second (As long as this spell is on the stack, players can't cast "
        "spells or activate abilities that aren't mana abilities.) "
        "Untap target creature."
    )
    assert parts[0].startswith("Split second")
    assert parts[1].startswith("Untap target")
