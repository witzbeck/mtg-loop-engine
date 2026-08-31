"""M5 mill/graveyard feedback: Bloodchief Ascension + Mindcrank class."""

from mtg_loop_engine.semantics.compiler import compile_oracle_text
from mtg_loop_engine.semantics.enums import SemanticCoverage, TriggerEvent
from mtg_loop_engine.semantics.ir import LoseLifeEffect, MillEffect, TriggeredAbility
from mtg_loop_engine.semantics.real_oracle_curriculum import REAL_ORACLE_CURRICULUM


def _compile(key: str):
    row = REAL_ORACLE_CURRICULUM[key]
    return compile_oracle_text(
        oracle_id=f"oracle:{key.lower().replace(' ', '-').replace(',', '')}",
        name=row.name,
        oracle_text=row.oracle_text,
        types=row.types,
    )


def test_bloodchief_and_mindcrank_compile_complete():
    bloodchief = _compile("Bloodchief Ascension")
    mindcrank = _compile("Mindcrank")
    assert bloodchief.coverage == SemanticCoverage.COMPLETE
    assert mindcrank.coverage == SemanticCoverage.COMPLETE
    gy_tr = next(
        a
        for a in bloodchief.semantics.abilities
        if isinstance(a, TriggeredAbility)
        and a.event == TriggerEvent.CARD_TO_OPPONENT_GRAVEYARD
    )
    mill_tr = next(
        a
        for a in mindcrank.semantics.abilities
        if isinstance(a, TriggeredAbility)
    )
    assert isinstance(gy_tr.effects[0], LoseLifeEffect)
    assert gy_tr.effects[0].amount == 2
    assert mill_tr.event == TriggerEvent.OPPONENT_LOSE_LIFE
    assert isinstance(mill_tr.effects[0], MillEffect)


def test_bloodchief_mindcrank_blind_discovery():
    from mtg_loop_engine.proofs.models import NetStateDelta
    from mtg_loop_engine.search.explorer import explore_pair
    from mtg_loop_engine.semantics.enums import Consequence
    from mtg_loop_engine.verify.verifier import Verifier

    bloodchief = _compile("Bloodchief Ascension").semantics
    mindcrank = _compile("Mindcrank").semantics
    hit = explore_pair(
        bloodchief,
        mindcrank,
        max_depth=8,
        expected_net_state=NetStateDelta(life_opponent=-2),
        expected_claim_consequence=Consequence.LETHAL,
        verifier=Verifier(),
    )
    assert hit is not None
    assert hit.proof.status.value == "verified"
    assert "discovered_without_pair_labels" in hit.witness.assumptions
