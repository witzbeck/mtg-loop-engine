"""M5 path-a slice 9: scaled tap-mana (frontier P0 cluster)."""

import pytest

from mtg_loop_engine.search.explorer import (
    CREATURE_MANA_SEED_ORACLE_ID,
    default_initial_state,
    explore_pair,
)
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import ManaScaleKind, SemanticCoverage, VerificationStatus
from mtg_loop_engine.semantics.ir import ActivatedAbility, AddManaEffect
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
    "key,scale",
    [
        ("Circle of Dreams Druid", ManaScaleKind.CONTROLLED_CREATURES),
        ("Priest of Titania", ManaScaleKind.BATTLEFIELD_ELF),
        ("Elvish Archdruid", ManaScaleKind.CONTROLLED_ELF),
        ("Overgrown Battlement", ManaScaleKind.CONTROLLED_DEFENDERS),
        ("Sanctum Weaver", ManaScaleKind.CONTROLLED_ENCHANTMENTS),
        ("Axebane Guardian", ManaScaleKind.CONTROLLED_DEFENDERS),
        ("Karametra's Acolyte", ManaScaleKind.DEVOTION_GREEN),
        ("Bloom Tender", ManaScaleKind.VIVID_PERMANENT_COLORS),
    ],
)
def test_scaled_tap_mana_cards_compile_complete(key: str, scale: ManaScaleKind):
    report = _compile(key)
    assert report.coverage == SemanticCoverage.COMPLETE, report.semantics.unsupported_fragments
    ability = next(a for a in report.semantics.abilities if isinstance(a, ActivatedAbility))
    effect = ability.effects[0]
    assert isinstance(effect, AddManaEffect)
    assert effect.mana_scale == scale


def test_creature_count_mana_stays_fail_closed_for_unsupported_shape():
    report = compile_oracle_text(
        oracle_id="oracle:false-creature-count",
        name="False Creature Count",
        oracle_text="{T}: Add {G} for each card in your hand.",
        types=["Creature"],
    )
    assert report.coverage == SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF
    assert report.semantics.relevant_unsupported()


def test_circle_of_dreams_seeds_extra_creatures_for_staff_cycle():
    circle = _compile("Circle of Dreams Druid").semantics
    staff = _compile("Staff of Domination").semantics
    spec = default_initial_state(circle, staff)
    seed_ids = {p.oracle_id for p in spec.permanents}
    assert CREATURE_MANA_SEED_ORACLE_ID in seed_ids
    creature_count = sum(1 for p in spec.permanents if p.is_creature)
    assert creature_count >= 4
    assert sum(1 for p in spec.permanents if p.oracle_id == CREATURE_MANA_SEED_ORACLE_ID) == 3


def test_circle_of_dreams_plus_staff_rediscovers():
    circle = _compile("Circle of Dreams Druid").semantics
    staff = _compile("Staff of Domination").semantics
    found = explore_pair(circle, staff, max_depth=8)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert names == {"Circle of Dreams Druid", "Staff of Domination"}


def test_bloom_tender_plus_freed_compiles_both_complete():
    bloom = _compile("Bloom Tender")
    freed = _compile("Freed from the Real")
    assert bloom.coverage == SemanticCoverage.COMPLETE
    assert freed.coverage == SemanticCoverage.COMPLETE
