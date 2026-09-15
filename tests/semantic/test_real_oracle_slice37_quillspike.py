"""M5 slice 37: Quillspike hybrid remove-m1m1 + Devoted Druid rediscovery."""

from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, VerificationStatus
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    HybridManaCost,
    ManaAmount,
    RemoveCounterCost,
)
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


def test_quillspike_compiles_hybrid_remove_m1m1():
    report = _compile("Quillspike")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    ab = next(a for a in report.semantics.abilities if isinstance(a, ActivatedAbility))
    hybrid = next(c for c in ab.costs if isinstance(c, HybridManaCost))
    assert hybrid.colors[0] == "green"
    assert "black" in hybrid.colors
    assert any(isinstance(c, RemoveCounterCost) for c in ab.costs)
    assert ab.effects == []


def test_quillspike_plus_devoted_druid_rediscovers():
    quill = _compile("Quillspike").semantics
    druid = _compile("Devoted Druid").semantics
    found = explore_pair(quill, druid, max_depth=12)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert names == {"Quillspike", "Devoted Druid"}


def test_quillspike_without_m1m1_partner_does_not_verify():
    quill = _compile("Quillspike").semantics
    earthcraft = _compile("Earthcraft").semantics
    found = explore_pair(quill, earthcraft, max_depth=10)
    assert found is None
