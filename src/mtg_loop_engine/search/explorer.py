"""Bounded action-space explorer that emits LoopWitness candidates."""

from __future__ import annotations

from collections import deque

from pydantic import BaseModel

from mtg_loop_engine.corpus.builders import bf, two_card  # shared with gold fixtures
from mtg_loop_engine.eval.classify import analyze_prerequisites
from mtg_loop_engine.interactions.capabilities import extract_capabilities
from mtg_loop_engine.proofs.models import (
    ActionStep,
    Classification,
    EssentialCardRef,
    InitialStateSpec,
    LoopProof,
    LoopRelevantState,
    LoopWitness,
    NetStateDelta,
    OutputDelta,
    Prerequisite,
    StateDimension,
)
from mtg_loop_engine.rules.executor import Executor
from mtg_loop_engine.search.pruning import reusable_fingerprint
from mtg_loop_engine.semantics.enums import (
    ComparisonOp,
    Consequence,
    OutputType,
    Provenance,
    SemanticCoverage,
    TriggerEvent,
    VerificationStatus,
    Zone,
)
from mtg_loop_engine.semantics.provenance import provenance_of
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    AddCounterCost,
    AddCounterEffect,
    AddManaEffect,
    CardSemantics,
    CreateTokenEffect,
    DealDamageEffect,
    FreeCastCreaturesByManaValue,
    GrantLifelinkEffect,
    InstantGrantTapBounce,
    ManaAmount,
    ManaCost,
    MoveToZoneEffect,
    RemoveCounterCost,
    SacrificeCost,
    BounceControlledCost,
    TapCost,
    TriggeredAbility,
    UntapSymbolCost,
)
from mtg_loop_engine.semantics.oracle_fixtures import GOLD_ORACLE_FIXTURES
from mtg_loop_engine.state.game import GameState
from mtg_loop_engine.verify.verifier import Verifier


class ExploredWitness(BaseModel):
    """First sequence the injected verifier accepts for this pair.

    Explorer is the only verification call on the discovery path. `discover_loops`
    attaches join reasons; it does not verify again.
    """

    witness: LoopWitness
    proof: LoopProof


OUTPUT_EVENT_KEYS = {
    "mana": OutputType.MANA,
    "token": OutputType.TOKEN,
    "etb": OutputType.ETB,
    "cast": OutputType.CAST,
    "untap": OutputType.UNTAP,
    "damage": OutputType.DAMAGE,
    "life_gain": OutputType.LIFE_GAIN,
    "life_loss": OutputType.LIFE_LOSS,
    "mill": OutputType.MILL,
    "death": OutputType.DEATH,
    "sacrifice": OutputType.SACRIFICE,
    "draw": OutputType.DRAW,
}


MANA_DORK_SEED_ORACLE_ID = "setup:mana-dork-seed"
BOUNCE_CREATURE_SEED_ORACLE_ID = "setup:bounce-creature-seed"
BASIC_ISLAND_SEED_ORACLE_ID = "setup:basic-island"
BASIC_PLAINS_SEED_ORACLE_ID = "setup:basic-plains"
GRANT_HOST_OBJECT_ID = "grant-host"
_MANA_DORK_SEED_COUNT = 3


def _mana_dork_seed_semantics() -> CardSemantics:
    return CardSemantics(
        oracle_id=MANA_DORK_SEED_ORACLE_ID,
        name="Seed Mana Dork",
        types=["Creature"],
        mana_cost=ManaAmount(),
        mana_value=0,
        abilities=[
            ActivatedAbility(
                ability_id="seed-tap-mana",
                costs=[TapCost()],
                effects=[AddManaEffect(amount=ManaAmount(any_color=1))],
                is_mana_ability=True,
                uses_stack=False,
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )


def _basic_island_seed_semantics() -> CardSemantics:
    return CardSemantics(
        oracle_id=BASIC_ISLAND_SEED_ORACLE_ID,
        name="Seed Island",
        types=["Basic", "Land", "Island"],
        mana_cost=ManaAmount(),
        mana_value=0,
        abilities=[
            ActivatedAbility(
                ability_id="seed-island-tap",
                costs=[TapCost()],
                effects=[AddManaEffect(amount=ManaAmount(blue=1))],
                is_mana_ability=True,
                uses_stack=False,
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )


def _basic_plains_seed_semantics() -> CardSemantics:
    return CardSemantics(
        oracle_id=BASIC_PLAINS_SEED_ORACLE_ID,
        name="Seed Plains",
        types=["Basic", "Land", "Plains"],
        mana_cost=ManaAmount(),
        mana_value=0,
        abilities=[
            ActivatedAbility(
                ability_id="seed-plains-tap",
                costs=[TapCost()],
                effects=[AddManaEffect(amount=ManaAmount(white=1))],
                is_mana_ability=True,
                uses_stack=False,
            )
        ],
        coverage=SemanticCoverage.COMPLETE,
    )


def _bounce_creature_seed_semantics() -> CardSemantics:
    return CardSemantics(
        oracle_id=BOUNCE_CREATURE_SEED_ORACLE_ID,
        name="Seed Bounce Creature",
        types=["Creature"],
        mana_cost=ManaAmount(generic=1),
        mana_value=1,
        abilities=[],
        coverage=SemanticCoverage.COMPLETE,
    )


def _has_cast_bounce(card: CardSemantics) -> bool:
    return any(
        isinstance(ab, TriggeredAbility)
        and ab.event == TriggerEvent.CAST
        and any(isinstance(e, MoveToZoneEffect) for e in ab.effects)
        for ab in card.abilities
    )


def _has_etb_bounce_to_hand(card: CardSemantics) -> bool:
    return any(
        isinstance(ab, TriggeredAbility)
        and ab.event == TriggerEvent.ENTER_BATTLEFIELD
        and any(
            isinstance(e, MoveToZoneEffect)
            and e.zone == Zone.HAND
            and e.target
            in {
                "controlled_creature",
                "controlled_creature_green_or_white",
                "controlled_permanent",
                "controlled_nonland",
            }
            for e in ab.effects
        )
        for ab in card.abilities
    )


def _has_activated_bounce_other_creature(card: CardSemantics) -> bool:
    return any(
        isinstance(ab, ActivatedAbility)
        and any(
            isinstance(e, MoveToZoneEffect)
            and e.zone == Zone.HAND
            and e.target == "other_controlled_creature"
            for e in ab.effects
        )
        for ab in card.abilities
    )


def _has_cloudstone_bounce(card: CardSemantics) -> bool:
    return any(
        isinstance(ab, TriggeredAbility)
        and ab.event == TriggerEvent.ENTER_BATTLEFIELD
        and any(
            isinstance(e, MoveToZoneEffect)
            and e.zone == Zone.HAND
            and e.target == "other_controlled_sharing_type"
            for e in ab.effects
        )
        for ab in card.abilities
    )


def _has_earthcraft(card: CardSemantics) -> bool:
    from mtg_loop_engine.semantics.ir import TapCreatureCost, UntapEffect

    return any(
        isinstance(ab, ActivatedAbility)
        and any(isinstance(c, TapCreatureCost) for c in ab.costs)
        and any(
            isinstance(e, UntapEffect) and e.target == "target_basic_land"
            for e in ab.effects
        )
        for ab in card.abilities
    )


def _has_free_cast(card: CardSemantics) -> bool:
    return any(isinstance(ab, FreeCastCreaturesByManaValue) for ab in card.abilities)


def _has_instant_grant_tap_bounce(card: CardSemantics) -> bool:
    return any(isinstance(ab, InstantGrantTapBounce) for ab in card.abilities)


def _has_etb_untap_all_creatures(card: CardSemantics) -> bool:
    """Intruder Alarm / Village Bell-Ringer: ETB → untap all creatures."""
    from mtg_loop_engine.semantics.ir import UntapEffect

    return any(
        isinstance(ab, TriggeredAbility)
        and ab.event == TriggerEvent.ENTER_BATTLEFIELD
        and any(isinstance(e, UntapEffect) and e.target == "all_creatures" for e in ab.effects)
        for ab in card.abilities
    )


ZOMBIE_SEED_ORACLE_ID = "token:zombie-seed"
# Setup permanent for host-tap auras (Presence of Gond class). Not a loop-created
# token: must appear in LoopRelevantState so host tapped EXACT is checked.
AURA_HOST_OBJECT_ID = "aura-host"
AURA_HOST_ORACLE_ID = "setup:aura-host"

CREATURE_MANA_SEED_ORACLE_ID = "scaled-mana:creature-seed"
ELF_MANA_SEED_ORACLE_ID = "scaled-mana:elf-seed"
DEFENDER_MANA_SEED_ORACLE_ID = "scaled-mana:defender-seed"
HAND_ARTIFACT_SEED_ORACLE_ID = "gated-mana:hand-artifact-seed"
METALCRAFT_ARTIFACT_SEED_ORACLE_ID = "gated-mana:metalcraft-artifact-seed"
FEROCIOUS_CREATURE_SEED_ORACLE_ID = "gated-mana:ferocious-creature-seed"
TAP_PAIR_CREATURE_SEED_ORACLE_ID = "gated-mana:tap-pair-creature-seed"

_SCALED_MANA_SEED_COUNT = 3
_HAND_ARTIFACT_SEED_COUNT = 3
_METALCRAFT_EXTRA_ARTIFACTS = 2


def _scaled_mana_seed_semantics() -> dict[str, CardSemantics]:
    from mtg_loop_engine.semantics.ir import ProofIrrelevantStatic

    return {
        CREATURE_MANA_SEED_ORACLE_ID: CardSemantics(
            oracle_id=CREATURE_MANA_SEED_ORACLE_ID,
            name="Seed Creature",
            types=["Creature"],
            abilities=[],
            coverage=SemanticCoverage.COMPLETE,
        ),
        ELF_MANA_SEED_ORACLE_ID: CardSemantics(
            oracle_id=ELF_MANA_SEED_ORACLE_ID,
            name="Seed Elf",
            types=["Creature", "Elf"],
            abilities=[],
            coverage=SemanticCoverage.COMPLETE,
        ),
        DEFENDER_MANA_SEED_ORACLE_ID: CardSemantics(
            oracle_id=DEFENDER_MANA_SEED_ORACLE_ID,
            name="Seed Defender",
            types=["Creature"],
            abilities=[
                ProofIrrelevantStatic(
                    ability_id="seed-defender-static",
                    clause="Defender",
                )
            ],
            coverage=SemanticCoverage.COMPLETE,
        ),
        HAND_ARTIFACT_SEED_ORACLE_ID: CardSemantics(
            oracle_id=HAND_ARTIFACT_SEED_ORACLE_ID,
            name="Seed Hand Artifact",
            types=["Artifact"],
            abilities=[],
            coverage=SemanticCoverage.COMPLETE,
        ),
        METALCRAFT_ARTIFACT_SEED_ORACLE_ID: CardSemantics(
            oracle_id=METALCRAFT_ARTIFACT_SEED_ORACLE_ID,
            name="Seed Metalcraft Artifact",
            types=["Artifact"],
            abilities=[],
            coverage=SemanticCoverage.COMPLETE,
        ),
        FEROCIOUS_CREATURE_SEED_ORACLE_ID: CardSemantics(
            oracle_id=FEROCIOUS_CREATURE_SEED_ORACLE_ID,
            name="Seed Ferocious Creature",
            types=["Creature"],
            abilities=[],
            coverage=SemanticCoverage.COMPLETE,
        ),
        TAP_PAIR_CREATURE_SEED_ORACLE_ID: CardSemantics(
            oracle_id=TAP_PAIR_CREATURE_SEED_ORACLE_ID,
            name="Seed Tap-Pair Creature",
            types=["Creature"],
            abilities=[],
            coverage=SemanticCoverage.COMPLETE,
        ),
    }


def _inject_seed_semantics(
    spec: InitialStateSpec, semantics: dict[str, CardSemantics]
) -> None:
    seeds = _scaled_mana_seed_semantics()
    for perm in spec.permanents:
        if perm.oracle_id in seeds and perm.oracle_id not in semantics:
            semantics[perm.oracle_id] = seeds[perm.oracle_id]
    if any(p.oracle_id == ZOMBIE_SEED_ORACLE_ID for p in spec.permanents):
        semantics[ZOMBIE_SEED_ORACLE_ID] = CardSemantics(
            oracle_id=ZOMBIE_SEED_ORACLE_ID,
            name="Zombie",
            types=["Creature", "Zombie"],
            abilities=[],
            coverage=SemanticCoverage.COMPLETE,
        )
    if any(p.oracle_id == MANA_DORK_SEED_ORACLE_ID for p in spec.permanents):
        semantics[MANA_DORK_SEED_ORACLE_ID] = _mana_dork_seed_semantics()
    if any(p.oracle_id == BASIC_ISLAND_SEED_ORACLE_ID for p in spec.permanents):
        semantics[BASIC_ISLAND_SEED_ORACLE_ID] = _basic_island_seed_semantics()
    if any(p.oracle_id == BASIC_PLAINS_SEED_ORACLE_ID for p in spec.permanents):
        semantics[BASIC_PLAINS_SEED_ORACLE_ID] = _basic_plains_seed_semantics()
    if any(p.oracle_id == BOUNCE_CREATURE_SEED_ORACLE_ID for p in spec.permanents):
        semantics[BOUNCE_CREATURE_SEED_ORACLE_ID] = _bounce_creature_seed_semantics()
    if any(p.object_id == GRANT_HOST_OBJECT_ID for p in spec.permanents):
        semantics.setdefault(
            AURA_HOST_ORACLE_ID,
            CardSemantics(
                oracle_id=AURA_HOST_ORACLE_ID,
                name="Grant Host",
                types=["Creature"],
                abilities=[],
                coverage=SemanticCoverage.COMPLETE,
            ),
        )


def _needs_zombie_gate(card: CardSemantics) -> bool:
    return any(
        isinstance(ab, ActivatedAbility) and ab.requires_zombie for ab in card.abilities
    )


def _needs_creature_host(card: CardSemantics) -> bool:
    return any(
        isinstance(ab, ActivatedAbility)
        and any(
            (isinstance(c, TapCost) and not c.source_self and c.host == "creature")
            or (isinstance(c, UntapSymbolCost) and not c.source_self)
            for c in ab.costs
        )
        for ab in card.abilities
    )


def _needs_land_host(card: CardSemantics) -> bool:
    return any(
        isinstance(ab, ActivatedAbility)
        and any(
            isinstance(c, TapCost) and not c.source_self and c.host == "land"
            for c in ab.costs
        )
        for ab in card.abilities
    )


def _needs_white_basic_land(card: CardSemantics) -> bool:
    """Patrol Signaler class: self {Q} create paid with white (+ generic via second tap)."""
    from mtg_loop_engine.semantics.ir import ManaCost, UntapSymbolCost

    for ab in card.abilities:
        if not isinstance(ab, ActivatedAbility):
            continue
        has_self_q = any(
            isinstance(c, UntapSymbolCost) and c.source_self for c in ab.costs
        )
        has_white = any(
            isinstance(c, ManaCost) and c.amount.white > 0 for c in ab.costs
        )
        if has_self_q and has_white:
            return True
    return False


def _grant_lifelink_ability(card: CardSemantics) -> ActivatedAbility | None:
    for ab in card.abilities:
        if isinstance(ab, ActivatedAbility) and any(
            isinstance(e, GrantLifelinkEffect) for e in ab.effects
        ):
            return ab
    return None


def _mana_for_grant_lifelink(card: CardSemantics) -> ManaAmount | None:
    """Seed pool for one paid grant-lifelink activate ({1}{W} class).

    Generic cost is seeded as colorless so ``pay_mana`` can spend it (Path b
    style mana prerequisite — not a free grant op).
    """
    ab = _grant_lifelink_ability(card)
    if ab is None:
        return None
    for cost in ab.costs:
        if isinstance(cost, ManaCost):
            need = cost.amount
            return ManaAmount(
                white=need.white,
                blue=need.blue,
                black=need.black,
                red=need.red,
                green=need.green,
                colorless=need.colorless + need.generic,
                any_color=need.any_color,
            )
    return None


def _subtype_scaled_create_ability(card: CardSemantics) -> ActivatedAbility | None:
    for ab in card.abilities:
        if not isinstance(ab, ActivatedAbility) or not ab.supported:
            continue
        if any(
            isinstance(e, CreateTokenEffect) and e.quantity_equal_to_controlled_subtype
            for e in ab.effects
        ):
            return ab
    return None


def _mana_for_subtype_scaled_create(card: CardSemantics) -> ManaAmount | None:
    """Seed pool for one Squirrel Girl-class X-create activate.

    Seed as ``any_color`` so Altar sac repay (also any_color) can meet the same
    MINIMUM recurrence floor as the setup pool.
    """
    ab = _subtype_scaled_create_ability(card)
    if ab is None:
        return None
    for cost in ab.costs:
        if isinstance(cost, ManaCost):
            need = cost.amount
            total = (
                need.white
                + need.blue
                + need.black
                + need.red
                + need.green
                + need.colorless
                + need.generic
                + need.any_color
            )
            return ManaAmount(any_color=total) if total > 0 else None
    return None


def _subtype_token_seed_name(card: CardSemantics) -> str | None:
    ab = _subtype_scaled_create_ability(card)
    if ab is None:
        return None
    for e in ab.effects:
        if isinstance(e, CreateTokenEffect) and e.quantity_equal_to_controlled_subtype:
            return e.name
    return None


def default_initial_state(a: CardSemantics, b: CardSemantics) -> InitialStateSpec:
    """Place both cards on the battlefield with generic fodder/counters as needed."""
    ordered = sorted([a, b], key=lambda c: c.oracle_id)
    free_cast_partner = any(_has_free_cast(c) for c in ordered)
    instant_grant = any(_has_instant_grant_tap_bounce(c) for c in ordered)
    alarm_partner = any(_has_etb_untap_all_creatures(c) for c in ordered)
    activated_bounce = any(_has_activated_bounce_other_creature(c) for c in ordered)
    cloudstone_partner = any(_has_cloudstone_bounce(c) for c in ordered)
    earthcraft_partner = any(_has_earthcraft(c) for c in ordered)
    cast_bounce_partner = any(_has_cast_bounce(c) for c in ordered)
    permanents = []
    for i, card in enumerate(ordered):
        types = {t.lower() for t in card.types}
        # Instant grant cards are not battlefield permanents; setup grants instead.
        if _has_instant_grant_tap_bounce(card):
            continue
        caps = extract_capabilities(card)
        is_creature = "creature" in types
        is_artifact = "artifact" in types
        fix = GOLD_ORACLE_FIXTURES.get(card.oracle_id)
        if (
            is_creature
            and fix is not None
            and fix.power is not None
            and fix.toughness is not None
        ):
            power, toughness = fix.power, fix.toughness
        else:
            power = 1 if is_creature else None
            toughness = 1 if is_creature else None
        # Counter-mana engines need enough p1p1 to pay Staff-class untap:
        # {3} untap creature + {1} untap Staff in the same cycle.
        if caps.needs_p1p1_mana_seed():
            counters = {"p1p1": 4}
        elif caps.removes_p1p1():
            # 0/0 counter-removers need ≥2 so one ping leaves a legal creature (SBA).
            counters = {"p1p1": 2 if toughness == 0 else 1}
        else:
            counters = {}
        # Aluren + Drake/Lion: start bounce creature in hand for free recast.
        # Alarm + Drake/Lion: same — cast pays mana from seeded dorks.
        # Cloudstone + Aluren: cast creature from hand; bounce a second creature.
        # Earthcraft + Drake: cast from hand; hold priority to tap Drake, untap Island.
        # Tidespout + rock: start artifact in hand for cast→bounce→recast.
        start_zone = Zone.BATTLEFIELD
        if is_creature and _has_etb_bounce_to_hand(card) and (
            free_cast_partner or alarm_partner or earthcraft_partner
        ):
            start_zone = Zone.HAND
        elif is_creature and cloudstone_partner and free_cast_partner:
            start_zone = Zone.HAND
        elif is_artifact and not is_creature and cast_bounce_partner:
            start_zone = Zone.HAND
        permanents.append(
            bf(
                f"c{i}",
                card.oracle_id,
                card.name,
                is_creature=is_creature,
                is_artifact=is_artifact,
                counters=counters,
                power=power,
                toughness=toughness,
                colors=list(card.colors),
                zone=start_zone,
            )
        )
    need_token = any(extract_capabilities(c).needs_token_fodder() for c in ordered)
    need_token = need_token or _needs_mana_create_token_sac_bootstrap(ordered)
    subtype_seed = next(
        (n for c in ordered if (n := _subtype_token_seed_name(c)) is not None),
        None,
    )
    # Subtype X-create + Altar: seed enough named tokens so X ≥ mana cost and
    # sac can repay (SG + 3 Squirrels → X=4 for {1}{G}{G}{G}).
    if subtype_seed is not None and _needs_mana_create_token_sac_bootstrap(ordered):
        for i in range(3):
            permanents.append(
                bf(
                    f"subtype_seed_{i}",
                    f"token:{subtype_seed}",
                    subtype_seed,
                    is_creature=True,
                    is_token=True,
                    power=1,
                    toughness=1,
                )
            )
        need_token = False
    need_zombie = any(_needs_zombie_gate(c) for c in ordered)
    need_creature_host = any(_needs_creature_host(c) for c in ordered)
    has_creature = any(p.is_creature for p in permanents)
    # One generic Zombie token covers cast-from-GY gates and sac fodder when both apply.
    if need_zombie:
        permanents.append(
            bf(
                "seed",
                ZOMBIE_SEED_ORACLE_ID,
                "Zombie",
                is_creature=True,
                is_token=True,
                power=1,
                toughness=1,
            )
        )
    elif need_token:
        permanents.append(
            bf(
                "seed",
                "token:seed",
                "Seed",
                is_creature=True,
                is_token=True,
                power=1,
                toughness=1,
            )
        )
    # Presence of Gond class: tap a host creature (prefer partner; else seed).
    # Seed as a non-token setup permanent so derive_relevant_state tracks tapped.
    if need_creature_host and not has_creature:
        permanents.append(
            bf(
                AURA_HOST_OBJECT_ID,
                AURA_HOST_ORACLE_ID,
                "Aura Host",
                is_creature=True,
                is_token=False,
                power=1,
                toughness=1,
            )
        )
    # Knack/Helix + Alarm: mana dorks, grant host, creature in hand to bounce.
    # Drake/Lion + Alarm (no Aluren): mana dorks so cast_from_hand can pay MV.
    bounce_alarm_cast = (
        alarm_partner
        and any(_has_etb_bounce_to_hand(c) for c in ordered)
        and not free_cast_partner
    )
    if instant_grant and alarm_partner:
        for i in range(_MANA_DORK_SEED_COUNT):
            permanents.append(
                bf(
                    f"mana_dork_{i}",
                    MANA_DORK_SEED_ORACLE_ID,
                    "Seed Mana Dork",
                    is_creature=True,
                    power=1,
                    toughness=1,
                )
            )
        permanents.append(
            bf(
                GRANT_HOST_OBJECT_ID,
                AURA_HOST_ORACLE_ID,
                "Grant Host",
                is_creature=True,
                power=1,
                toughness=1,
            )
        )
        permanents.append(
            bf(
                "bounce_seed",
                BOUNCE_CREATURE_SEED_ORACLE_ID,
                "Seed Bounce Creature",
                is_creature=True,
                power=1,
                toughness=1,
                zone=Zone.HAND,
            )
        )
    elif bounce_alarm_cast:
        bounce_mv = max(
            (c.mana_value for c in ordered if _has_etb_bounce_to_hand(c)),
            default=0,
        )
        dork_n = max(_MANA_DORK_SEED_COUNT, bounce_mv)
        for i in range(dork_n):
            permanents.append(
                bf(
                    f"mana_dork_{i}",
                    MANA_DORK_SEED_ORACLE_ID,
                    "Seed Mana Dork",
                    is_creature=True,
                    power=1,
                    toughness=1,
                )
            )
    # Temur + Bell-Ringer: mana dorks pay bounce activation + recast after untap-all.
    elif activated_bounce and alarm_partner:
        # {1}{G} bounce + {2}{W} Bell-Ringer ≈ 5 any-color taps per cycle.
        for i in range(max(_MANA_DORK_SEED_COUNT, 5)):
            permanents.append(
                bf(
                    f"mana_dork_{i}",
                    MANA_DORK_SEED_ORACLE_ID,
                    "Seed Mana Dork",
                    is_creature=True,
                    power=1,
                    toughness=1,
                )
            )
    # Cloudstone + Aluren: need a second Creature on BF to bounce (type-share).
    if cloudstone_partner and free_cast_partner:
        has_bf_creature = any(
            p.is_creature and p.zone == Zone.BATTLEFIELD for p in permanents
        )
        has_hand_creature = any(
            p.is_creature and p.zone == Zone.HAND for p in permanents
        )
        if not has_hand_creature:
            permanents.append(
                bf(
                    "cloudstone_cast_seed",
                    BOUNCE_CREATURE_SEED_ORACLE_ID,
                    "Seed Bounce Creature",
                    is_creature=True,
                    power=1,
                    toughness=1,
                    zone=Zone.HAND,
                )
            )
        if not has_bf_creature:
            permanents.append(
                bf(
                    "cloudstone_bf_seed",
                    BOUNCE_CREATURE_SEED_ORACLE_ID,
                    "Seed Bounce Creature",
                    is_creature=True,
                    power=1,
                    toughness=1,
                )
            )
    if earthcraft_partner or any(_needs_land_host(c) for c in ordered):
        use_plains = any(_needs_white_basic_land(c) for c in ordered)
        if use_plains:
            permanents.append(
                bf(
                    "basic_plains",
                    BASIC_PLAINS_SEED_ORACLE_ID,
                    "Seed Plains",
                    is_creature=False,
                    is_artifact=False,
                )
            )
        else:
            permanents.append(
                bf(
                    "basic_island",
                    BASIC_ISLAND_SEED_ORACLE_ID,
                    "Seed Island",
                    is_creature=False,
                    is_artifact=False,
                )
            )
    pair_caps = [extract_capabilities(c) for c in ordered]
    if any(c.needs_creature_count_mana_seed() for c in pair_caps):
        for i in range(_SCALED_MANA_SEED_COUNT):
            permanents.append(
                bf(
                    f"scaled_creature_{i}",
                    CREATURE_MANA_SEED_ORACLE_ID,
                    "Seed Creature",
                    is_creature=True,
                    power=1,
                    toughness=1,
                )
            )
    if any(c.needs_elf_count_mana_seed() for c in pair_caps):
        for i in range(_SCALED_MANA_SEED_COUNT):
            permanents.append(
                bf(
                    f"scaled_elf_{i}",
                    ELF_MANA_SEED_ORACLE_ID,
                    "Seed Elf",
                    is_creature=True,
                    power=1,
                    toughness=1,
                )
            )
    if any(c.needs_defender_count_mana_seed() for c in pair_caps):
        for i in range(_SCALED_MANA_SEED_COUNT):
            permanents.append(
                bf(
                    f"scaled_defender_{i}",
                    DEFENDER_MANA_SEED_ORACLE_ID,
                    "Seed Defender",
                    is_creature=True,
                    power=0,
                    toughness=4,
                )
            )
    if any(c.needs_hand_artifact_mana_seed() for c in pair_caps):
        for i in range(_HAND_ARTIFACT_SEED_COUNT):
            permanents.append(
                bf(
                    f"hand_artifact_{i}",
                    HAND_ARTIFACT_SEED_ORACLE_ID,
                    "Seed Hand Artifact",
                    is_creature=False,
                    is_artifact=True,
                    zone=Zone.HAND,
                )
            )
    if any(c.needs_metalcraft_seed() for c in pair_caps):
        have = sum(1 for p in permanents if p.is_artifact and p.zone == Zone.BATTLEFIELD)
        for i in range(max(0, 3 - have)):
            permanents.append(
                bf(
                    f"metalcraft_artifact_{i}",
                    METALCRAFT_ARTIFACT_SEED_ORACLE_ID,
                    "Seed Metalcraft Artifact",
                    is_creature=False,
                    is_artifact=True,
                )
            )
    if any(c.needs_ferocious_seed() for c in pair_caps):
        permanents.append(
            bf(
                "ferocious_creature",
                FEROCIOUS_CREATURE_SEED_ORACLE_ID,
                "Seed Ferocious Creature",
                is_creature=True,
                power=4,
                toughness=4,
            )
        )
    if any(c.needs_tap_creature_pair_seed() for c in pair_caps):
        permanents.append(
            bf(
                "tap_pair_creature",
                TAP_PAIR_CREATURE_SEED_ORACLE_ID,
                "Seed Tap-Pair Creature",
                is_creature=True,
                power=1,
                toughness=1,
            )
        )
    mana = ManaAmount()
    for card in ordered:
        for seed_fn in (_mana_for_grant_lifelink, _mana_for_subtype_scaled_create):
            seed = seed_fn(card)
            if seed is None:
                continue
            mana = ManaAmount(
                white=mana.white + seed.white,
                blue=mana.blue + seed.blue,
                black=mana.black + seed.black,
                red=mana.red + seed.red,
                green=mana.green + seed.green,
                colorless=mana.colorless + seed.colorless,
                any_color=mana.any_color + seed.any_color,
            )
    # Tidespout + rock: seed colorless for the first cast (any_color repay from rock tap).
    if cast_bounce_partner:
        for card in ordered:
            types = {t.lower() for t in card.types}
            if "artifact" in types and "creature" not in types and card.mana_value > 0:
                mana = ManaAmount(
                    white=mana.white,
                    blue=mana.blue,
                    black=mana.black,
                    red=mana.red,
                    green=mana.green,
                    colorless=mana.colorless + card.mana_value,
                    any_color=mana.any_color,
                )
    # Sliver Queen + Mana Echoes: seed {2} so the first create can fire; ETB mana pays the rest.
    if _needs_mana_create_echoes_bootstrap(ordered):
        mana = ManaAmount(
            white=mana.white,
            blue=mana.blue,
            black=mana.black,
            red=mana.red,
            green=mana.green,
            colorless=mana.colorless + 2,
            any_color=mana.any_color,
        )
    return InitialStateSpec(permanents=permanents, mana=mana)


def _try_apply(executor: Executor, state: GameState, step: ActionStep) -> GameState | None:
    nxt = state.copy()
    err = executor.run_step(nxt, step)
    return None if err else nxt


def _effect_needs_permanent_target(ability: ActivatedAbility) -> bool:
    for effect in ability.effects:
        if getattr(effect, "target", None) in {
            "target_permanent",
            "target_basic_land",
            "target_artifact",
            "target_other_creature",
            "other_controlled_creature",
            "other_controlled_sharing_type",
            "controlled_creature",
            "controlled_creature_green_or_white",
            "controlled_permanent",
            "controlled_nonland",
            "target_nonland",
        }:
            return True
    return False


def _has_tap_creature_cost(ability: ActivatedAbility) -> bool:
    from mtg_loop_engine.semantics.ir import TapCreatureCost

    return any(isinstance(c, TapCreatureCost) for c in ability.costs)


def _any_target_damage(ability: ActivatedAbility) -> bool:
    return any(
        isinstance(e, DealDamageEffect) and e.target == "any_target"
        for e in ability.effects
    )


def _tap_cost_needs_host(ability: ActivatedAbility) -> bool:
    return any(isinstance(c, TapCost) and not c.source_self for c in ability.costs)


def _tap_cost_host_kind(ability: ActivatedAbility) -> str:
    for cost in ability.costs:
        if isinstance(cost, TapCost) and not cost.source_self:
            return cost.host
    return "creature"

def _untap_symbol_cost_needs_host(ability: ActivatedAbility) -> bool:
    return any(
        isinstance(c, UntapSymbolCost) and not c.source_self for c in ability.costs
    )


def _remove_counter_cost(ability: ActivatedAbility) -> RemoveCounterCost | None:
    for cost in ability.costs:
        if isinstance(cost, RemoveCounterCost):
            return cost
    return None


def _sac_selector(ability: ActivatedAbility) -> str | None:
    for cost in ability.costs:
        if isinstance(cost, SacrificeCost) and cost.selector != "self":
            return cost.selector
    return None


def _bounce_cost_selector(ability: ActivatedAbility) -> str | None:
    for cost in ability.costs:
        if isinstance(cost, BounceControlledCost):
            return cost.selector
    return None


def _fodder_ids(state: GameState, selector: str) -> list[str]:
    ids: list[str] = []
    for perm in state.permanents.values():
        if perm.zone != Zone.BATTLEFIELD or perm.controller != "you":
            continue
        if selector == "token_creature_controlled" and perm.is_token and perm.is_creature:
            ids.append(perm.object_id)
        elif selector == "creature_controlled" and perm.is_creature:
            ids.append(perm.object_id)
    # Prefer tokens so sac outlets do not eat essential creatures first.
    ids.sort(key=lambda oid: (not state.permanents[oid].is_token, oid))
    return ids


def _bounce_fodder_ids(executor: Executor, state: GameState, selector: str) -> list[str]:
    ids = [
        p.object_id
        for p in state.permanents.values()
        if executor.matches_bounce_selector(p, selector)
    ]
    ids.sort()
    return ids


def legal_steps(executor: Executor, state: GameState) -> list[ActionStep]:
    """Deterministic legal actions.

    With pending triggers, combo-player may hold priority to activate
    Earthcraft-class ``TapCreatureCost`` abilities and mana abilities
    (e.g. tap Drake before bounce; tap Sol Ring before Tidespout bounce).
    """
    steps: list[ActionStep] = []
    if state.pending_triggers:
        # Holding priority: Earthcraft tap-creature costs + mana abilities.
        steps.extend(
            _activation_steps(executor, state, tap_creature_cost_only=True)
        )
        bf_ids = [
            p.object_id
            for p in state.permanents.values()
            if p.zone == Zone.BATTLEFIELD and p.controller == "you"
        ]
        tapped_first = sorted(
            bf_ids,
            key=lambda oid: (not state.permanents[oid].tapped, oid),
        )
        seen: set[tuple] = set()
        for trig in state.pending_triggers:
            base = ActionStep(
                op="resolve_trigger",
                actor=trig["source_id"],
                ability_id=trig["ability_id"],
            )
            ab = executor.find_ability(
                state.permanents[trig["source_id"]].oracle_id,
                trig["ability_id"],
            )
            needs_target = False
            exclude_source = False
            exclude_subject = False
            require_creature = False
            require_nonland = False
            require_gw = False
            require_share_type = False
            if ab is not None:
                for effect in getattr(ab, "effects", []):
                    tgt = getattr(effect, "target", None)
                    if tgt in {
                        "target_permanent",
                        "target_basic_land",
                        "target_other_creature",
                        "enchanted_creature",
                        "controlled_creature",
                        "controlled_creature_green_or_white",
                        "controlled_permanent",
                        "controlled_nonland",
                        "other_controlled_creature",
                        "other_controlled_sharing_type",
                        "target_nonland",
                    }:
                        needs_target = True
                    if tgt in {
                        "target_other_creature",
                        "enchanted_creature",
                        "other_controlled_creature",
                    }:
                        exclude_source = True
                        require_creature = True
                    if tgt in {
                        "controlled_creature",
                        "controlled_creature_green_or_white",
                    }:
                        require_creature = True
                    if tgt == "other_controlled_sharing_type":
                        exclude_subject = True
                        require_share_type = True
                    if tgt == "target_nonland" or tgt == "controlled_nonland":
                        require_nonland = True
                    require_gw = tgt == "controlled_creature_green_or_white"
            if needs_target:
                exclude = set()
                if exclude_source:
                    exclude.add(trig["source_id"])
                if exclude_subject and trig.get("subject_id"):
                    exclude.add(trig["subject_id"])
                candidates = [
                    oid for oid in tapped_first if oid not in exclude
                ]
                if require_creature:
                    candidates = [
                        oid
                        for oid in candidates
                        if state.permanents[oid].is_creature
                    ]
                if require_nonland:
                    filtered: list[str] = []
                    for oid in candidates:
                        sem = executor.semantics.get(state.permanents[oid].oracle_id)
                        types = [t.casefold() for t in (sem.types if sem else [])]
                        if "land" not in types:
                            filtered.append(oid)
                    candidates = filtered
                if require_gw:
                    gw: list[str] = []
                    for oid in candidates:
                        p = state.permanents[oid]
                        colors = {c.upper() for c in p.colors}
                        if not colors:
                            sem = executor.semantics.get(p.oracle_id)
                            colors = {c.upper() for c in (sem.colors if sem else [])}
                        if colors & {"G", "W"}:
                            gw.append(oid)
                    candidates = gw
                if require_share_type:
                    subject_id = trig.get("subject_id")
                    subject = (
                        state.permanents.get(subject_id) if subject_id else None
                    )
                    if subject is None:
                        candidates = []
                    else:
                        subj_types = executor._permanent_type_set(subject)
                        candidates = [
                            oid
                            for oid in candidates
                            if executor._permanent_type_set(state.permanents[oid])
                            & subj_types
                        ]
            else:
                candidates = [None]
            for target in candidates:
                step = base.model_copy(update={"target": target})
                key = (step.actor, step.ability_id, step.target)
                if key in seen:
                    continue
                if _try_apply(executor, state, step) is not None:
                    seen.add(key)
                    steps.append(step)
        return steps

    steps.extend(_activation_steps(executor, state, tap_creature_cost_only=False))

    # Cast creatures/artifacts from hand (Aluren free cast or paid mana_cost).
    for perm in sorted(state.permanents.values(), key=lambda p: p.object_id):
        if perm.zone != Zone.HAND or perm.controller != "you":
            continue
        if not (perm.is_creature or perm.is_artifact):
            continue
        step = ActionStep(op="cast_from_hand", actor=perm.object_id)
        if _try_apply(executor, state, step) is not None:
            steps.append(step)

    # Knack/Helix granted {T}: bounce nonland.
    for perm in sorted(state.permanents.values(), key=lambda p: p.object_id):
        if (
            perm.zone != Zone.BATTLEFIELD
            or perm.controller != "you"
            or not perm.tap_bounce_nonland
            or perm.tapped
            or perm.summoning_sick
        ):
            continue
        for target in sorted(state.permanents.values(), key=lambda p: p.object_id):
            if target.zone != Zone.BATTLEFIELD:
                continue
            sem = executor.semantics.get(target.oracle_id)
            types = [t.casefold() for t in (sem.types if sem else [])]
            if "land" in types:
                continue
            step = ActionStep(
                op="activate_granted_tap_bounce",
                actor=perm.object_id,
                target=target.object_id,
            )
            if _try_apply(executor, state, step) is not None:
                steps.append(step)
    return steps


def _activation_steps(
    executor: Executor,
    state: GameState,
    *,
    tap_creature_cost_only: bool,
) -> list[ActionStep]:
    steps: list[ActionStep] = []
    for perm in sorted(state.permanents.values(), key=lambda p: p.object_id):
        card = executor.semantics.get(perm.oracle_id)
        if not card:
            continue
        activated: list = [
            ab
            for ab in card.abilities
            if isinstance(ab, ActivatedAbility) and ab.supported
        ]
        activated.extend(executor.iter_granted_activated(state, perm))
        for ab in activated:
            if tap_creature_cost_only and not (
                _has_tap_creature_cost(ab) or ab.is_mana_ability
            ):
                continue
            selector = _sac_selector(ab)
            bounce_sel = _bounce_cost_selector(ab)
            remove_cost = _remove_counter_cost(ab)
            need_effect_target = _effect_needs_permanent_target(ab)
            need_tap_host = _tap_cost_needs_host(ab)
            need_untap_host = _untap_symbol_cost_needs_host(ab)
            any_target_dmg = _any_target_damage(ab)
            require_basic_land = any(
                getattr(e, "target", None) == "target_basic_land" for e in ab.effects
            )
            tap_creature = _has_tap_creature_cost(ab)
            # Earthcraft: enumerate (creature fodder, basic land) so Signaler vs token
            # choices are searchable (TapCreatureCost uses cost_target; land uses target).
            if tap_creature and require_basic_land:
                creatures = [
                    p.object_id
                    for p in state.permanents.values()
                    if p.zone == Zone.BATTLEFIELD
                    and p.controller == "you"
                    and p.is_creature
                    and not p.tapped
                    and p.object_id != perm.object_id
                ]
                lands = [
                    p.object_id
                    for p in state.permanents.values()
                    if p.zone == Zone.BATTLEFIELD
                    and p.controller == "you"
                    and executor._is_basic_land(p)
                ]
                for cost_target in creatures:
                    for land in lands:
                        step = ActionStep(
                            op="activate",
                            actor=perm.object_id,
                            ability_id=ab.ability_id,
                            target=land,
                            cost_target=cost_target,
                        )
                        if _try_apply(executor, state, step) is not None:
                            steps.append(step)
                continue
            # Quirion / Wirewood: bounce Forest/Elf cost × untap target creature.
            if bounce_sel and need_effect_target:
                fodder = _bounce_fodder_ids(executor, state, bounce_sel)
                effect_targets = [
                    p.object_id
                    for p in state.permanents.values()
                    if p.zone == Zone.BATTLEFIELD
                    and p.controller == "you"
                    and p.is_creature
                ]
                for cost_target in fodder:
                    for target in effect_targets:
                        if target == cost_target:
                            continue
                        step = ActionStep(
                            op="activate",
                            actor=perm.object_id,
                            ability_id=ab.ability_id,
                            target=target,
                            cost_target=cost_target,
                        )
                        if _try_apply(executor, state, step) is not None:
                            steps.append(step)
                continue
            if bounce_sel and not need_effect_target:
                for cost_target in _bounce_fodder_ids(executor, state, bounce_sel):
                    step = ActionStep(
                        op="activate",
                        actor=perm.object_id,
                        ability_id=ab.ability_id,
                        cost_target=cost_target,
                    )
                    if _try_apply(executor, state, step) is not None:
                        steps.append(step)
                continue
            if selector:
                targets = _fodder_ids(state, selector)
            elif remove_cost is not None:
                targets = []
                for p in state.permanents.values():
                    if p.zone != Zone.BATTLEFIELD or p.controller != "you":
                        continue
                    if remove_cost.selector == "creature_controlled" and not p.is_creature:
                        continue
                    if p.counters.get(remove_cost.counter_type, 0) < remove_cost.quantity:
                        continue
                    targets.append(p.object_id)
            elif need_tap_host:
                host_kind = _tap_cost_host_kind(ab)
                targets = []
                for p in state.permanents.values():
                    if p.zone != Zone.BATTLEFIELD or p.controller != "you":
                        continue
                    if p.tapped or p.object_id == perm.object_id:
                        continue
                    if host_kind == "land":
                        if not executor._is_land_permanent(p):
                            continue
                    elif not p.is_creature:
                        continue
                    targets.append(p.object_id)
            elif need_untap_host:
                targets = [
                    p.object_id
                    for p in state.permanents.values()
                    if p.zone == Zone.BATTLEFIELD
                    and p.controller == "you"
                    and p.is_creature
                    and p.tapped
                    and p.object_id != perm.object_id
                ]
            elif any_target_dmg:
                targets = ["opponent", perm.object_id]
            elif need_effect_target:
                exclude_source = any(
                    getattr(e, "target", None)
                    in {
                        "target_other_creature",
                        "other_controlled_creature",
                    }
                    for e in ab.effects
                )
                require_creature = any(
                    getattr(e, "target", None)
                    in {
                        "target_other_creature",
                        "other_controlled_creature",
                        "controlled_creature",
                        "controlled_creature_green_or_white",
                    }
                    for e in ab.effects
                )
                targets = []
                for p in state.permanents.values():
                    if p.zone != Zone.BATTLEFIELD or p.controller != "you":
                        continue
                    if exclude_source and p.object_id == perm.object_id:
                        continue
                    if require_creature and not p.is_creature:
                        continue
                    if require_basic_land and not executor._is_basic_land(p):
                        continue
                    targets.append(p.object_id)
            else:
                targets = [None]
            for target in targets:
                step = ActionStep(
                    op="activate",
                    actor=perm.object_id,
                    ability_id=ab.ability_id,
                    target=target,
                )
                if _try_apply(executor, state, step) is not None:
                    steps.append(step)
    return steps


def derive_relevant_state(
    spec: InitialStateSpec,
    before: GameState,
    *,
    loop_actions: list[ActionStep] | None = None,
    cards: list[CardSemantics] | None = None,
) -> LoopRelevantState:
    dims: list[StateDimension] = []
    for perm in spec.permanents:
        if perm.is_token:
            continue
        live = before.permanents.get(perm.object_id)
        if live is None:
            continue
        dims.append(
            StateDimension(
                path=f"permanents.{perm.object_id}.zone",
                op=ComparisonOp.EXACT,
                value=live.zone.value,
            )
        )
        dims.append(
            StateDimension(
                path=f"permanents.{perm.object_id}.tapped",
                op=ComparisonOp.EXACT,
                value=live.tapped,
            )
        )
        for ctype, qty in live.counters.items():
            # Accumulating +1/+1 loops (Rosie/Scurry) need MINIMUM; reload loops
            # that return to the same count still satisfy MINIMUM.
            op = (
                ComparisonOp.MINIMUM
                if ctype in {"p1p1", "+1/+1"}
                else ComparisonOp.EXACT
            )
            dims.append(
                StateDimension(
                    path=f"permanents.{perm.object_id}.counters.{ctype}",
                    op=op,
                    value=qty,
                )
            )
    # Once-per-turn + pending-trigger + m1m1-pay dims: shared with verifier (ADR 0008).
    from mtg_loop_engine.verify.mandatory_recurrence import (
        m1m1_pay_dimensions,
        once_per_turn_dimensions,
        pending_trigger_dimensions,
    )

    if loop_actions and cards:
        dims.extend(
            once_per_turn_dimensions(
                loop_actions=loop_actions, cards=cards, before=before
            )
        )
    if cards:
        dims.extend(m1m1_pay_dimensions(cards=cards, before=before))
    dims.extend(pending_trigger_dimensions(before))
    if any(p.is_token for p in spec.permanents):
        dims.append(
            StateDimension(
                path="count.battlefield.creature_tokens",
                op=ComparisonOp.MINIMUM,
                value=before.get_path("count.battlefield.creature_tokens"),
            )
        )
    for color in (
        "white",
        "blue",
        "black",
        "red",
        "green",
        "colorless",
        "any_color",
    ):
        start = getattr(before.mana, color)
        dims.append(
            StateDimension(
                path=f"mana.{color}",
                op=ComparisonOp.MINIMUM,
                value=start,
            )
        )
    return LoopRelevantState(dimensions=dims)


def derive_outputs(before: GameState, after: GameState) -> list[OutputDelta]:
    outs: list[OutputDelta] = []
    for key, typ in OUTPUT_EVENT_KEYS.items():
        delta = after.event_counters.get(key, 0) - before.event_counters.get(key, 0)
        if delta > 0:
            outs.append(OutputDelta(type=typ, delta_per_iteration=delta))
    return outs


def _needs_life_gain_seed(card: CardSemantics) -> bool:
    """Path-b life-drain seed (Bond/Blood), not Heliod counter-on-gain."""
    from mtg_loop_engine.semantics.ir import LoseLifeEffect

    return any(
        isinstance(ab, TriggeredAbility)
        and ab.event == TriggerEvent.GAIN_LIFE
        and any(isinstance(e, LoseLifeEffect) for e in ab.effects)
        for ab in card.abilities
    )


def _is_gain_life_put_counter(card: CardSemantics) -> bool:
    """Heliod / Archangel: GAIN_LIFE → +1/+1 puts."""
    return any(
        isinstance(ab, TriggeredAbility)
        and ab.event == TriggerEvent.GAIN_LIFE
        and any(isinstance(e, AddCounterEffect) for e in ab.effects)
        for ab in card.abilities
    )


def _is_counter_added_damage(card: CardSemantics) -> bool:
    """Shalai-class: COUNTER_ADDED → damage (needs life-gain bootstrap + lifelink)."""
    return any(
        isinstance(ab, TriggeredAbility)
        and ab.event == TriggerEvent.COUNTER_ADDED
        and any(isinstance(e, DealDamageEffect) for e in ab.effects)
        for ab in card.abilities
    )


def _lifelink_grant_ping_target(card: CardSemantics, perm_is_creature: bool) -> bool:
    """Ballista remove-counter OR Shalai counter→damage can close with lifelink."""
    if not perm_is_creature:
        return False
    caps = extract_capabilities(card)
    return caps.removes_p1p1() or _is_counter_added_damage(card)


def _needs_opponent_lose_life_seed(card: CardSemantics) -> bool:
    """Path-b mill feedback seed (Mindcrank / Bloodchief class)."""
    from mtg_loop_engine.semantics.ir import MillEffect

    return any(
        isinstance(ab, TriggeredAbility)
        and ab.event == TriggerEvent.OPPONENT_LOSE_LIFE
        and any(isinstance(e, MillEffect) for e in ab.effects)
        for ab in card.abilities
    )


def _needs_token_create_seed(card: CardSemantics) -> bool:
    return any(
        isinstance(ab, TriggeredAbility) and ab.event == TriggerEvent.CREATE_TOKEN
        for ab in card.abilities
    )


def _needs_mana_create_token_sac_bootstrap(cards: list[CardSemantics]) -> bool:
    """Sliver Queen + Altar: seed a token so sac→mana can pay the first create."""
    has_mana_create = False
    has_sac_mana = False
    for card in cards:
        for ab in card.abilities:
            if not isinstance(ab, ActivatedAbility) or not ab.supported:
                continue
            costs = ab.costs
            effects = ab.effects
            if any(isinstance(c, ManaCost) for c in costs) and any(
                isinstance(e, CreateTokenEffect) for e in effects
            ):
                has_mana_create = True
            if any(isinstance(c, SacrificeCost) for c in costs) and any(
                isinstance(e, AddManaEffect) for e in effects
            ):
                has_sac_mana = True
    return has_mana_create and has_sac_mana


def _needs_mana_create_echoes_bootstrap(cards: list[CardSemantics]) -> bool:
    """Sliver Queen + Mana Echoes: seed {2} so the first create ETB can float repay mana."""
    from mtg_loop_engine.semantics.enums import ManaScaleKind

    has_mana_create = False
    has_echoes = False
    for card in cards:
        for ab in card.abilities:
            if (
                isinstance(ab, ActivatedAbility)
                and ab.supported
                and any(isinstance(c, ManaCost) for c in ab.costs)
                and any(isinstance(e, CreateTokenEffect) for e in ab.effects)
            ):
                has_mana_create = True
            if isinstance(ab, TriggeredAbility) and ab.event == TriggerEvent.ENTER_BATTLEFIELD:
                for e in ab.effects:
                    if (
                        isinstance(e, AddManaEffect)
                        and e.mana_scale
                        is ManaScaleKind.CONTROLLED_SHARING_CREATURE_TYPE
                    ):
                        has_echoes = True
    return has_mana_create and has_echoes


def _needs_lifelink_grant_seed(card: CardSemantics) -> bool:
    """Heliod-class: GAIN_LIFE → counter; partner pings or deals counter-put damage."""
    return _is_gain_life_put_counter(card)


def build_witness(
    a: CardSemantics,
    b: CardSemantics,
    spec: InitialStateSpec,
    loop_actions: list[ActionStep],
    before: GameState,
    after: GameState,
    *,
    setup_actions: list[ActionStep] | None = None,
) -> LoopWitness:
    generic: list[Prerequisite] = []
    if any(p.is_token for p in spec.permanents):
        generic.append(
            Prerequisite(
                kind="board",
                description="creature token fodder (identity irrelevant)",
            )
        )
    if any(p.object_id == AURA_HOST_OBJECT_ID for p in spec.permanents):
        generic.append(
            Prerequisite(
                kind="board",
                description="generic creature host for aura tap cost (identity irrelevant)",
            )
        )
    scaled_seed_ids = {
        CREATURE_MANA_SEED_ORACLE_ID,
        ELF_MANA_SEED_ORACLE_ID,
        DEFENDER_MANA_SEED_ORACLE_ID,
    }
    if any(p.oracle_id in scaled_seed_ids for p in spec.permanents):
        generic.append(
            Prerequisite(
                kind="board",
                description=(
                    "generic board-scaled mana fodder "
                    "(creature / elf / defender identity irrelevant)"
                ),
            )
        )
    if any(p.oracle_id == HAND_ARTIFACT_SEED_ORACLE_ID for p in spec.permanents):
        generic.append(
            Prerequisite(
                kind="board",
                description="hand artifact cards for Metalworker scale (identity irrelevant)",
            )
        )
    if any(
        p.oracle_id == METALCRAFT_ARTIFACT_SEED_ORACLE_ID for p in spec.permanents
    ):
        generic.append(
            Prerequisite(
                kind="board",
                description="generic artifacts for metalcraft (identity irrelevant)",
            )
        )
    if any(p.oracle_id == FEROCIOUS_CREATURE_SEED_ORACLE_ID for p in spec.permanents):
        generic.append(
            Prerequisite(
                kind="board",
                description="generic power-4+ creature for ferocious (identity irrelevant)",
            )
        )
    if any(p.oracle_id == TAP_PAIR_CREATURE_SEED_ORACLE_ID for p in spec.permanents):
        generic.append(
            Prerequisite(
                kind="board",
                description="generic creature to tap with Supportive Parents (identity irrelevant)",
            )
        )
    setup = setup_actions or []
    if any(s.op == "seed_gain_life" for s in setup):
        generic.append(
            Prerequisite(
                kind="board",
                description=(
                    "generic life-gain seed to start GAIN_LIFE triggers "
                    "(identity irrelevant)"
                ),
            )
        )
    if any(s.op == "seed_lose_life" for s in setup):
        generic.append(
            Prerequisite(
                kind="board",
                description=(
                    "generic opponent life-loss seed to start OPPONENT_LOSE_LIFE "
                    "triggers (identity irrelevant)"
                ),
            )
        )
    if any(s.op == "seed_create_token" for s in setup):
        generic.append(
            Prerequisite(
                kind="board",
                description=(
                    "generic token-create seed to start CREATE_TOKEN triggers "
                    "(Food identity irrelevant)"
                ),
            )
        )
    if any(s.op == "seed_grant_lifelink" for s in setup):
        generic.append(
            Prerequisite(
                kind="board",
                description=(
                    "physics lifelink grant seed (not product-legal for ORACLE_EXACT; "
                    "identity of grant source irrelevant once lifelink is on the pinger)"
                ),
            )
        )
    if any(s.op == "seed_grant_tap_bounce" for s in setup):
        generic.append(
            Prerequisite(
                kind="board",
                description=(
                    "Instant tap-bounce grant seed (Banishing Knack / Retraction Helix "
                    "class; grant persists for the witness)"
                ),
            )
        )
    if any(p.oracle_id == MANA_DORK_SEED_ORACLE_ID for p in spec.permanents):
        generic.append(
            Prerequisite(
                kind="board",
                description=(
                    "generic tap-mana dork fodder for cast-from-hand loops "
                    "(identity irrelevant)"
                ),
            )
        )
    if any(p.oracle_id == BOUNCE_CREATURE_SEED_ORACLE_ID for p in spec.permanents):
        generic.append(
            Prerequisite(
                kind="board",
                description=(
                    "generic creature in hand to cast/bounce under grant+Alarm "
                    "(identity irrelevant)"
                ),
            )
        )
    if any(p.oracle_id == BASIC_ISLAND_SEED_ORACLE_ID for p in spec.permanents):
        generic.append(
            Prerequisite(
                kind="board",
                description=(
                    "generic basic Island for enchanted-land tap hosts / "
                    "Earthcraft untap (identity irrelevant)"
                ),
            )
        )
    if any(p.oracle_id == BASIC_PLAINS_SEED_ORACLE_ID for p in spec.permanents):
        generic.append(
            Prerequisite(
                kind="board",
                description=(
                    "generic basic Plains for paid {Q} create / Earthcraft untap "
                    "(identity irrelevant; double-tap pays {1}{W})"
                ),
            )
        )
    grant_ability_ids = {
        ab.ability_id
        for card in (a, b)
        if (ab := _grant_lifelink_ability(card)) is not None
    }
    if any(
        s.op == "activate" and s.ability_id in grant_ability_ids for s in setup
    ):
        generic.append(
            Prerequisite(
                kind="board",
                description=(
                    "generic mana for one paid grant-lifelink activation "
                    "(Path b; identity of mana source irrelevant)"
                ),
            )
        )
    refs = [
        EssentialCardRef(oracle_id=a.oracle_id, name=a.name),
        EssentialCardRef(oracle_id=b.oracle_id, name=b.name),
    ]
    semantics_for_witness: dict[str, CardSemantics] = {
        a.oracle_id: a,
        b.oracle_id: b,
    }
    _inject_seed_semantics(spec, semantics_for_witness)
    pair_id = "__".join(sorted([a.oracle_id, b.oracle_id]))
    witness = LoopWitness(
        id=f"discover_{pair_id}",
        classification=two_card(essential=refs, generic=generic),
        essential_cards=refs,
        card_semantics=list(semantics_for_witness.values()),
        initial_state=spec,
        setup_actions=setup,
        loop_actions=loop_actions,
        relevant_state=derive_relevant_state(
            spec, before, loop_actions=loop_actions, cards=[a, b]
        ),
        expected_outputs=derive_outputs(before, after),
        assumptions=["discovered_without_pair_labels"],
        prerequisites=generic,
    )
    analysis = analyze_prerequisites(witness)
    functional = [
        Prerequisite(kind="functional", description=item)
        for item in analysis.functional_external_requirements
    ]
    # Prefer classify disclosure; keep explorer-only board labels if classify is empty.
    analysis_generics = [
        Prerequisite(kind="board", description=item)
        for item in analysis.generic_prerequisites
    ]
    if analysis_generics:
        # Union with explorer labels so Path-b / setup seeds never drop when
        # classify also reports tokens or scaled fodder.
        seen = {p.description for p in analysis_generics}
        merged = list(analysis_generics)
        for p in generic:
            if p.description not in seen:
                seen.add(p.description)
                merged.append(p)
        generic_prereqs = merged
    else:
        generic_prereqs = generic
    witness.classification = Classification(
        essential_card_count=max(analysis.essential_functional_count, 1),
        strict_two_card=analysis.strict_two_card,
        generic_prerequisites=generic_prereqs,
        functional_external_requirements=functional,
    )
    witness.prerequisites = generic_prereqs + functional
    witness.assumptions = ["discovered_without_pair_labels"] + [
        f"{item.kind.value}: {item.description}" for item in analysis.assumptions
    ]
    return witness


def explore_pair(
    a: CardSemantics,
    b: CardSemantics,
    *,
    max_depth: int = 6,
    max_states: int = 4000,
    verifier: Verifier | None = None,
    expected_net_state: NetStateDelta | None = None,
    expected_claim_consequence: Consequence | None = None,
) -> ExploredWitness | None:
    """Search one unordered pair.

    Returns the first verifier-accepted loop where both searched essentials
    participate (`strict_two_card`). Bystander-verified sequences are skipped
    silently so BFS can continue; if none qualify, returns ``None``.

    When ``expected_net_state`` / ``expected_claim_consequence`` are set, stamp
    them on candidate witnesses before verify so shallow gross-only loops can
    be skipped in favor of the claimed net benefit (gold promotion).
    """
    check = verifier or Verifier()
    spec = default_initial_state(a, b)
    semantics = {a.oracle_id: a, b.oracle_id: b}
    _inject_seed_semantics(spec, semantics)
    executor = Executor(semantics)
    start = GameState.from_spec(spec)
    setup_actions: list[ActionStep] = []
    if _needs_life_gain_seed(a) or _needs_life_gain_seed(b):
        seed_actor = None
        for perm in sorted(start.permanents.values(), key=lambda p: p.object_id):
            card = semantics.get(perm.oracle_id)
            if card is not None and _needs_life_gain_seed(card):
                seed_actor = perm.object_id
                break
        if seed_actor is not None:
            seed = ActionStep(
                op="seed_gain_life",
                actor=seed_actor,
                note="generic life-gain seed (Path b)",
            )
            err = executor.run_step(start, seed)
            if err is None:
                setup_actions = [seed]
    # Heliod/Archangel + Shalai: no remove-counter ping to bootstrap — seed life gain.
    if (
        (_is_gain_life_put_counter(a) and _is_counter_added_damage(b))
        or (_is_gain_life_put_counter(b) and _is_counter_added_damage(a))
    ) and not any(s.op == "seed_gain_life" for s in setup_actions):
        seed_actor = None
        for perm in sorted(start.permanents.values(), key=lambda p: p.object_id):
            card = semantics.get(perm.oracle_id)
            if card is not None and _is_gain_life_put_counter(card):
                seed_actor = perm.object_id
                break
        if seed_actor is not None:
            seed = ActionStep(
                op="seed_gain_life",
                actor=seed_actor,
                note="generic life-gain seed (Heliod/Shalai counter→damage bootstrap)",
            )
            err = executor.run_step(start, seed)
            if err is None:
                setup_actions = [*setup_actions, seed]
    if _needs_opponent_lose_life_seed(a) or _needs_opponent_lose_life_seed(b):
        seed_actor = None
        for perm in sorted(start.permanents.values(), key=lambda p: p.object_id):
            card = semantics.get(perm.oracle_id)
            if card is not None and _needs_opponent_lose_life_seed(card):
                seed_actor = perm.object_id
                break
        if seed_actor is not None:
            seed = ActionStep(
                op="seed_lose_life",
                actor=seed_actor,
                note="generic opponent life-loss seed (Path b)",
            )
            err = executor.run_step(start, seed)
            if err is None:
                setup_actions = [*setup_actions, seed]
    if _needs_token_create_seed(a) or _needs_token_create_seed(b):
        seed_actor = None
        for perm in sorted(start.permanents.values(), key=lambda p: p.object_id):
            card = semantics.get(perm.oracle_id)
            if card is not None and _needs_token_create_seed(card):
                seed_actor = perm.object_id
                break
        if seed_actor is not None:
            seed = ActionStep(
                op="seed_create_token",
                actor=seed_actor,
                note="generic token-create seed (Rosie class)",
            )
            err = executor.run_step(start, seed)
            if err is None:
                setup_actions = [*setup_actions, seed]
    # seed_grant_lifelink is a physics stand-in only. Never emit on ORACLE_EXACT
    # product pairs (Heliod requires a paid {1}{W} activation for product VERIFIED).
    both_oracle_exact = (
        provenance_of(a.oracle_id) is Provenance.ORACLE_EXACT
        and provenance_of(b.oracle_id) is Provenance.ORACLE_EXACT
    )
    if (
        not both_oracle_exact
        and (_needs_lifelink_grant_seed(a) or _needs_lifelink_grant_seed(b))
        and _grant_lifelink_ability(a) is None
        and _grant_lifelink_ability(b) is None
    ):
        # Grant lifelink to a partner that can remove counters for damage.
        grantor = None
        pinger = None
        for perm in sorted(start.permanents.values(), key=lambda p: p.object_id):
            card = semantics.get(perm.oracle_id)
            if card is None:
                continue
            if _needs_lifelink_grant_seed(card):
                grantor = perm.object_id
            if _lifelink_grant_ping_target(card, perm.is_creature):
                pinger = perm.object_id
        if grantor is not None and pinger is not None and grantor != pinger:
            seed = ActionStep(
                op="seed_grant_lifelink",
                actor=grantor,
                target=pinger,
                note="physics lifelink grant seed (non-product path)",
            )
            err = executor.run_step(start, seed)
            if err is None:
                setup_actions = [*setup_actions, seed]
    # Paid Heliod-class grant: activate once in setup targeting the counter-pinger.
    grant_card = a if _grant_lifelink_ability(a) is not None else (
        b if _grant_lifelink_ability(b) is not None else None
    )
    if grant_card is not None:
        grant_ab = _grant_lifelink_ability(grant_card)
        grantor = None
        pinger = None
        for perm in sorted(start.permanents.values(), key=lambda p: p.object_id):
            card = semantics.get(perm.oracle_id)
            if card is None:
                continue
            if card.oracle_id == grant_card.oracle_id:
                grantor = perm.object_id
            if _lifelink_grant_ping_target(card, perm.is_creature):
                pinger = perm.object_id
        if (
            grant_ab is not None
            and grantor is not None
            and pinger is not None
            and grantor != pinger
        ):
            step = ActionStep(
                op="activate",
                actor=grantor,
                ability_id=grant_ab.ability_id,
                target=pinger,
                note="paid lifelink grant setup (Path b mana prerequisite)",
            )
            err = executor.run_step(start, step)
            if err is None:
                setup_actions = [*setup_actions, step]
    # Banishing Knack / Retraction Helix: Instant grant via setup onto grant host.
    if _has_instant_grant_tap_bounce(a) or _has_instant_grant_tap_bounce(b):
        host = start.permanents.get(GRANT_HOST_OBJECT_ID)
        if host is not None and host.is_creature:
            seed = ActionStep(
                op="seed_grant_tap_bounce",
                target=GRANT_HOST_OBJECT_ID,
                note="Instant grant {T}: bounce nonland (witness-persistent)",
            )
            err = executor.run_step(start, seed)
            if err is None:
                setup_actions = [*setup_actions, seed]
    queue: deque[tuple[GameState, list[ActionStep]]] = deque([(start, [])])
    expanded: set[tuple] = set()
    visited = 0

    while queue:
        state, actions = queue.popleft()
        visited += 1
        if visited > max_states:
            break
        # Check arrival before expansion pruning so returning to the start
        # fingerprint can still be recognized as a loop.
        # Empty pending: classic closed loop. Same trigger ability/source/amount
        # as post-seed start: Path-b life-drain feedback (subject_id may change).
        if 1 <= len(actions) <= max_depth:
            def _trigger_close_key(st: GameState) -> tuple:
                return tuple(
                    (
                        t.get("ability_id"),
                        t.get("source_id"),
                        t.get("amount"),
                    )
                    for t in st.pending_triggers
                )

            can_close = (not state.pending_triggers) or (
                bool(start.pending_triggers)
                and _trigger_close_key(state) == _trigger_close_key(start)
            )
            if can_close:
                outputs = derive_outputs(start, state)
                if outputs:
                    witness = build_witness(
                        a,
                        b,
                        spec,
                        actions,
                        start,
                        state,
                        setup_actions=setup_actions,
                    )
                    if (
                        expected_net_state is not None
                        or expected_claim_consequence is not None
                    ):
                        witness = witness.model_copy(
                            update={
                                k: v
                                for k, v in {
                                    "expected_net_state": expected_net_state,
                                    "expected_claim_consequence": (
                                        expected_claim_consequence
                                    ),
                                }.items()
                                if v is not None
                            }
                        )
                    proof = check.verify(witness)
                    # Participant gate (search-only): physics may verify a one-card
                    # self-loop while the other searched card never acts. Detection
                    # already stamps strict_two_card; enforce it before acceptance.
                    if (
                        proof.status == VerificationStatus.VERIFIED
                        and witness.classification.strict_two_card
                    ):
                        return ExploredWitness(witness=witness, proof=proof)
        if len(actions) >= max_depth:
            continue
        fp = reusable_fingerprint(state)
        if fp in expanded:
            continue
        expanded.add(fp)
        for step in legal_steps(executor, state):
            nxt = _try_apply(executor, state, step)
            if nxt is None:
                continue
            queue.append((nxt, [*actions, step]))
    return None
