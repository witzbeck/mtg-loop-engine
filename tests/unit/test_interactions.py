"""Isolated capability joins and inverted-index neighborhoods."""

from mtg_loop_engine.interactions.capabilities import (
    CardCapabilities,
    extract_capabilities,
    join_reasons,
)
from mtg_loop_engine.interactions.index import InteractionIndex
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    AddManaEffect,
    CardSemantics,
    ContinuousCostReduction,
    CreateTokenEffect,
    DealDamageEffect,
    ManaAmount,
    ManaCost,
    SacrificeCost,
    TapCost,
    TriggeredAbility,
    UntapEffect,
)


def _tapper(oid: str = "t:tap") -> CardSemantics:
    return CardSemantics(
        oracle_id=oid,
        name="Tapper",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="tap-ping",
                costs=[TapCost()],
                effects=[DealDamageEffect(amount=1)],
            )
        ],
    )


def _untapper(oid: str = "t:untap") -> CardSemantics:
    return CardSemantics(
        oracle_id=oid,
        name="Untapper",
        types=["Enchantment"],
        abilities=[
            ActivatedAbility(
                ability_id="untap-target",
                costs=[],
                effects=[UntapEffect(target="target_permanent")],
            )
        ],
    )


def test_join_reasons_are_directional():
    tap = CardCapabilities(oracle_id="a", name="A", requires={"tap"})
    untap = CardCapabilities(oracle_id="b", name="B", produces={"untap"})
    assert join_reasons(tap, untap) == ["tap_untap"]
    assert join_reasons(untap, tap) == []


def test_join_reasons_cover_core_families():
    assert "etb_trigger" in join_reasons(
        CardCapabilities(oracle_id="a", name="A", produces={"token", "etb"}),
        CardCapabilities(oracle_id="b", name="B", triggers_on={"enter_battlefield"}),
    )
    assert "sac_recursion" in join_reasons(
        CardCapabilities(oracle_id="a", name="A", requires={"sac_self"}),
        CardCapabilities(oracle_id="b", name="B", produces={"gy_return"}),
    )
    assert "counter_reload" in join_reasons(
        CardCapabilities(oracle_id="a", name="A", requires={"remove_counter"}),
        CardCapabilities(oracle_id="b", name="B", produces={"add_counter"}),
    )
    assert "cost_reduce" in join_reasons(
        CardCapabilities(oracle_id="a", name="A", requires={"mana"}),
        CardCapabilities(oracle_id="b", name="B", modifies={"reduce_activation_cost"}),
    )


def test_extract_capabilities_from_ir():
    tapper = extract_capabilities(_tapper())
    assert "tap" in tapper.requires
    assert "damage" in tapper.produces
    reducer = extract_capabilities(
        CardSemantics(
            oracle_id="t:reduce",
            name="Reducer",
            abilities=[ContinuousCostReduction(ability_id="r", reduce_generic=1)],
        )
    )
    assert "reduce_activation_cost" in reducer.modifies


def test_inverted_index_pairs_complements_not_unrelated():
    tapper = _tapper()
    untapper = _untapper()
    unrelated = CardSemantics(
        oracle_id="t:noise",
        name="Noise",
        types=["Enchantment"],
        abilities=[
            ActivatedAbility(
                ability_id="ping",
                costs=[],
                effects=[DealDamageEffect(amount=1)],
            )
        ],
    )
    index = InteractionIndex([tapper, untapper, unrelated])
    pairs = {(p.left_id, p.right_id): p.reasons for p in index.candidate_pairs()}
    key = tuple(sorted((tapper.oracle_id, untapper.oracle_id)))
    assert key in pairs
    assert "tap_untap" in pairs[key]
    assert all(unrelated.oracle_id not in pair for pair in pairs)


def test_inverted_maps_drive_mana_cost_reduce_neighborhood():
    rock = CardSemantics(
        oracle_id="t:rock",
        name="Rock",
        types=["Artifact"],
        abilities=[
            ActivatedAbility(
                ability_id="tap-mana",
                costs=[TapCost()],
                effects=[AddManaEffect(amount=ManaAmount(colorless=3))],
                is_mana_ability=True,
            ),
            ActivatedAbility(
                ability_id="untap",
                costs=[ManaCost(amount=ManaAmount(generic=3))],
                effects=[UntapEffect(target="self")],
            ),
        ],
    )
    grounds = CardSemantics(
        oracle_id="t:grounds",
        name="Grounds",
        types=["Enchantment"],
        abilities=[ContinuousCostReduction(ability_id="reduce", reduce_generic=1)],
    )
    index = InteractionIndex([rock, grounds])
    assert rock.oracle_id in index.by_requires["mana"]
    assert grounds.oracle_id in index.by_modifies["reduce_activation_cost"]
    neighbors = index._complement_ids(rock.oracle_id)
    assert grounds.oracle_id in neighbors
    pairs = index.candidate_pairs()
    assert len(pairs) == 1
    assert "cost_reduce" in pairs[0].reasons


def test_etb_token_neighborhood_uses_trigger_map():
    maker = CardSemantics(
        oracle_id="t:maker",
        name="Maker",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="make",
                costs=[TapCost()],
                effects=[CreateTokenEffect(name="Spawn")],
            )
        ],
    )
    alarm = CardSemantics(
        oracle_id="t:alarm",
        name="Alarm",
        types=["Enchantment"],
        abilities=[
            TriggeredAbility(
                ability_id="untap",
                event=TriggerEvent.ENTER_BATTLEFIELD,
                filter="creature",
                effects=[UntapEffect(target="target_permanent")],
            )
        ],
    )
    index = InteractionIndex([maker, alarm])
    assert maker.oracle_id in index.by_produces["token"]
    assert alarm.oracle_id in index.by_triggers["enter_battlefield"]
    assert alarm.oracle_id in index._complement_ids(maker.oracle_id)
    reasons = index.candidate_pairs()[0].reasons
    assert "etb_trigger" in reasons


def test_index_drops_relevant_unsupported_cards():
    ok = _tapper()
    bad = CardSemantics(
        oracle_id="t:bad",
        name="Bad",
        coverage=SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF,
        abilities=[
            ActivatedAbility(
                ability_id="untap",
                costs=[],
                effects=[UntapEffect(target="target_permanent")],
            )
        ],
    )
    index = InteractionIndex([ok, bad, _untapper()])
    assert bad.oracle_id not in index.cards
    assert all(bad.oracle_id not in (p.left_id, p.right_id) for p in index.candidate_pairs())


def test_sac_token_capability_flags():
    outlet = CardSemantics(
        oracle_id="t:outlet",
        name="Outlet",
        abilities=[
            ActivatedAbility(
                ability_id="sac",
                costs=[SacrificeCost(selector="token_creature_controlled")],
                effects=[AddManaEffect(amount=ManaAmount(black=1))],
            )
        ],
    )
    caps = extract_capabilities(outlet)
    assert caps.needs_token_fodder()
    assert "sac_token" in caps.requires
