"""M5 path-a: Presence of Gond host-tap tokens + false-COMPLETE aura gate."""

from mtg_loop_engine.search.explorer import explore_pair
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage
from mtg_loop_engine.semantics.ir import ActivatedAbility, CreateTokenEffect, TapCost
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-').replace(',', '').replace(chr(39), '')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
    )


def test_presence_of_gond_compiles_host_tap_token():
    report = _compile("Presence of Gond")
    assert report.coverage == SemanticCoverage.COMPLETE
    ab = next(a for a in report.semantics.abilities if isinstance(a, ActivatedAbility))
    assert any(isinstance(c, TapCost) and not c.source_self for c in ab.costs)
    assert isinstance(ab.effects[0], CreateTokenEffect)


def test_aphetto_alchemist_compiles_with_morph_irrelevant():
    report = _compile("Aphetto Alchemist")
    assert report.coverage == SemanticCoverage.COMPLETE
    assert any(a.kind == "proof_irrelevant_static" for a in report.semantics.abilities)


def test_splinter_twin_copy_grant_stays_unsupported():
    report = compile_oracle_text(
        oracle_id="oracle:splinter-twin",
        name="Splinter Twin",
        oracle_text=(
            "Enchant creature\n"
            'Enchanted creature has "{T}: Create a token that\'s a copy of this creature, '
            'except it has haste. Exile that token at the beginning of the next end step."'
        ),
        types=["Enchantment", "Aura"],
    )
    assert report.coverage == SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF
    assert report.semantics.relevant_unsupported()


def test_presence_of_gond_plus_midnight_guard_discovers():
    gond = _compile("Presence of Gond").semantics
    guard = _compile("Midnight Guard").semantics
    found = explore_pair(gond, guard, max_depth=8)
    assert found is not None
    names = {c.name for c in found.witness.essential_cards}
    assert names == {"Presence of Gond", "Midnight Guard"}
