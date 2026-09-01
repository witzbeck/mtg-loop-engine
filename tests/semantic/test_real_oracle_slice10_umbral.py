"""M5 path-a slice 10: Umbral Mantle {Q} untap-symbol equipment grant."""

from mtg_loop_engine.search.explorer import default_initial_state, explore_pair
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, VerificationStatus
from mtg_loop_engine.semantics.ir import ActivatedAbility, ManaCost, UntapSymbolCost
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-').replace(chr(39), '')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
    )


def test_umbral_mantle_compiles_equipped_untap_pump():
    report = _compile("Umbral Mantle")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    ab = next(a for a in report.semantics.abilities if isinstance(a, ActivatedAbility))
    assert any(isinstance(c, ManaCost) and c.amount.generic == 3 for c in ab.costs)
    assert any(isinstance(c, UntapSymbolCost) and not c.source_self for c in ab.costs)
    assert ab.effects == []


def test_wrong_untap_symbol_wording_stays_unsupported():
    report = compile_oracle_text(
        oracle_id="oracle:false-untap-symbol",
        name="False Untap Symbol",
        oracle_text=(
            'Equipped creature has "{3}, {T}: This creature gets +2/+2 until end of turn."'
        ),
        types=["Artifact", "Equipment"],
    )
    assert report.coverage == SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF
    assert report.semantics.relevant_unsupported()


def test_umbral_mantle_plus_priest_of_titania_rediscovers():
    umbral = _compile("Umbral Mantle").semantics
    priest = _compile("Priest of Titania").semantics
    found = explore_pair(umbral, priest, max_depth=8)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert names == {"Umbral Mantle", "Priest of Titania"}


def test_umbral_mantle_plus_circle_of_dreams_druid_rediscovers():
    umbral = _compile("Umbral Mantle").semantics
    circle = _compile("Circle of Dreams Druid").semantics
    spec = default_initial_state(umbral, circle)
    assert any(p.is_creature and not p.is_token for p in spec.permanents)
    found = explore_pair(umbral, circle, max_depth=8)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
