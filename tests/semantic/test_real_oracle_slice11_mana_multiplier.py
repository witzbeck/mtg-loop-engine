"""M5 path-a slice 11: tap-mana multiplier replacement (frontier P1)."""

import pytest

from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, VerificationStatus
from mtg_loop_engine.semantics.ir import ReplacementMultiplyTapMana
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-').replace(chr(39), '')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
    )


@pytest.mark.parametrize(
    "key,multiplier",
    [
        ("Mana Reflection", 2),
        ("Nyxbloom Ancient", 3),
    ],
)
def test_tap_mana_multiplier_cards_compile_complete(key: str, multiplier: int):
    report = _compile(key)
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    ab = next(
        a for a in report.semantics.abilities if isinstance(a, ReplacementMultiplyTapMana)
    )
    assert ab.multiplier == multiplier


def test_wrong_multiplier_wording_stays_unsupported():
    report = compile_oracle_text(
        oracle_id="oracle:false-multiplier",
        name="False Multiplier",
        oracle_text="If you tap a permanent for mana, it produces four times as much of that mana instead.",
        types=["Enchantment"],
    )
    assert report.coverage == SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF
    assert report.semantics.relevant_unsupported()


def test_basalt_monolith_plus_mana_reflection_rediscovers():
    basalt = _compile("Basalt Monolith Live").semantics
    reflection = _compile("Mana Reflection").semantics
    found = explore_pair(basalt, reflection, max_depth=8)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert names == {"Basalt Monolith", "Mana Reflection"}
