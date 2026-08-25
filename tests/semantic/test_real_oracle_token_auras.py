"""M5 path-a: Presence of Gond host-tap tokens + false-COMPLETE aura gate."""

from mtg_loop_engine.search.explorer import (
    AURA_HOST_OBJECT_ID,
    default_initial_state,
    explore_pair,
)
from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, VerificationStatus
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


def test_aura_host_seed_is_non_token_setup_permanent():
    gond = _compile("Presence of Gond").semantics
    alarm = _compile("Intruder Alarm Live").semantics
    spec = default_initial_state(gond, alarm)
    host = next(p for p in spec.permanents if p.object_id == AURA_HOST_OBJECT_ID)
    assert host.is_token is False
    assert host.is_creature is True


def test_presence_of_gond_plus_midnight_guard_discovers():
    gond = _compile("Presence of Gond").semantics
    guard = _compile("Midnight Guard").semantics
    found = explore_pair(gond, guard, max_depth=8)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    names = {c.name for c in found.witness.essential_cards}
    assert names == {"Presence of Gond", "Midnight Guard"}


def test_presence_of_gond_plus_intruder_alarm_discovers_with_host_in_d():
    gond = _compile("Presence of Gond").semantics
    alarm = _compile("Intruder Alarm Live").semantics
    found = explore_pair(gond, alarm, max_depth=8)
    assert found is not None
    assert found.proof.status == VerificationStatus.VERIFIED
    dim = next(
        (
            d
            for d in found.witness.relevant_state.dimensions
            if d.path == f"permanents.{AURA_HOST_OBJECT_ID}.tapped"
        ),
        None,
    )
    assert dim is not None, "aura-host tapped must be in LoopRelevantState"
    assert dim.value is False


def test_gond_without_untapper_does_not_verify_as_loop():
    """Finite host-tap + ETB damage / bystander must not accept as a recurring loop."""
    gond = _compile("Presence of Gond").semantics
    for partner_key in ("Impact Tremors", "Warleader's Call", "Basalt Monolith Live"):
        partner = _compile(partner_key).semantics
        found = explore_pair(gond, partner, max_depth=8)
        assert found is None, f"expected no verified loop for Gond + {partner_key}"
