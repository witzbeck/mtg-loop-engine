"""M5 E57/E65: indestructible / hexproof / shroud grants as proof-irrelevant."""

from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.patterns import _parse_mana_braces
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    mana_cost = _parse_mana_braces(row.mana_cost) if row.mana_cost else None
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-').replace(',', '')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
        mana_cost=mana_cost,
        mana_value=row.mana_value,
    )


def test_e57_e65_keyword_grants_complete():
    for key in (
        "Lightning Greaves",
        "Darksteel Plate",
        "Anara, Wolvid Familiar",
        "Avacyn, Angel of Hope",
        "Myr Matrix",
    ):
        report = _compile(key)
        assert report.coverage == SemanticCoverage.COMPLETE, (
            key,
            report.semantics.unsupported_fragments,
        )


def test_metropolis_hexproof_with_reflect_complete():
    # Curriculum already has Metropolis Reformer from E02; hexproof must not block COMPLETE.
    report = _compile("Metropolis Reformer")
    assert report.coverage == SemanticCoverage.COMPLETE, (
        report.semantics.unsupported_fragments
    )


def test_grant_keyword_theater_stays_partial():
    report = compile_oracle_text(
        oracle_id="oracle:false-hex",
        name="False Hex",
        oracle_text="Creatures you control have hexproof and '{T}: Draw a card.'",
        types=["Enchantment"],
    )
    assert report.coverage == SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF
