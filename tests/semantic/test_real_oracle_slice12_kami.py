"""M5 path-a slice 12: Kami +1/+1 amplify (frontier P0)."""

from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, VerificationStatus
from mtg_loop_engine.semantics.ir import ReplacementAmplifyP1P1Counters
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-').replace(chr(39), '')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
    )


def test_kami_of_whispered_hopes_compiles_complete():
    report = _compile("Kami of Whispered Hopes")
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    ab = next(
        a
        for a in report.semantics.abilities
        if isinstance(a, ReplacementAmplifyP1P1Counters)
    )
    assert ab.plus == 1
    assert ab.applies_to == "permanents_you_control"


def test_wrong_amplify_wording_stays_unsupported():
    report = compile_oracle_text(
        oracle_id="oracle:false-amplify",
        name="False Amplify",
        oracle_text=(
            "If one or more +1/+1 counters would be put on a permanent you control, "
            "that many plus two +1/+1 counters are put on that permanent instead."
        ),
        types=["Enchantment"],
    )
    assert report.coverage == SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF
    assert report.semantics.relevant_unsupported()


def test_kami_plus_freed_from_the_real_rediscovers():
    kami = _compile("Kami of Whispered Hopes").semantics
    freed = _compile("Freed from the Real").semantics
    found = explore_pair(kami, freed, max_depth=8)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert names == {"Kami of Whispered Hopes", "Freed from the Real"}
