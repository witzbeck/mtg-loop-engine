"""Executor contracts for board-scaled tap mana (M5 slice 9)."""

from mtg_loop_engine.proofs.models import InitialStateSpec, PermanentSpec
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.enums import ManaScaleKind, SemanticCoverage
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    AddManaEffect,
    CardSemantics,
    ManaAmount,
    ManaCost,
    ProofIrrelevantStatic,
    TapCost,
)
from mtg_loop_engine.state.game import GameState


def _elf(oid: str, name: str) -> CardSemantics:
    return CardSemantics(
        oracle_id=oid,
        name=name,
        types=["Creature", "Elf"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )


def test_controlled_creature_count_adds_green_per_creature():
    sem = CardSemantics(
        oracle_id="oracle:circle",
        name="Circle",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="tap-creature-count",
                costs=[TapCost()],
                effects=[
                    AddManaEffect(
                        mana_scale=ManaScaleKind.CONTROLLED_CREATURES,
                        scale_color="green",
                    )
                ],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    semantics = {
        sem.oracle_id: sem,
        "oid:e1": _elf("oid:e1", "E1"),
        "oid:e2": _elf("oid:e2", "E2"),
    }
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="c0",
                    oracle_id=sem.oracle_id,
                    name="Circle",
                    is_creature=True,
                ),
                PermanentSpec(
                    object_id="c1",
                    oracle_id="oid:e1",
                    name="E1",
                    is_creature=True,
                ),
                PermanentSpec(
                    object_id="c2",
                    oracle_id="oid:e2",
                    name="E2",
                    is_creature=True,
                ),
            ]
        )
    )
    err = Executor(semantics).apply_effects(
        state,
        state.permanents["c0"],
        [
            AddManaEffect(
                mana_scale=ManaScaleKind.CONTROLLED_CREATURES,
                scale_color="green",
            )
        ],
        target_id=None,
    )
    assert err is None
    assert state.mana.green == 3


def test_battlefield_elf_count_includes_all_elves():
    sem = CardSemantics(
        oracle_id="oracle:priest",
        name="Priest",
        types=["Creature", "Elf"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    semantics = {sem.oracle_id: sem, "oid:e1": _elf("oid:e1", "E1")}
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="c0",
                    oracle_id=sem.oracle_id,
                    name="Priest",
                    is_creature=True,
                ),
                PermanentSpec(
                    object_id="c1",
                    oracle_id="oid:e1",
                    name="E1",
                    is_creature=True,
                ),
            ]
        )
    )
    err = Executor(semantics).apply_effects(
        state,
        state.permanents["c0"],
        [
            AddManaEffect(
                mana_scale=ManaScaleKind.BATTLEFIELD_ELF,
                scale_color="green",
            )
        ],
        target_id=None,
    )
    assert err is None
    assert state.mana.green == 2


def test_controlled_defender_count():
    sem = CardSemantics(
        oracle_id="oracle:wall",
        name="Wall",
        types=["Creature"],
        abilities=[
            ProofIrrelevantStatic(ability_id="def", clause="Defender"),
            ActivatedAbility(
                ability_id="tap-def",
                costs=[TapCost()],
                effects=[
                    AddManaEffect(
                        mana_scale=ManaScaleKind.CONTROLLED_DEFENDERS,
                        scale_color="green",
                    )
                ],
            ),
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    defender = CardSemantics(
        oracle_id="oid:d1",
        name="D1",
        types=["Creature"],
        abilities=[ProofIrrelevantStatic(ability_id="d", clause="Defender")],
        coverage=SemanticCoverage.COMPLETE,
    )
    semantics = {sem.oracle_id: sem, defender.oracle_id: defender}
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="c0",
                    oracle_id=sem.oracle_id,
                    name="Wall",
                    is_creature=True,
                ),
                PermanentSpec(
                    object_id="c1",
                    oracle_id=defender.oracle_id,
                    name="D1",
                    is_creature=True,
                ),
            ]
        )
    )
    err = Executor(semantics).apply_effects(
        state,
        state.permanents["c0"],
        [
            AddManaEffect(
                mana_scale=ManaScaleKind.CONTROLLED_DEFENDERS,
                scale_color="green",
            )
        ],
        target_id=None,
    )
    assert err is None
    assert state.mana.green == 2


def test_vivid_adds_one_per_color_among_controlled():
    freed = CardSemantics(
        oracle_id="oracle:freed",
        name="Freed",
        types=["Enchantment", "Aura"],
        abilities=[
            ActivatedAbility(
                ability_id="untap-enchanted",
                costs=[ManaCost(amount=ManaAmount(blue=1))],
                effects=[],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    bloom = CardSemantics(
        oracle_id="oracle:bloom",
        name="Bloom",
        types=["Creature", "Elf"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    semantics = {bloom.oracle_id: bloom, freed.oracle_id: freed}
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="c0",
                    oracle_id=bloom.oracle_id,
                    name="Bloom",
                    is_creature=True,
                ),
                PermanentSpec(
                    object_id="e0",
                    oracle_id=freed.oracle_id,
                    name="Freed",
                ),
            ]
        )
    )
    err = Executor(semantics).apply_effects(
        state,
        state.permanents["c0"],
        [AddManaEffect(mana_scale=ManaScaleKind.VIVID_PERMANENT_COLORS)],
        target_id=None,
    )
    assert err is None
    assert state.mana.blue == 1


def test_devotion_green_counts_green_pips_in_activated_costs():
    sem = CardSemantics(
        oracle_id="oracle:karametra",
        name="Karametra",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="other",
                costs=[ManaCost(amount=ManaAmount(green=2))],
                effects=[],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    semantics = {sem.oracle_id: sem}
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="c0",
                    oracle_id=sem.oracle_id,
                    name="Karametra",
                    is_creature=True,
                )
            ]
        )
    )
    err = Executor(semantics).apply_effects(
        state,
        state.permanents["c0"],
        [
            AddManaEffect(
                mana_scale=ManaScaleKind.DEVOTION_GREEN,
                scale_color="green",
            )
        ],
        target_id=None,
    )
    assert err is None
    assert state.mana.green == 2


def test_controlled_elf_count_only_your_elves():
    archdruid = CardSemantics(
        oracle_id="oracle:archdruid",
        name="Archdruid",
        types=["Creature", "Elf"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    semantics = {
        archdruid.oracle_id: archdruid,
        "oid:e1": _elf("oid:e1", "E1"),
    }
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="c0",
                    oracle_id=archdruid.oracle_id,
                    name="Archdruid",
                    is_creature=True,
                ),
                PermanentSpec(
                    object_id="c1",
                    oracle_id="oid:e1",
                    name="E1",
                    is_creature=True,
                ),
            ]
        )
    )
    err = Executor(semantics).apply_effects(
        state,
        state.permanents["c0"],
        [
            AddManaEffect(
                mana_scale=ManaScaleKind.CONTROLLED_ELF,
                scale_color="green",
            )
        ],
        target_id=None,
    )
    assert err is None
    assert state.mana.green == 2


def test_defender_scale_any_color_adds_to_any_color_pool():
    axebane = CardSemantics(
        oracle_id="oracle:axe",
        name="Axebane",
        types=["Creature"],
        abilities=[
            ProofIrrelevantStatic(ability_id="def", clause="Defender"),
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    wall = CardSemantics(
        oracle_id="oid:w",
        name="Wall",
        types=["Creature"],
        abilities=[ProofIrrelevantStatic(ability_id="d", clause="Defender")],
        coverage=SemanticCoverage.COMPLETE,
    )
    semantics = {axebane.oracle_id: axebane, wall.oracle_id: wall}
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="c0",
                    oracle_id=axebane.oracle_id,
                    name="Axebane",
                    is_creature=True,
                ),
                PermanentSpec(
                    object_id="c1",
                    oracle_id=wall.oracle_id,
                    name="Wall",
                    is_creature=True,
                ),
            ]
        )
    )
    err = Executor(semantics).apply_effects(
        state,
        state.permanents["c0"],
        [
            AddManaEffect(
                mana_scale=ManaScaleKind.CONTROLLED_DEFENDERS,
                scale_color="any_color",
            )
        ],
        target_id=None,
    )
    assert err is None
    assert state.mana.any_color == 2


def test_capabilities_tags_scaled_mana_produces():
    from mtg_loop_engine.interactions.capabilities import extract_capabilities

    card = CardSemantics(
        oracle_id="oracle:test",
        name="Test",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="t",
                costs=[TapCost()],
                effects=[
                    AddManaEffect(
                        mana_scale=ManaScaleKind.CONTROLLED_CREATURES,
                        scale_color="green",
                    )
                ],
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )
    caps = extract_capabilities(card)
    assert "mana_scale_creature" in caps.produces
    assert caps.needs_creature_count_mana_seed()

    weaver = CardSemantics(
        oracle_id="oracle:weaver",
        name="Weaver",
        types=["Creature"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    freed = CardSemantics(
        oracle_id="oracle:freed",
        name="Freed",
        types=["Enchantment", "Aura"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    impact = CardSemantics(
        oracle_id="oracle:impact",
        name="Impact Tremors",
        types=["Enchantment"],
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )
    semantics = {
        weaver.oracle_id: weaver,
        freed.oracle_id: freed,
        impact.oracle_id: impact,
    }
    state = GameState.from_spec(
        InitialStateSpec(
            permanents=[
                PermanentSpec(
                    object_id="c0",
                    oracle_id=weaver.oracle_id,
                    name="Weaver",
                    is_creature=True,
                ),
                PermanentSpec(
                    object_id="e0",
                    oracle_id=freed.oracle_id,
                    name="Freed",
                ),
                PermanentSpec(
                    object_id="e1",
                    oracle_id=impact.oracle_id,
                    name="Impact",
                ),
            ]
        )
    )
    err = Executor(semantics).apply_effects(
        state,
        state.permanents["c0"],
        [
            AddManaEffect(
                mana_scale=ManaScaleKind.CONTROLLED_ENCHANTMENTS,
                scale_color="any_color",
            )
        ],
        target_id=None,
    )
    assert err is None
    assert state.mana.any_color == 2
