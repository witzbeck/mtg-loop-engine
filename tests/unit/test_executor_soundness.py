"""P0 verifier soundness: targets, triggers, exile/DIES, summoning sickness."""

from mtg_loop_engine.corpus.gold_core.cases import (
    BLOOD_ARTIST,
    INTRUDER_ALARM,
    PHYREXIAN_ALTAR,
    REST_IN_PEACE,
    TOKEN_TAPPER,
)
from mtg_loop_engine.proofs.models import ActionStep, InitialStateSpec, PermanentSpec
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.semantics.enums import VerificationStatus, Zone
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    AddManaEffect,
    CardSemantics,
    CreateTokenEffect,
    ManaAmount,
    SacrificeCost,
    TapCost,
    TapEffect,
)
from mtg_loop_engine.state.game import GameState


def _altar_semantics() -> dict[str, CardSemantics]:
    return {PHYREXIAN_ALTAR.oracle_id: PHYREXIAN_ALTAR}


def _board(
    *permanents: PermanentSpec, semantics: dict[str, CardSemantics] | None = None
) -> tuple[GameState, Executor]:
    state = GameState.from_spec(InitialStateSpec(permanents=list(permanents)))
    return state, Executor(semantics or {})


# --- Explicit target revalidation ---


def test_sac_rejects_opponent_creature():
    state, ex = _board(
        PermanentSpec(
            object_id="altar",
            oracle_id=PHYREXIAN_ALTAR.oracle_id,
            name="Altar",
            is_artifact=True,
        ),
        PermanentSpec(
            object_id="opp",
            oracle_id="oracle:opp-beast",
            name="Opp Beast",
            controller="opponent",
            is_creature=True,
            power=2,
            toughness=2,
        ),
        PermanentSpec(
            object_id="mine",
            oracle_id="oracle:my-beast",
            name="My Beast",
            is_creature=True,
            power=1,
            toughness=1,
        ),
        semantics=_altar_semantics(),
    )
    err = ex.activate(
        state,
        ActionStep(
            op="activate",
            actor="altar",
            ability_id="altar-sac",
            target="opp",
        ),
    )
    assert err is not None
    assert err.status == VerificationStatus.ILLEGAL_TARGET


def test_sac_rejects_noncreature():
    state, ex = _board(
        PermanentSpec(
            object_id="altar",
            oracle_id=PHYREXIAN_ALTAR.oracle_id,
            name="Altar",
            is_artifact=True,
        ),
        PermanentSpec(
            object_id="rock",
            oracle_id="oracle:rock",
            name="Rock",
            is_artifact=True,
        ),
        semantics=_altar_semantics(),
    )
    err = ex.activate(
        state,
        ActionStep(
            op="activate",
            actor="altar",
            ability_id="altar-sac",
            target="rock",
        ),
    )
    assert err is not None
    assert err.status == VerificationStatus.ILLEGAL_TARGET


def test_sac_rejects_nontoken_for_token_selector():
    outlet = CardSemantics(
        oracle_id="oracle:token-outlet",
        name="Token Outlet",
        types=["Artifact"],
        abilities=[
            ActivatedAbility(
                ability_id="sac-token",
                costs=[SacrificeCost(selector="token_creature_controlled")],
                effects=[AddManaEffect(amount=ManaAmount(colorless=1))],
            )
        ],
    )
    state, ex = _board(
        PermanentSpec(
            object_id="outlet",
            oracle_id=outlet.oracle_id,
            name=outlet.name,
            is_artifact=True,
        ),
        PermanentSpec(
            object_id="beast",
            oracle_id="oracle:beast",
            name="Beast",
            is_creature=True,
            power=1,
            toughness=1,
        ),
        semantics={outlet.oracle_id: outlet},
    )
    err = ex.activate(
        state,
        ActionStep(
            op="activate",
            actor="outlet",
            ability_id="sac-token",
            target="beast",
        ),
    )
    assert err is not None
    assert err.status == VerificationStatus.ILLEGAL_TARGET


def test_sac_auto_pick_resource_deficit_when_empty():
    state, ex = _board(
        PermanentSpec(
            object_id="altar",
            oracle_id=PHYREXIAN_ALTAR.oracle_id,
            name="Altar",
            is_artifact=True,
        ),
        semantics=_altar_semantics(),
    )
    err = ex.activate(
        state,
        ActionStep(op="activate", actor="altar", ability_id="altar-sac"),
    )
    assert err is not None
    assert err.status == VerificationStatus.RESOURCE_DEFICIT


def test_sac_positive_controlled_creature():
    state, ex = _board(
        PermanentSpec(
            object_id="altar",
            oracle_id=PHYREXIAN_ALTAR.oracle_id,
            name="Altar",
            is_artifact=True,
        ),
        PermanentSpec(
            object_id="fodder",
            oracle_id="oracle:fodder",
            name="Fodder",
            is_creature=True,
            is_token=True,
            power=1,
            toughness=1,
        ),
        semantics=_altar_semantics(),
    )
    err = ex.activate(
        state,
        ActionStep(
            op="activate",
            actor="altar",
            ability_id="altar-sac",
            target="fodder",
        ),
    )
    assert err is None
    assert state.permanents["fodder"].zone == Zone.GRAVEYARD


def test_host_tap_rejects_opponent_creature():
    aura = CardSemantics(
        oracle_id="oracle:host-aura",
        name="Host Aura",
        types=["Enchantment"],
        abilities=[
            ActivatedAbility(
                ability_id="enchanted-tap",
                costs=[TapCost(source_self=False)],
                effects=[CreateTokenEffect(name="Elf", quantity=1)],
            )
        ],
    )
    state, ex = _board(
        PermanentSpec(
            object_id="aura",
            oracle_id=aura.oracle_id,
            name=aura.name,
        ),
        PermanentSpec(
            object_id="host",
            oracle_id="oracle:host",
            name="Host",
            controller="opponent",
            is_creature=True,
            power=1,
            toughness=1,
        ),
        semantics={aura.oracle_id: aura},
    )
    err = ex.activate(
        state,
        ActionStep(
            op="activate",
            actor="aura",
            ability_id="enchanted-tap",
            target="host",
        ),
    )
    assert err is not None
    assert err.status == VerificationStatus.ILLEGAL_TARGET


def test_host_tap_rejects_noncreature():
    aura = CardSemantics(
        oracle_id="oracle:host-aura",
        name="Host Aura",
        types=["Enchantment"],
        abilities=[
            ActivatedAbility(
                ability_id="enchanted-tap",
                costs=[TapCost(source_self=False)],
                effects=[CreateTokenEffect(name="Elf", quantity=1)],
            )
        ],
    )
    state, ex = _board(
        PermanentSpec(
            object_id="aura",
            oracle_id=aura.oracle_id,
            name=aura.name,
        ),
        PermanentSpec(
            object_id="rock",
            oracle_id="oracle:rock",
            name="Rock",
            is_artifact=True,
        ),
        semantics={aura.oracle_id: aura},
    )
    err = ex.activate(
        state,
        ActionStep(
            op="activate",
            actor="aura",
            ability_id="enchanted-tap",
            target="rock",
        ),
    )
    assert err is not None
    assert err.status == VerificationStatus.ILLEGAL_TARGET


def test_host_tap_positive_controlled_creature():
    aura = CardSemantics(
        oracle_id="oracle:host-aura",
        name="Host Aura",
        types=["Enchantment"],
        abilities=[
            ActivatedAbility(
                ability_id="enchanted-tap",
                costs=[TapCost(source_self=False)],
                effects=[CreateTokenEffect(name="Elf", quantity=1)],
            )
        ],
    )
    state, ex = _board(
        PermanentSpec(
            object_id="aura",
            oracle_id=aura.oracle_id,
            name=aura.name,
        ),
        PermanentSpec(
            object_id="host",
            oracle_id="oracle:host",
            name="Host",
            is_creature=True,
            power=1,
            toughness=1,
        ),
        semantics={aura.oracle_id: aura},
    )
    err = ex.activate(
        state,
        ActionStep(
            op="activate",
            actor="aura",
            ability_id="enchanted-tap",
            target="host",
        ),
    )
    assert err is None
    assert state.permanents["host"].tapped is True


def test_activate_rejects_opponent_controlled_permanent():
    state, ex = _board(
        PermanentSpec(
            object_id="opp_tapper",
            oracle_id=TOKEN_TAPPER.oracle_id,
            name=TOKEN_TAPPER.name,
            controller="opponent",
            is_creature=True,
            power=1,
            toughness=1,
        ),
        semantics={TOKEN_TAPPER.oracle_id: TOKEN_TAPPER},
    )
    err = ex.activate(
        state,
        ActionStep(
            op="activate",
            actor="opp_tapper",
            ability_id="tap-make-token",
        ),
    )
    assert err is not None
    assert err.status == VerificationStatus.ILLEGAL_ACTION


# --- Exact trigger matching ---


def test_resolve_trigger_wrong_ability_is_illegal():
    state, ex = _board(
        PermanentSpec(
            object_id="alarm",
            oracle_id=INTRUDER_ALARM.oracle_id,
            name=INTRUDER_ALARM.name,
        ),
        PermanentSpec(
            object_id="artist",
            oracle_id=BLOOD_ARTIST.oracle_id,
            name=BLOOD_ARTIST.name,
            is_creature=True,
            power=0,
            toughness=1,
        ),
        semantics={
            INTRUDER_ALARM.oracle_id: INTRUDER_ALARM,
            BLOOD_ARTIST.oracle_id: BLOOD_ARTIST,
        },
    )
    state.pending_triggers = [
        {"source_id": "alarm", "ability_id": "alarm-untap", "subject_id": "artist"}
    ]
    err = ex.resolve_trigger(
        state,
        ActionStep(op="resolve_trigger", actor="artist", ability_id="ba-drain"),
    )
    assert err is not None
    assert err.status == VerificationStatus.ILLEGAL_ACTION
    assert len(state.pending_triggers) == 1


def test_resolve_trigger_wrong_actor_is_illegal():
    state, ex = _board(
        PermanentSpec(
            object_id="alarm",
            oracle_id=INTRUDER_ALARM.oracle_id,
            name=INTRUDER_ALARM.name,
        ),
        PermanentSpec(
            object_id="artist",
            oracle_id=BLOOD_ARTIST.oracle_id,
            name=BLOOD_ARTIST.name,
            is_creature=True,
            power=0,
            toughness=1,
        ),
        semantics={
            INTRUDER_ALARM.oracle_id: INTRUDER_ALARM,
            BLOOD_ARTIST.oracle_id: BLOOD_ARTIST,
        },
    )
    state.pending_triggers = [
        {"source_id": "alarm", "ability_id": "alarm-untap", "subject_id": "artist"}
    ]
    err = ex.resolve_trigger(
        state,
        ActionStep(op="resolve_trigger", actor="artist", ability_id="alarm-untap"),
    )
    assert err is not None
    assert err.status == VerificationStatus.ILLEGAL_ACTION
    assert len(state.pending_triggers) == 1


def test_resolve_trigger_correct_match():
    state, ex = _board(
        PermanentSpec(
            object_id="alarm",
            oracle_id=INTRUDER_ALARM.oracle_id,
            name=INTRUDER_ALARM.name,
        ),
        PermanentSpec(
            object_id="tapper",
            oracle_id=TOKEN_TAPPER.oracle_id,
            name=TOKEN_TAPPER.name,
            is_creature=True,
            tapped=True,
            power=1,
            toughness=1,
        ),
        semantics={
            INTRUDER_ALARM.oracle_id: INTRUDER_ALARM,
            TOKEN_TAPPER.oracle_id: TOKEN_TAPPER,
        },
    )
    state.pending_triggers = [
        {"source_id": "alarm", "ability_id": "alarm-untap", "subject_id": "tapper"}
    ]
    err = ex.resolve_trigger(
        state,
        ActionStep(
            op="resolve_trigger",
            actor="alarm",
            ability_id="alarm-untap",
            target="tapper",
        ),
    )
    assert err is None
    assert state.permanents["tapper"].tapped is False
    assert state.pending_triggers == []


def test_resolve_trigger_unspecified_picks_favorably():
    """When actor/ability_id omitted, idx 0 may still resolve a valid pending trigger."""
    state, ex = _board(
        PermanentSpec(
            object_id="alarm",
            oracle_id=INTRUDER_ALARM.oracle_id,
            name=INTRUDER_ALARM.name,
        ),
        PermanentSpec(
            object_id="tapper",
            oracle_id=TOKEN_TAPPER.oracle_id,
            name=TOKEN_TAPPER.name,
            is_creature=True,
            tapped=True,
            power=1,
            toughness=1,
        ),
        semantics={
            INTRUDER_ALARM.oracle_id: INTRUDER_ALARM,
            TOKEN_TAPPER.oracle_id: TOKEN_TAPPER,
        },
    )
    state.pending_triggers = [
        {"source_id": "alarm", "ability_id": "alarm-untap", "subject_id": "tapper"}
    ]
    err = ex.resolve_trigger(
        state,
        ActionStep(op="resolve_trigger", target="tapper"),
    )
    assert err is None
    assert state.permanents["tapper"].tapped is False


# --- RIP / exile suppresses DIES ---


def test_die_under_rip_exiles_without_death_or_dies():
    state, ex = _board(
        PermanentSpec(
            object_id="rip",
            oracle_id=REST_IN_PEACE.oracle_id,
            name=REST_IN_PEACE.name,
        ),
        PermanentSpec(
            object_id="beast",
            oracle_id="oracle:beast",
            name="Beast",
            is_creature=True,
            power=1,
            toughness=1,
        ),
        PermanentSpec(
            object_id="artist",
            oracle_id=BLOOD_ARTIST.oracle_id,
            name=BLOOD_ARTIST.name,
            is_creature=True,
            power=0,
            toughness=1,
        ),
        semantics={
            REST_IN_PEACE.oracle_id: REST_IN_PEACE,
            BLOOD_ARTIST.oracle_id: BLOOD_ARTIST,
        },
    )
    death_before = state.event_counters.get("death", 0)
    sac_before = state.event_counters.get("sacrifice", 0)
    ex.sacrifice(state, state.permanents["beast"])
    assert state.event_counters.get("sacrifice", 0) == sac_before + 1
    assert state.event_counters.get("death", 0) == death_before
    assert state.permanents["beast"].zone == Zone.EXILE
    assert not any(t["ability_id"] == "ba-drain" for t in state.pending_triggers)


def test_die_to_graveyard_still_queues_dies():
    state, ex = _board(
        PermanentSpec(
            object_id="beast",
            oracle_id="oracle:beast",
            name="Beast",
            is_creature=True,
            power=1,
            toughness=1,
        ),
        PermanentSpec(
            object_id="artist",
            oracle_id=BLOOD_ARTIST.oracle_id,
            name=BLOOD_ARTIST.name,
            is_creature=True,
            power=0,
            toughness=1,
        ),
        semantics={BLOOD_ARTIST.oracle_id: BLOOD_ARTIST},
    )
    ex.sacrifice(state, state.permanents["beast"])
    assert state.permanents["beast"].zone == Zone.GRAVEYARD
    assert state.event_counters.get("death", 0) == 1
    assert any(t["ability_id"] == "ba-drain" for t in state.pending_triggers)


def test_sac_noncreature_artifact_does_not_bump_death():
    """events.death / OutputType.DEATH are creature-scoped; artifact GY still moves."""
    state, ex = _board(
        PermanentSpec(
            object_id="fodder",
            oracle_id="oracle:sol-ring",
            name="Sol Ring",
            is_artifact=True,
        ),
        PermanentSpec(
            object_id="artist",
            oracle_id=BLOOD_ARTIST.oracle_id,
            name=BLOOD_ARTIST.name,
            is_creature=True,
            power=0,
            toughness=1,
        ),
        semantics={BLOOD_ARTIST.oracle_id: BLOOD_ARTIST},
    )
    sac_before = state.event_counters.get("sacrifice", 0)
    ex.sacrifice(state, state.permanents["fodder"])
    assert state.permanents["fodder"].zone == Zone.GRAVEYARD
    assert state.event_counters.get("sacrifice", 0) == sac_before + 1
    assert state.event_counters.get("death", 0) == 0
    # DIES queued but Blood Artist filter="creature" skips noncreatures.
    assert not any(t["ability_id"] == "ba-drain" for t in state.pending_triggers)


def test_sac_creature_bumps_death():
    state, ex = _board(
        PermanentSpec(
            object_id="beast",
            oracle_id="oracle:beast",
            name="Beast",
            is_creature=True,
            power=1,
            toughness=1,
        ),
    )
    ex.sacrifice(state, state.permanents["beast"])
    assert state.permanents["beast"].zone == Zone.GRAVEYARD
    assert state.event_counters.get("death", 0) == 1
    assert state.event_counters.get("sacrifice", 0) == 1


# --- Summoning sickness on tap mana abilities ---


def _mana_tapper(*, sick: bool) -> tuple[GameState, Executor]:
    card = CardSemantics(
        oracle_id="oracle:joiner",
        name="Joiner",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="tap-mana",
                costs=[TapCost()],
                effects=[AddManaEffect(amount=ManaAmount(green=1))],
                is_mana_ability=True,
                uses_stack=False,
            )
        ],
    )
    return _board(
        PermanentSpec(
            object_id="joiner",
            oracle_id=card.oracle_id,
            name=card.name,
            is_creature=True,
            summoning_sick=sick,
            power=1,
            toughness=1,
        ),
        semantics={card.oracle_id: card},
    )


def test_sick_tap_mana_ability_is_timing_violation():
    state, ex = _mana_tapper(sick=True)
    err = ex.activate(
        state,
        ActionStep(op="activate", actor="joiner", ability_id="tap-mana"),
    )
    assert err is not None
    assert err.status == VerificationStatus.TIMING_VIOLATION


def test_nonsick_tap_mana_ability_succeeds():
    state, ex = _mana_tapper(sick=False)
    err = ex.activate(
        state,
        ActionStep(op="activate", actor="joiner", ability_id="tap-mana"),
    )
    assert err is None
    assert state.mana.green == 1
    assert state.permanents["joiner"].tapped is True


# --- TapEffect apply (compile→execute seam) ---


def _tap_effect_card() -> CardSemantics:
    return CardSemantics(
        oracle_id="oracle:tapper",
        name="Tapper",
        types=["Creature"],
        abilities=[
            ActivatedAbility(
                ability_id="do-tap",
                costs=[],
                effects=[TapEffect(target="target_permanent")],
            )
        ],
    )


def test_tap_effect_taps_explicit_target():
    card = _tap_effect_card()
    state, ex = _board(
        PermanentSpec(
            object_id="src",
            oracle_id=card.oracle_id,
            name=card.name,
            is_creature=True,
        ),
        PermanentSpec(
            object_id="host",
            oracle_id="oracle:host",
            name="Host",
            is_creature=True,
        ),
        semantics={card.oracle_id: card},
    )
    err = ex.activate(
        state,
        ActionStep(op="activate", actor="src", ability_id="do-tap", target="host"),
    )
    assert err is None
    assert state.permanents["host"].tapped is True
    assert state.event_counters.get("tap", 0) >= 1


def test_tap_effect_missing_target_is_illegal_target():
    card = _tap_effect_card()
    state, ex = _board(
        PermanentSpec(
            object_id="src",
            oracle_id=card.oracle_id,
            name=card.name,
            is_creature=True,
        ),
        semantics={card.oracle_id: card},
    )
    err = ex.activate(
        state,
        ActionStep(op="activate", actor="src", ability_id="do-tap"),
    )
    assert err is not None
    assert err.status == VerificationStatus.ILLEGAL_TARGET
