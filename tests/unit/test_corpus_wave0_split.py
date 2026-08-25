"""Coverage anchors for Wave 0 corpus split helpers."""

from mtg_loop_engine.corpus import oracle_gap_catalog, physics_hard_negatives
from mtg_loop_engine.corpus.physics_fixtures.hard_negatives import (
    all_physics_hard_negatives,
)


def test_oracle_gap_catalog_empty_in_wave0():
    assert oracle_gap_catalog() == []


def test_physics_hard_negative_aliases_agree():
    a = physics_hard_negatives()
    b = all_physics_hard_negatives()
    assert len(a) == 10
    assert [w.id for w in a] == [w.id for w in b]
