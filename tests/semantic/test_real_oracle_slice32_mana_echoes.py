"""M5 slice 32: Mana Echoes creature-type-share ETB mana."""

from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import ManaScaleKind, SemanticCoverage, VerificationStatus
from mtg_loop_engine.semantics.ir import AddManaEffect, ManaAmount, TriggeredAbility
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    slug = key.lower().replace(" ", "-")
    cost = _parse_mana_braces(row.mana_cost) if row.mana_cost else ManaAmount()
    return compile_oracle_text(
        oracle_id=f"oracle:{slug}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=cost,
        mana_value=row.mana_value,
    )


def test_mana_echoes_compiles_and_rediscovers_with_sliver_queen():
    report = _compile("Mana Echoes")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    trig = next(a for a in report.semantics.abilities if isinstance(a, TriggeredAbility))
    assert trig.filter == "creature"
    effect = trig.effects[0]
    assert isinstance(effect, AddManaEffect)
    assert effect.mana_scale is ManaScaleKind.CONTROLLED_SHARING_CREATURE_TYPE
    assert effect.scale_color == "colorless"
    echoes = report.semantics
    queen = _compile("Sliver Queen").semantics
    found = explore_pair(echoes, queen, max_depth=10)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    assert "Mana Echoes" in {c.name for c in found.witness.essential_cards}
