"""M5 path-a slice 7: life-untap, self-ETB untap-all, counter-mana, ETB may-untap."""

from mtg_loop_engine.search.explorer import default_initial_state, explore_pair
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent, VerificationStatus
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    AddManaEffect,
    TriggeredAbility,
    UntapEffect,
)
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-').replace(',', '').replace(chr(39), '')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
    )


def test_famished_paladin_gain_life_untap_compiles_complete():
    report = _compile("Famished Paladin")
    assert report.coverage == SemanticCoverage.COMPLETE
    trig = next(a for a in report.semantics.abilities if isinstance(a, TriggeredAbility))
    assert trig.event == TriggerEvent.GAIN_LIFE
    assert isinstance(trig.effects[0], UntapEffect)
    assert trig.effects[0].target == "self"


def test_village_bell_ringer_self_etb_untap_all_compiles_complete():
    report = _compile("Village Bell-Ringer")
    assert report.coverage == SemanticCoverage.COMPLETE
    trig = next(a for a in report.semantics.abilities if isinstance(a, TriggeredAbility))
    assert trig.event == TriggerEvent.ENTER_BATTLEFIELD
    assert trig.filter == "self"
    assert isinstance(trig.effects[0], UntapEffect)
    assert trig.effects[0].target == "all_creatures"


def test_gyre_sage_counter_mana_compiles_complete():
    report = _compile("Gyre Sage")
    assert report.coverage == SemanticCoverage.COMPLETE
    ability = next(a for a in report.semantics.abilities if isinstance(a, ActivatedAbility))
    effect = ability.effects[0]
    assert isinstance(effect, AddManaEffect)
    assert effect.equal_to_source_p1p1_counters == "green"


def test_pestermite_etb_may_untap_compiles_complete():
    report = _compile("Pestermite")
    assert report.coverage == SemanticCoverage.COMPLETE
    trig = next(a for a in report.semantics.abilities if isinstance(a, TriggeredAbility))
    assert isinstance(trig.effects[0], UntapEffect)
    assert trig.effects[0].target == "target_permanent"


def test_counter_mana_without_counters_stays_unsupported_shape():
    """Power-scaled mana must not silently absorb counter-mana wording."""
    report = compile_oracle_text(
        oracle_id="oracle:false-counter-mana",
        name="False Counter Mana",
        oracle_text="{T}: Add {G} for each card in your hand.",
        types=["Creature"],
    )
    assert report.coverage == SemanticCoverage.PARTIAL_RELEVANT_TO_PROOF
    assert report.semantics.relevant_unsupported()


def test_gyre_sage_seeds_four_p1p1_counters():
    sage = _compile("Gyre Sage").semantics
    staff = _compile("Staff of Domination").semantics
    spec = default_initial_state(sage, staff)
    sage_perm = next(p for p in spec.permanents if p.name == "Gyre Sage")
    assert sage_perm.counters.get("p1p1") == 4


def test_gyre_sage_plus_staff_of_domination_rediscovers():
    sage = _compile("Gyre Sage").semantics
    staff = _compile("Staff of Domination").semantics
    found = explore_pair(sage, staff, max_depth=8)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert names == {"Gyre Sage", "Staff of Domination"}
