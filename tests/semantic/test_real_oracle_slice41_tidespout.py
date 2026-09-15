"""M5 slice 41: Tidespout Tyrant CAST bounce + Sol Ring rediscovery."""

from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent, VerificationStatus
from mtg_loop_engine.semantics.ir import ManaAmount, MoveToZoneEffect, TriggeredAbility
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    slug = key.lower().replace(" ", "-").replace("'", "")
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


def test_tidespout_compiles_cast_bounce():
    report = _compile("Tidespout Tyrant")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    trig = next(
        a
        for a in report.semantics.abilities
        if isinstance(a, TriggeredAbility) and a.event == TriggerEvent.CAST
    )
    effect = trig.effects[0]
    assert isinstance(effect, MoveToZoneEffect)
    assert effect.target == "target_permanent"


def test_sol_ring_compiles_complete():
    report = _compile("Sol Ring")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments


def test_tidespout_plus_sol_ring_rediscovers():
    tide = _compile("Tidespout Tyrant").semantics
    ring = _compile("Sol Ring").semantics
    found = explore_pair(tide, ring, max_depth=12)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert names == {"Tidespout Tyrant", "Sol Ring"}
    assert any(s.op == "cast_from_hand" for s in found.witness.loop_actions)
