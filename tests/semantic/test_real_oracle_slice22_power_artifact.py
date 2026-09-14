"""M5 slice 22: Power Artifact enchanted-artifact cost reduction."""

from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, VerificationStatus
from mtg_loop_engine.semantics.ir import ContinuousCostReduction
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    slug = key.lower().replace(" ", "-")
    return compile_oracle_text(
        oracle_id=f"oracle:{slug}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
        colors=list(row.colors),
    )


def test_power_artifact_compiles_complete():
    report = _compile("Power Artifact")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    red = next(
        a for a in report.semantics.abilities if isinstance(a, ContinuousCostReduction)
    )
    assert red.reduce_generic == 2
    assert red.applies_to == "enchanted_artifact_activated"
    assert red.min_mana_remaining == 1


def test_power_artifact_plus_basalt_discovers():
    power = _compile("Power Artifact").semantics
    basalt = _compile("Basalt Monolith Live").semantics
    found = explore_pair(power, basalt, max_depth=8)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert "Power Artifact" in names
    assert "Basalt Monolith" in names
