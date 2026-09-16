"""Rules-aware action executor for witness replay."""

from __future__ import annotations

from dataclasses import dataclass

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.semantics.enums import ManaScaleKind, TriggerEvent, VerificationStatus, Zone
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    AddCounterCost,
    UntapSymbolCost,
    AddCounterEffect,
    AddManaEffect,
    CardSemantics,
    ContinuousCostReduction,
    CreateTokenEffect,
    DealDamageEffect,
    DrawEffect,
    FreeCastCreaturesByManaValue,
    GainLifeEffect,
    GrantLifelinkEffect,
    GrantTapBounceNonlandEffect,
    HybridManaCost,
    LoseLifeEffect,
    ManaAmount,
    ManaCost,
    MillEffect,
    MoveToZoneEffect,
    ProofIrrelevantStatic,
    RemoveCounterCost,
    RemoveCounterEffect,
    ReplacementAmplifyP1P1Counters,
    ReplacementExileInsteadOfGraveyard,
    ReplacementMultiplyTapMana,
    ReplacementDoubleTokens,
    ReplacementReduceM1M1Counters,
    ReturnToBattlefieldEffect,
    SacrificeCost,
    TapCost,
    TapCreatureCost,
    TapEffect,
    TriggeredAbility,
    UntapEffect,
)
from mtg_loop_engine.state.game import GameState, Permanent


def _semantics_for(
    semantics: dict[str, CardSemantics], perm: Permanent
) -> CardSemantics | None:
    return semantics.get(perm.oracle_id)


def _is_elf(sem: CardSemantics) -> bool:
    return any("elf" in t.casefold() for t in sem.types)


def _has_defender(sem: CardSemantics) -> bool:
    for ab in sem.abilities:
        if isinstance(ab, ProofIrrelevantStatic) and ab.clause.casefold().strip() == "defender":
            return True
    return False


# CR 205.2a card types + 205.4a supertypes — not creature subtypes.
_NON_CREATURE_TYPE_WORDS = frozenset(
    {
        "artifact",
        "battle",
        "conspiracy",
        "creature",
        "dungeon",
        "enchantment",
        "instant",
        "land",
        "phenomenon",
        "plane",
        "planeswalker",
        "scheme",
        "sorcery",
        "tribal",
        "kindred",
        "vanguard",
        "basic",
        "legendary",
        "ongoing",
        "snow",
        "world",
        "token",
        "colorless",
        "white",
        "blue",
        "black",
        "red",
        "green",
    }
)


def _controlled_permanents(state: GameState, controller: str = "you") -> list[Permanent]:
    return [
        p
        for p in state.permanents.values()
        if p.zone == Zone.BATTLEFIELD and p.controller == controller
    ]


def _colors_among_controlled(
    state: GameState,
    semantics: dict[str, CardSemantics],
    controller: str = "you",
) -> set[str]:
    colors: set[str] = set()
    for perm in _controlled_permanents(state, controller):
        sem = _semantics_for(semantics, perm)
        if sem is None:
            continue
        for ab in sem.abilities:
            if not isinstance(ab, ActivatedAbility):
                continue
            for cost in ab.costs:
                if not isinstance(cost, ManaCost):
                    continue
                for color in ("white", "blue", "black", "red", "green"):
                    if getattr(cost.amount, color) > 0:
                        colors.add(color)
    return colors


def _devotion_green(
    state: GameState,
    semantics: dict[str, CardSemantics],
    controller: str = "you",
) -> int:
    total = 0
    for perm in _controlled_permanents(state, controller):
        sem = _semantics_for(semantics, perm)
        if sem is None:
            continue
        for ab in sem.abilities:
            if not isinstance(ab, ActivatedAbility):
                continue
            for cost in ab.costs:
                if isinstance(cost, ManaCost):
                    total += cost.amount.green
    return total


def _scaled_mana_quantity(
    effect: AddManaEffect,
    state: GameState,
    source: Permanent,
    semantics: dict[str, CardSemantics],
) -> int:
    scale = effect.mana_scale
    if scale is None:
        return 0
    if scale is ManaScaleKind.CONTROLLED_CREATURES:
        return sum(1 for p in _controlled_permanents(state) if p.is_creature)
    if scale is ManaScaleKind.CONTROLLED_ELF:
        return sum(
            1
            for p in _controlled_permanents(state)
            if p.is_creature and (sem := _semantics_for(semantics, p)) and _is_elf(sem)
        )
    if scale is ManaScaleKind.BATTLEFIELD_ELF:
        return sum(
            1
            for p in state.permanents.values()
            if p.zone == Zone.BATTLEFIELD
            and p.is_creature
            and (sem := _semantics_for(semantics, p))
            and _is_elf(sem)
        )
    if scale is ManaScaleKind.CONTROLLED_DEFENDERS:
        return sum(
            1
            for p in _controlled_permanents(state)
            if p.is_creature and (sem := _semantics_for(semantics, p)) and _has_defender(sem)
        )
    if scale is ManaScaleKind.CONTROLLED_ENCHANTMENTS:
        return sum(
            1
            for p in _controlled_permanents(state)
            if (sem := _semantics_for(semantics, p))
            and any(t.casefold() == "enchantment" for t in sem.types)
        )
    if scale is ManaScaleKind.DEVOTION_GREEN:
        return _devotion_green(state, semantics)
    if scale is ManaScaleKind.VIVID_PERMANENT_COLORS:
        return len(_colors_among_controlled(state, semantics))
    if scale is ManaScaleKind.HAND_ARTIFACTS:
        return sum(
            1
            for p in state.permanents.values()
            if p.zone == Zone.HAND and p.controller == "you" and p.is_artifact
        )
    return 0


@dataclass
class ExecError:
    status: VerificationStatus
    message: str


class Executor:
    """Replay setup/loop actions. Combo player chooses favorably; opponents adversarial."""

    def __init__(self, semantics: dict[str, CardSemantics]):
        self.semantics = semantics  # keyed by oracle_id

    def cost_reduction(
        self,
        state: GameState,
        *,
        ability: ActivatedAbility | None = None,
        actor: Permanent | None = None,
    ) -> tuple[int, int]:
        """Return (generic_reduction, min_mana_remaining floor)."""
        reduction = 0
        floor = 0
        for perm in state.permanents.values():
            if perm.zone != Zone.BATTLEFIELD or perm.controller != "you":
                continue
            card = self.semantics.get(perm.oracle_id)
            if not card:
                continue
            for ab in card.abilities:
                if not isinstance(ab, ContinuousCostReduction):
                    continue
                if (
                    ab.exclude_mana_abilities
                    and ability is not None
                    and ability.is_mana_ability
                ):
                    continue
                if ab.applies_to == "enchanted_artifact_activated":
                    # No attachment graph: reduce activations of other artifacts
                    # you control (the enchanted host in two-card witnesses).
                    if (
                        actor is None
                        or not actor.is_artifact
                        or actor.object_id == perm.object_id
                    ):
                        continue
                reduction += ab.reduce_generic
                floor = max(floor, ab.min_mana_remaining)
        return reduction, floor

    def has_exile_on_death(self, state: GameState) -> bool:
        for perm in state.permanents.values():
            if perm.zone != Zone.BATTLEFIELD or perm.controller != "you":
                continue
            card = self.semantics.get(perm.oracle_id)
            if not card:
                continue
            for ab in card.abilities:
                if isinstance(ab, ReplacementExileInsteadOfGraveyard):
                    return True
        return False

    def m1m1_put_quantity(self, state: GameState, quantity: int) -> int:
        """Apply Vizier-style replacement to a would-be -1/-1 put."""
        reduce_by = 0
        for perm in state.permanents.values():
            if perm.zone != Zone.BATTLEFIELD or perm.controller != "you":
                continue
            card = self.semantics.get(perm.oracle_id)
            if not card:
                continue
            for ab in card.abilities:
                if isinstance(ab, ReplacementReduceM1M1Counters):
                    reduce_by = max(reduce_by, ab.reduce_by)
        return max(0, quantity - reduce_by)

    def p1p1_put_quantity(
        self, state: GameState, quantity: int, *, permanent: Permanent
    ) -> int:
        """Apply Kami/Hardened Scales-style amplify to a would-be +1/+1 put."""
        if permanent.controller != "you" or quantity <= 0:
            return quantity
        bonus = 0
        for perm in state.permanents.values():
            if perm.zone != Zone.BATTLEFIELD or perm.controller != "you":
                continue
            card = self.semantics.get(perm.oracle_id)
            if not card:
                continue
            for ab in card.abilities:
                if not isinstance(ab, ReplacementAmplifyP1P1Counters):
                    continue
                if (
                    ab.applies_to == "creatures_you_control"
                    and not permanent.is_creature
                ):
                    continue
                bonus += ab.plus
        return quantity + bonus

    def token_create_multiplier(self, state: GameState) -> int:
        mult = 1
        for perm in state.permanents.values():
            if perm.zone != Zone.BATTLEFIELD or perm.controller != "you":
                continue
            card = self.semantics.get(perm.oracle_id)
            if not card:
                continue
            for ab in card.abilities:
                if isinstance(ab, ReplacementDoubleTokens):
                    mult *= ab.multiplier
        return mult

    def tap_mana_multiplier(self, state: GameState) -> int:
        """Product of active tap-mana multipliers (Mana Reflection / Nyxbloom class)."""
        mult = 1
        for perm in state.permanents.values():
            if perm.zone != Zone.BATTLEFIELD or perm.controller != "you":
                continue
            card = self.semantics.get(perm.oracle_id)
            if not card:
                continue
            for ab in card.abilities:
                if isinstance(ab, ReplacementMultiplyTapMana):
                    mult *= ab.multiplier
        return mult

    def _effective_tap_mana_qty(self, state: GameState, source: Permanent, qty: int) -> int:
        if qty <= 0 or not source.tapped:
            return qty
        return qty * self.tap_mana_multiplier(state)

    def find_ability(
        self, oracle_id: str, ability_id: str
    ) -> ActivatedAbility | TriggeredAbility | None:
        card = self.semantics.get(oracle_id)
        if not card:
            return None
        for ab in card.abilities:
            if getattr(ab, "ability_id", None) == ability_id:
                return ab  # type: ignore[return-value]
        return None

    def pay_mana(
        self,
        state: GameState,
        amount: ManaAmount,
        *,
        allow_activate_only: bool = False,
    ) -> ExecError | None:
        # Colors exact, then any_color may cover remaining colored needs.
        # Generic paid from colorless, then colored, then any_color.
        # Unrestricted pool first; activate-only pool only when allowed.
        pools = [state.mana]
        if allow_activate_only:
            pools.append(state.mana_activate_only)
        need = amount.model_copy(deep=True)

        for color in ("white", "blue", "black", "red", "green", "colorless"):
            n = getattr(need, color)
            if not n:
                continue
            remaining = n
            for pool in pools:
                if remaining <= 0:
                    break
                avail = getattr(pool, color)
                use = min(avail, remaining)
                if use:
                    setattr(pool, color, avail - use)
                    remaining -= use
            if remaining:
                for pool in pools:
                    if remaining <= 0:
                        break
                    if pool.any_color < remaining:
                        use = pool.any_color
                    else:
                        use = remaining
                    if use:
                        pool.any_color -= use
                        remaining -= use
            if remaining:
                return ExecError(
                    VerificationStatus.MANA_RESTRICTION, f"need {color} {n}"
                )
            setattr(need, color, 0)

        generic = need.generic
        for pool in pools:
            while generic > 0 and pool.colorless > 0:
                pool.colorless -= 1
                generic -= 1
            for color in ("white", "blue", "black", "red", "green"):
                while generic > 0 and getattr(pool, color) > 0:
                    setattr(pool, color, getattr(pool, color) - 1)
                    generic -= 1
            while generic > 0 and pool.any_color > 0:
                pool.any_color -= 1
                generic -= 1
        if generic > 0:
            return ExecError(
                VerificationStatus.RESOURCE_DEFICIT, f"cannot pay generic {need.generic}"
            )
        return None

    def _credit_mana(
        self,
        state: GameState,
        effect: AddManaEffect,
        color: str,
        qty: int,
    ) -> None:
        if qty <= 0:
            return
        pool = (
            state.mana_activate_only
            if effect.spend_only == "activate_abilities"
            else state.mana
        )
        setattr(pool, color, getattr(pool, color) + qty)
        state.bump("mana", qty)

    def apply_effects(
        self,
        state: GameState,
        source: Permanent,
        effects: list,
        target_id: str | None,
        *,
        trigger_amount: int | None = None,
        trigger_subject_id: str | None = None,
    ) -> ExecError | None:
        amount = trigger_amount
        for effect in effects:
            # Half-life lose: compute qty before apply so following gains can reuse it.
            if isinstance(effect, LoseLifeEffect) and effect.half_life_rounded_up:
                life = (
                    state.life_opponent if effect.who == "opponent" else state.life_you
                )
                amount = (life + 1) // 2
            err = self._apply_one(
                state,
                source,
                effect,
                target_id,
                trigger_amount=amount,
                trigger_subject_id=trigger_subject_id,
            )
            if err:
                return err
        return None

    def _apply_one(
        self,
        state: GameState,
        source: Permanent,
        effect,
        target_id: str | None,
        *,
        trigger_amount: int | None = None,
        trigger_subject_id: str | None = None,
    ) -> ExecError | None:
        if isinstance(effect, AddManaEffect):
            mult = self.tap_mana_multiplier(state) if source.tapped else 1
            if effect.equal_to_source_power:
                power = source.effective_power()
                qty = self._effective_tap_mana_qty(
                    state, source, max(int(power or 0), 0)
                )
                if qty > 0:
                    self._credit_mana(state, effect, effect.equal_to_source_power, qty)
                return None
            if effect.equal_to_source_p1p1_counters:
                qty = self._effective_tap_mana_qty(
                    state,
                    source,
                    max(int(source.counters.get("p1p1", 0)), 0),
                )
                if qty > 0:
                    self._credit_mana(
                        state, effect, effect.equal_to_source_p1p1_counters, qty
                    )
                return None
            if effect.mana_scale is not None:
                if effect.mana_scale is ManaScaleKind.VIVID_PERMANENT_COLORS:
                    colors = _colors_among_controlled(state, self.semantics)
                    for color in colors:
                        self._credit_mana(state, effect, color, mult)
                    return None
                if (
                    effect.mana_scale
                    is ManaScaleKind.CONTROLLED_SHARING_CREATURE_TYPE
                ):
                    if (
                        not trigger_subject_id
                        or trigger_subject_id not in state.permanents
                    ):
                        return ExecError(
                            VerificationStatus.ILLEGAL_TARGET,
                            "sharing-type mana needs trigger subject",
                        )
                    subject = state.permanents[trigger_subject_id]
                    subtypes = self._creature_subtypes(subject)
                    if not subtypes:
                        return None
                    qty = sum(
                        1
                        for p in _controlled_permanents(state)
                        if p.is_creature
                        and (self._creature_subtypes(p) & subtypes)
                    )
                    if qty > 0:
                        self._credit_mana(state, effect, effect.scale_color, qty)
                    return None
                base = max(
                    _scaled_mana_quantity(effect, state, source, self.semantics),
                    0,
                )
                qty = self._effective_tap_mana_qty(
                    state,
                    source,
                    base * max(int(effect.scale_multiplier or 1), 1),
                )
                if qty > 0:
                    self._credit_mana(state, effect, effect.scale_color, qty)
                return None
            for color in (
                "white",
                "blue",
                "black",
                "red",
                "green",
                "colorless",
                "generic",
                "any_color",
            ):
                delta = getattr(effect.amount, color) * mult
                if delta:
                    self._credit_mana(state, effect, color, delta)
            return None

        if isinstance(effect, UntapEffect):
            if effect.target == "all_creatures":
                n = 0
                for perm in state.permanents.values():
                    if perm.zone == Zone.BATTLEFIELD and perm.is_creature:
                        was_tapped = perm.tapped
                        perm.tapped = False
                        if was_tapped:
                            self._queue_triggers(
                                state, TriggerEvent.UNTAP, perm
                            )
                        n += 1
                if n:
                    state.bump("untap", n)
                return None
            tid = source.object_id if effect.target == "self" else target_id
            if not tid or tid not in state.permanents:
                return ExecError(VerificationStatus.ILLEGAL_TARGET, "untap target missing")
            target_perm = state.permanents[tid]
            if effect.target == "target_basic_land":
                if not self._is_basic_land(target_perm):
                    return ExecError(
                        VerificationStatus.ILLEGAL_TARGET,
                        "untap target must be a basic land",
                    )
            self._untap_permanent(state, target_perm)
            state.bump("untap")
            return None

        if isinstance(effect, TapEffect):
            tid = source.object_id if effect.target == "self" else target_id
            if not tid or tid not in state.permanents:
                return ExecError(VerificationStatus.ILLEGAL_TARGET, "tap target missing")
            state.permanents[tid].tapped = True
            state.bump("tap")
            return None

        if isinstance(effect, CreateTokenEffect):
            qty = effect.quantity
            if effect.quantity_equal_to_controlled_subtype:
                subtype = effect.quantity_equal_to_controlled_subtype.casefold()
                qty = sum(
                    1
                    for p in state.permanents.values()
                    if p.zone == Zone.BATTLEFIELD
                    and p.controller == "you"
                    and p.is_creature
                    and subtype in self._creature_subtypes(p)
                )
            qty *= self.token_create_multiplier(state)
            if qty <= 0:
                return None
            for _ in range(qty):
                oid = state.next_token_id()
                tok = Permanent(
                    object_id=oid,
                    oracle_id=f"token:{effect.name}",
                    name=effect.name,
                    controller="you",
                    zone=Zone.BATTLEFIELD,
                    is_token=True,
                    is_creature=effect.is_creature,
                    is_artifact=effect.is_artifact or effect.treasure,
                    power=effect.power,
                    toughness=effect.toughness,
                )
                state.permanents[oid] = tok
                state.bump("token")
                self._on_etb(state, tok)
                self._queue_triggers(state, TriggerEvent.CREATE_TOKEN, tok)
            return None

        if isinstance(effect, AddCounterEffect):
            if effect.target == "each_controlled_creature":
                qty = effect.quantity
                if effect.amount_from_trigger:
                    if trigger_amount is None or trigger_amount <= 0:
                        return ExecError(
                            VerificationStatus.ILLEGAL_ACTION,
                            "counter amount_from_trigger needs trigger amount",
                        )
                    qty = trigger_amount
                hosts = [
                    p
                    for p in state.permanents.values()
                    if p.zone == Zone.BATTLEFIELD
                    and p.controller == "you"
                    and p.is_creature
                ]
                for p in sorted(hosts, key=lambda x: x.object_id):
                    put_qty = qty
                    if effect.counter_type in {"m1m1", "-1/-1"}:
                        put_qty = self.m1m1_put_quantity(state, put_qty)
                    elif effect.counter_type in {"p1p1", "+1/+1"}:
                        put_qty = self.p1p1_put_quantity(
                            state, put_qty, permanent=p
                        )
                    if put_qty > 0:
                        p.counters[effect.counter_type] = (
                            p.counters.get(effect.counter_type, 0) + put_qty
                        )
                        state.bump("counter_added", put_qty)
                        self._queue_triggers(
                            state, TriggerEvent.COUNTER_ADDED, p, amount=put_qty
                        )
                return None
            if effect.target == "self":
                tid = source.object_id
            elif effect.target == "enchanted_creature":
                # Aura-granted "this creature" — host is the effect target (explorer
                # supplies a controlled creature; no attachment graph yet).
                tid = target_id
            else:
                tid = target_id
            if not tid or tid not in state.permanents:
                return ExecError(VerificationStatus.ILLEGAL_TARGET, "counter target")
            p = state.permanents[tid]
            if effect.target == "target_other_creature":
                if tid == source.object_id or not p.is_creature:
                    return ExecError(
                        VerificationStatus.ILLEGAL_TARGET,
                        "counter target must be another creature",
                    )
            if effect.target == "enchanted_creature":
                if tid == source.object_id or not p.is_creature:
                    return ExecError(
                        VerificationStatus.ILLEGAL_TARGET,
                        "enchanted counter host must be a creature",
                    )
            qty = effect.quantity
            if effect.amount_from_trigger:
                if trigger_amount is None or trigger_amount <= 0:
                    return ExecError(
                        VerificationStatus.ILLEGAL_ACTION,
                        "counter amount_from_trigger needs trigger amount",
                    )
                qty = trigger_amount
            if effect.counter_type in {"m1m1", "-1/-1"}:
                qty = self.m1m1_put_quantity(state, qty)
            elif effect.counter_type in {"p1p1", "+1/+1"}:
                qty = self.p1p1_put_quantity(state, qty, permanent=p)
            if qty > 0:
                p.counters[effect.counter_type] = (
                    p.counters.get(effect.counter_type, 0) + qty
                )
                state.bump("counter_added", qty)
                self._queue_triggers(
                    state, TriggerEvent.COUNTER_ADDED, p, amount=qty
                )
            return None

        if isinstance(effect, GrantLifelinkEffect):
            tid = target_id
            if not tid or tid not in state.permanents:
                return ExecError(
                    VerificationStatus.ILLEGAL_TARGET,
                    "grant lifelink needs target creature",
                )
            p = state.permanents[tid]
            if tid == source.object_id or not p.is_creature:
                return ExecError(
                    VerificationStatus.ILLEGAL_TARGET,
                    "grant lifelink target must be another creature",
                )
            p.lifelink = True
            return None

        if isinstance(effect, GrantTapBounceNonlandEffect):
            tid = target_id
            if not tid or tid not in state.permanents:
                return ExecError(
                    VerificationStatus.ILLEGAL_TARGET,
                    "grant tap-bounce needs target creature",
                )
            p = state.permanents[tid]
            if not p.is_creature or p.zone != Zone.BATTLEFIELD:
                return ExecError(
                    VerificationStatus.ILLEGAL_TARGET,
                    "grant tap-bounce target must be a battlefield creature",
                )
            p.tap_bounce_nonland = True
            return None

        if isinstance(effect, RemoveCounterEffect):
            tid = source.object_id
            p = state.permanents[tid]
            have = p.counters.get(effect.counter_type, 0)
            if have < effect.quantity:
                return ExecError(
                    VerificationStatus.RESOURCE_DEFICIT, "not enough counters"
                )
            p.counters[effect.counter_type] = have - effect.quantity
            return None

        if isinstance(effect, ReturnToBattlefieldEffect):
            source.zone = Zone.BATTLEFIELD
            source.tapped = False
            source.summoning_sick = True
            source.damage_marked = 0
            state.bump("return_to_battlefield")
            self._on_etb(state, source)
            return None

        if isinstance(effect, DealDamageEffect):
            qty = effect.amount
            if effect.amount_from_trigger:
                if trigger_amount is None or trigger_amount <= 0:
                    return ExecError(
                        VerificationStatus.ILLEGAL_ACTION,
                        "damage amount_from_trigger needs trigger amount",
                    )
                qty = trigger_amount
            if effect.target == "each_player":
                state.life_you -= qty
                state.life_opponent -= qty
                self._queue_triggers(
                    state,
                    TriggerEvent.OPPONENT_LOSE_LIFE,
                    source,
                    amount=qty,
                )
            else:
                to_opponent = effect.target == "opponent" or (
                    effect.target == "any_target"
                    and target_id in (None, "opponent")
                )
                if to_opponent:
                    state.life_opponent -= qty
                    self._queue_triggers(
                        state,
                        TriggerEvent.OPPONENT_LOSE_LIFE,
                        source,
                        amount=qty,
                    )
                    self._queue_triggers(
                        state,
                        TriggerEvent.DAMAGE_OPPONENT,
                        source,
                        amount=qty,
                    )
                elif effect.target == "any_target" and target_id is not None:
                    # CR 702.92 / Triskelion-class: any-target may include the source.
                    victim = state.permanents.get(target_id)
                    if (
                        victim is None
                        or victim.zone != Zone.BATTLEFIELD
                        or not victim.is_creature
                    ):
                        return ExecError(
                            VerificationStatus.ILLEGAL_TARGET,
                            "damage target must be a battlefield creature",
                        )
                    victim.damage_marked += qty
                    self._queue_triggers(
                        state,
                        TriggerEvent.DEALT_DAMAGE,
                        victim,
                        amount=qty,
                    )
                else:
                    return ExecError(
                        VerificationStatus.ILLEGAL_TARGET,
                        "deal damage needs opponent or creature target",
                    )
            state.bump("damage", qty)
            if source.lifelink and qty > 0:
                state.life_you += qty
                state.bump("life_gain", qty)
                self._queue_triggers(
                    state, TriggerEvent.GAIN_LIFE, source, amount=qty
                )
            return None

        if isinstance(effect, GainLifeEffect):
            qty = (
                trigger_amount
                if effect.amount_from_trigger and trigger_amount is not None
                else effect.amount
            )
            if qty is None or qty <= 0:
                return ExecError(VerificationStatus.ILLEGAL_ACTION, "gain life amount")
            state.life_you += qty
            state.bump("life_gain", qty)
            self._queue_triggers(state, TriggerEvent.GAIN_LIFE, source, amount=qty)
            return None

        if isinstance(effect, DrawEffect):
            for _ in range(max(int(effect.amount), 0)):
                state.bump("draw", 1)
                self._queue_triggers(state, TriggerEvent.DRAW, source, amount=1)
            return None

        if isinstance(effect, LoseLifeEffect):
            if effect.half_life_rounded_up:
                life = (
                    state.life_opponent if effect.who == "opponent" else state.life_you
                )
                qty = (life + 1) // 2
            else:
                qty = (
                    trigger_amount
                    if effect.amount_from_trigger and trigger_amount is not None
                    else effect.amount
                )
            if qty is None or qty <= 0:
                return ExecError(VerificationStatus.ILLEGAL_ACTION, "lose life amount")
            if effect.who == "opponent":
                state.life_opponent -= qty
                self._queue_triggers(
                    state,
                    TriggerEvent.OPPONENT_LOSE_LIFE,
                    source,
                    amount=qty,
                )
            else:
                state.life_you -= qty
            state.bump("life_loss", qty)
            return None

        if isinstance(effect, MillEffect):
            qty = effect.amount
            if qty <= 0:
                return ExecError(VerificationStatus.ILLEGAL_ACTION, "mill amount")
            if effect.who == "opponent":
                state.bump("mill", qty)
                for _ in range(qty):
                    self._queue_triggers(
                        state,
                        TriggerEvent.CARD_TO_OPPONENT_GRAVEYARD,
                        source,
                    )
            else:
                # Self-mill: count only (no library model) — Mesmeric Orb class.
                state.bump("mill", qty)
            return None

        if isinstance(effect, MoveToZoneEffect):
            if effect.target == "self":
                source.zone = effect.zone
                return None
            if effect.target in {
                "controlled_creature",
                "controlled_creature_green_or_white",
                "controlled_permanent",
                "controlled_nonland",
                "other_controlled_creature",
                "other_controlled_sharing_type",
                "target_nonland",
                "target_permanent",
            }:
                return self._bounce_to_zone(
                    state,
                    effect=effect,
                    target_id=target_id,
                    source=source,
                    trigger_subject_id=trigger_subject_id,
                )
            return ExecError(
                VerificationStatus.UNSUPPORTED_SEMANTICS,
                f"unsupported move target {effect.target}",
            )

        return ExecError(
            VerificationStatus.UNSUPPORTED_SEMANTICS, f"unknown effect {effect}"
        )

    def _permanent_colors(self, permanent: Permanent) -> set[str]:
        colors = {c.upper() for c in permanent.colors}
        if colors:
            return colors
        card = self.semantics.get(permanent.oracle_id)
        return {c.upper() for c in (card.colors if card else [])}

    _PERMANENT_TYPES = frozenset(
        {
            "artifact",
            "battle",
            "creature",
            "enchantment",
            "land",
            "planeswalker",
            "kindred",
            "tribal",
        }
    )

    def _permanent_type_set(self, permanent: Permanent) -> set[str]:
        """CR 205.2a permanent types from card types + runtime flags."""
        card = self.semantics.get(permanent.oracle_id)
        types = {t.casefold() for t in (card.types if card else [])}
        if permanent.is_creature:
            types.add("creature")
        if permanent.is_artifact:
            types.add("artifact")
        return types & self._PERMANENT_TYPES

    def _creature_subtypes(self, permanent: Permanent) -> set[str]:
        """Creature subtypes for Mana Echoes-style type sharing."""
        card = self.semantics.get(permanent.oracle_id)
        if card is not None:
            return {
                t.casefold()
                for t in card.types
                if t.casefold() not in _NON_CREATURE_TYPE_WORDS
            }
        # Token without registered semantics: infer from name words (e.g. "colorless Sliver").
        if permanent.is_creature:
            return {
                w
                for w in permanent.name.casefold().split()
                if w not in _NON_CREATURE_TYPE_WORDS
            }
        return set()

    def _is_land_permanent(self, permanent: Permanent) -> bool:
        return "land" in self._permanent_type_set(permanent)

    def _is_basic_land(self, permanent: Permanent) -> bool:
        card = self.semantics.get(permanent.oracle_id)
        types = {t.casefold() for t in (card.types if card else [])}
        return "land" in types and "basic" in types

    def _is_artifact_permanent(self, permanent: Permanent) -> bool:
        return "artifact" in self._permanent_type_set(permanent)

    def _bounce_to_zone(
        self,
        state: GameState,
        *,
        effect: MoveToZoneEffect,
        target_id: str | None,
        source: Permanent | None = None,
        trigger_subject_id: str | None = None,
    ) -> ExecError | None:
        if not target_id or target_id not in state.permanents:
            return ExecError(
                VerificationStatus.ILLEGAL_TARGET, "bounce needs a permanent"
            )
        bounced = state.permanents[target_id]
        if bounced.zone != Zone.BATTLEFIELD:
            return ExecError(
                VerificationStatus.ILLEGAL_TARGET,
                "bounce target must be on the battlefield",
            )
        tgt = effect.target
        if tgt in {
            "controlled_creature",
            "controlled_creature_green_or_white",
            "controlled_permanent",
            "controlled_nonland",
            "other_controlled_creature",
            "other_controlled_sharing_type",
        }:
            if bounced.controller != "you":
                return ExecError(
                    VerificationStatus.ILLEGAL_TARGET,
                    "bounce target must be controlled by you",
                )
        if tgt in {
            "controlled_creature",
            "controlled_creature_green_or_white",
            "other_controlled_creature",
        }:
            if not bounced.is_creature:
                return ExecError(
                    VerificationStatus.ILLEGAL_TARGET,
                    "bounce target must be a controlled creature",
                )
        if tgt == "other_controlled_creature":
            if source is not None and bounced.object_id == source.object_id:
                return ExecError(
                    VerificationStatus.ILLEGAL_TARGET,
                    "bounce target must be another creature",
                )
        if tgt == "other_controlled_sharing_type":
            subject_id = trigger_subject_id
            if not subject_id or subject_id not in state.permanents:
                return ExecError(
                    VerificationStatus.ILLEGAL_TARGET,
                    "type-share bounce needs trigger subject",
                )
            if bounced.object_id == subject_id:
                return ExecError(
                    VerificationStatus.ILLEGAL_TARGET,
                    "bounce target must be another permanent",
                )
            subject = state.permanents[subject_id]
            if not (
                self._permanent_type_set(bounced) & self._permanent_type_set(subject)
            ):
                return ExecError(
                    VerificationStatus.ILLEGAL_TARGET,
                    "bounce target must share a permanent type with subject",
                )
        if tgt == "controlled_creature_green_or_white":
            colors = self._permanent_colors(bounced)
            if not (colors & {"G", "W"}):
                return ExecError(
                    VerificationStatus.ILLEGAL_TARGET,
                    "bounce target must be green or white",
                )
        if tgt in {"controlled_nonland", "target_nonland"}:
            if self._is_land_permanent(bounced):
                return ExecError(
                    VerificationStatus.ILLEGAL_TARGET,
                    "bounce target must be nonland",
                )
        bounced.zone = effect.zone
        bounced.tapped = False
        if effect.zone == Zone.HAND:
            bounced.was_cast = False
            bounced.summoning_sick = False
        return None

    def _on_etb(self, state: GameState, permanent: Permanent) -> None:
        state.bump("etb")
        self._queue_triggers(state, TriggerEvent.ENTER_BATTLEFIELD, permanent)

    def _untap_permanent(self, state: GameState, permanent: Permanent) -> bool:
        """BF tapped→untapped transition; queues UNTAP triggers. Returns True if changed."""
        if permanent.zone != Zone.BATTLEFIELD or not permanent.tapped:
            return False
        permanent.tapped = False
        self._queue_triggers(state, TriggerEvent.UNTAP, permanent)
        return True

    def _queue_triggers(
        self,
        state: GameState,
        event: TriggerEvent,
        subject: Permanent,
        *,
        amount: int | None = None,
    ) -> None:
        for perm in list(state.permanents.values()):
            if perm.zone != Zone.BATTLEFIELD or perm.controller != "you":
                continue
            card = self.semantics.get(perm.oracle_id)
            if not card:
                continue
            for ab in card.abilities:
                if not isinstance(ab, TriggeredAbility) or ab.event != event:
                    continue
                if not ab.supported:
                    continue
                if ab.filter == "self" and subject.object_id != perm.object_id:
                    continue
                if ab.filter == "creature" and not subject.is_creature:
                    continue
                if ab.filter == "controlled_creature" and (
                    not subject.is_creature or subject.controller != "you"
                ):
                    continue
                if ab.filter == "controlled_nonartifact":
                    if subject.controller != "you" or self._is_artifact_permanent(
                        subject
                    ):
                        continue
                if ab.filter == "other_controlled_creature" and (
                    not subject.is_creature
                    or subject.controller != "you"
                    or subject.object_id == perm.object_id
                ):
                    continue
                if ab.filter == "other_controlled_human":
                    if (
                        not subject.is_creature
                        or subject.controller != "you"
                        or subject.object_id == perm.object_id
                    ):
                        continue
                    subj_card = self.semantics.get(subject.oracle_id)
                    types = [t.casefold() for t in (subj_card.types if subj_card else [])]
                    if "human" not in types:
                        continue
                if ab.filter == "other_controlled_green":
                    if (
                        not subject.is_creature
                        or subject.controller != "you"
                        or subject.object_id == perm.object_id
                    ):
                        continue
                    # Prefer permanent.colors; fall back to CardSemantics.colors.
                    colors = {c.upper() for c in subject.colors}
                    if not colors:
                        subj_card = self.semantics.get(subject.oracle_id)
                        colors = {
                            c.upper() for c in (subj_card.colors if subj_card else [])
                        }
                    if "G" not in colors:
                        continue
                if ab.filter == "token_creature" and not (
                    subject.is_token and subject.is_creature
                ):
                    continue
                # CR 603.4 intervening-if (cast): only if subject entered via cast_from_hand.
                if ab.intervening_if == "cast" and not subject.was_cast:
                    continue
                entry = {
                    "source_id": perm.object_id,
                    "ability_id": ab.ability_id,
                    "subject_id": subject.object_id,
                }
                if amount is not None:
                    entry["amount"] = amount
                state.pending_triggers.append(entry)

    def die(self, state: GameState, permanent: Permanent) -> None:
        # CR 700.4: "dies" means BF→GY for any permanent.
        # Engine ``events.death`` / OutputType.DEATH count *creature* deaths only
        # (Blood Artist-class outputs); DIES triggers still queue for all and
        # filter by ``filter="creature"`` where needed.
        # Exile replacements (e.g. Rest in Peace) suppress death events and DIES triggers.
        # Sacrifice events still fire before this replacement is applied.
        # CR 702.92a/c: undying returns iff the creature had no +1/+1 counters when it died.
        had_p1p1 = permanent.counters.get("p1p1", 0)
        had_undying = permanent.undying
        permanent.damage_marked = 0
        if self.has_exile_on_death(state) and permanent.is_creature:
            permanent.zone = Zone.EXILE
            permanent.tapped = False
            return
        if permanent.is_creature:
            state.bump("death")
        tough = permanent.effective_toughness()
        self._queue_triggers(
            state,
            TriggerEvent.DIES,
            permanent,
            amount=tough if tough is not None and tough > 0 else None,
        )
        permanent.zone = Zone.GRAVEYARD
        permanent.tapped = False
        if had_undying and had_p1p1 == 0:
            state.pending_triggers.append(
                {
                    "source_id": permanent.object_id,
                    "ability_id": "__undying_return__",
                    "subject_id": permanent.object_id,
                }
            )

    def apply_state_based_actions(
        self, state: GameState, *, max_iters: int = 16
    ) -> None:
        """CR 704.5f/g: creatures with toughness ≤ 0 or lethal damage die.

        Iterates until stable or ``max_iters`` (undying / death cascades).
        """
        for _ in range(max_iters):
            doomed: list[Permanent] = []
            for perm in state.permanents.values():
                if perm.zone != Zone.BATTLEFIELD or perm.controller != "you":
                    continue
                if not perm.is_creature:
                    continue
                et = perm.effective_toughness()
                if et is None:
                    continue
                if et <= 0 or perm.damage_marked >= et:
                    doomed.append(perm)
            if not doomed:
                return
            for perm in doomed:
                self.die(state, perm)

    def sacrifice(self, state: GameState, permanent: Permanent) -> None:
        state.bump("sacrifice")
        self._queue_triggers(state, TriggerEvent.SACRIFICED, permanent)
        self.die(state, permanent)

    @staticmethod
    def matches_sacrifice_selector(permanent: Permanent, selector: str) -> bool:
        """BF + combo-player control + type constraints for sacrifice selectors."""
        if permanent.zone != Zone.BATTLEFIELD or permanent.controller != "you":
            return False
        if selector == "self":
            return True
        if selector == "creature_controlled":
            return permanent.is_creature
        if selector == "token_creature_controlled":
            return permanent.is_token and permanent.is_creature
        return False

    def _validate_tap_host(
        self,
        tap_perm: Permanent | None,
        *,
        host: str = "creature",
    ) -> ExecError | None:
        """Host for enchanted {T}: BF, controlled, untapped; kind from ``TapCost.host``."""
        if tap_perm is None:
            return ExecError(VerificationStatus.ILLEGAL_TARGET, "tap host missing")
        if tap_perm.zone != Zone.BATTLEFIELD:
            return ExecError(
                VerificationStatus.ILLEGAL_TARGET, "tap host not on battlefield"
            )
        if tap_perm.controller != "you":
            return ExecError(
                VerificationStatus.ILLEGAL_TARGET, "tap host not controlled"
            )
        if host == "land":
            if not self._is_land_permanent(tap_perm):
                return ExecError(
                    VerificationStatus.ILLEGAL_TARGET, "tap host not a land"
                )
        elif not tap_perm.is_creature:
            return ExecError(
                VerificationStatus.ILLEGAL_TARGET, "tap host not a creature"
            )
        if tap_perm.tapped:
            return ExecError(VerificationStatus.ILLEGAL_ACTION, "already tapped")
        # CR 302.6: creatures with summoning sickness cannot {T}; lands have no sickness.
        if host == "creature" and tap_perm.summoning_sick:
            return ExecError(VerificationStatus.TIMING_VIOLATION, "summoning sick")
        return None

    def _validate_explicit_sacrifice(
        self, state: GameState, fodder_id: str, selector: str
    ) -> ExecError | None:
        fodder = state.permanents.get(fodder_id)
        if fodder is None:
            return ExecError(
                VerificationStatus.ILLEGAL_TARGET, "sacrifice target missing"
            )
        # Wrong controller / type: adversarial illegal target.
        if fodder.controller != "you":
            return ExecError(
                VerificationStatus.ILLEGAL_TARGET,
                f"sacrifice target illegal for {selector}",
            )
        if selector == "creature_controlled" and not fodder.is_creature:
            return ExecError(
                VerificationStatus.ILLEGAL_TARGET,
                f"sacrifice target illegal for {selector}",
            )
        if selector == "token_creature_controlled" and not (
            fodder.is_token and fodder.is_creature
        ):
            return ExecError(
                VerificationStatus.ILLEGAL_TARGET,
                f"sacrifice target illegal for {selector}",
            )
        # Consumed / off-battlefield: resource exhausted (finite fodder loops).
        if fodder.zone != Zone.BATTLEFIELD:
            return ExecError(
                VerificationStatus.RESOURCE_DEFICIT,
                "sacrifice target not on battlefield",
            )
        return None


    def _controls_metalcraft(self, state: GameState) -> bool:
        n = sum(
            1
            for p in state.permanents.values()
            if p.zone == Zone.BATTLEFIELD
            and p.controller == "you"
            and p.is_artifact
        )
        return n >= 3

    def _has_controlled_power_at_least(self, state: GameState, need: int) -> bool:
        for p in state.permanents.values():
            if p.zone != Zone.BATTLEFIELD or p.controller != "you":
                continue
            if not p.is_creature:
                continue
            power = p.effective_power()
            if power is not None and power >= need:
                return True
        return False

    def _controls_zombie(self, state: GameState) -> bool:
        for perm in state.permanents.values():
            if perm.zone != Zone.BATTLEFIELD or not perm.is_creature:
                continue
            if perm.controller != "you":
                continue
            card = self.semantics.get(perm.oracle_id)
            if card is not None and any("zombie" in t.casefold() for t in card.types):
                return True
            if "zombie" in perm.name.casefold():
                return True
        return False

    def _graveyard_drain_seed_amount(self) -> int:
        """Path-b seed sizing: match partner fixed graveyard drain when present."""
        qty = 1
        for card in self.semantics.values():
            for ab in card.abilities:
                if (
                    isinstance(ab, TriggeredAbility)
                    and ab.event == TriggerEvent.CARD_TO_OPPONENT_GRAVEYARD
                ):
                    for effect in ab.effects:
                        if isinstance(effect, LoseLifeEffect) and effect.amount:
                            qty = max(qty, effect.amount)
        return qty

    def activate(
        self, state: GameState, step: ActionStep
    ) -> ExecError | None:
        if not step.actor or not step.ability_id:
            return ExecError(VerificationStatus.ILLEGAL_ACTION, "activate needs actor/ability")
        perm = state.permanents.get(step.actor)
        if not perm:
            return ExecError(VerificationStatus.ILLEGAL_ACTION, "actor missing")
        if perm.controller != "you":
            return ExecError(
                VerificationStatus.ILLEGAL_ACTION,
                "cannot activate opponent-controlled permanent",
            )
        ab = self.find_ability(perm.oracle_id, step.ability_id)
        if not isinstance(ab, ActivatedAbility):
            return ExecError(VerificationStatus.ILLEGAL_ACTION, "ability not activated")
        if not ab.supported:
            return ExecError(
                VerificationStatus.UNSUPPORTED_SEMANTICS, f"unsupported {ab.ability_id}"
            )
        # Battlefield by default; GY allowed when ability returns self to battlefield.
        from_gy = any(isinstance(e, ReturnToBattlefieldEffect) for e in ab.effects)
        if perm.zone == Zone.GRAVEYARD and not from_gy:
            return ExecError(VerificationStatus.ILLEGAL_ACTION, "cannot activate from GY")
        if perm.zone not in (Zone.BATTLEFIELD, Zone.GRAVEYARD):
            return ExecError(VerificationStatus.ILLEGAL_ACTION, f"bad zone {perm.zone}")
        if perm.zone == Zone.BATTLEFIELD and from_gy:
            return ExecError(VerificationStatus.ILLEGAL_ACTION, "return ability needs GY")
        if ab.requires_zombie and not self._controls_zombie(state):
            return ExecError(VerificationStatus.ILLEGAL_ACTION, "need a Zombie")
        if ab.requires_metalcraft and not self._controls_metalcraft(state):
            return ExecError(
                VerificationStatus.ILLEGAL_ACTION, "need metalcraft (3+ artifacts)"
            )
        if ab.requires_controlled_power_at_least is not None:
            need = ab.requires_controlled_power_at_least
            if not self._has_controlled_power_at_least(state, need):
                return ExecError(
                    VerificationStatus.ILLEGAL_ACTION,
                    f"need controlled creature power {need}+",
                )
        if ab.once_per_turn and ab.ability_id in perm.once_per_turn_used:
            return ExecError(VerificationStatus.ONCE_PER_TURN_LIMIT, ab.ability_id)

        # Costs
        reduction, mana_floor = self.cost_reduction(state, ability=ab, actor=perm)
        for cost in ab.costs:
            if isinstance(cost, TapCost):
                tap_perm = perm
                if not cost.source_self:
                    if not step.target:
                        return ExecError(
                            VerificationStatus.ILLEGAL_ACTION, "tap cost needs host"
                        )
                    tap_perm = state.permanents.get(step.target)
                    err = self._validate_tap_host(tap_perm, host=cost.host)
                    if err:
                        return err
                else:
                    if tap_perm.tapped:
                        return ExecError(
                            VerificationStatus.ILLEGAL_ACTION, "already tapped"
                        )
                    # CR 302.6: {T} on a sick creature is illegal even for mana abilities.
                    if tap_perm.is_creature and tap_perm.summoning_sick:
                        return ExecError(
                            VerificationStatus.TIMING_VIOLATION, "summoning sick"
                        )
                assert tap_perm is not None
                tap_perm.tapped = True
                # Host-tap activations still apply effects from the aura actor;
                # do not pass the host as an effect target unless the effect asks.
                if not cost.source_self:
                    step = step.model_copy(update={"target": None})
            elif isinstance(cost, ManaCost):
                need = cost.amount.model_copy(deep=True)
                reduced = min(reduction, need.generic)
                need.generic -= reduced
                reduction -= reduced
                if mana_floor > 0:
                    current = need.total()
                    if current < mana_floor:
                        need.generic += mana_floor - current
                err = self.pay_mana(state, need, allow_activate_only=True)
                if err:
                    return err
            elif isinstance(cost, HybridManaCost):
                paid = False
                for color in cost.colors:
                    if color not in ("white", "blue", "black", "red", "green"):
                        continue
                    if getattr(state.mana, color) <= 0 and state.mana.any_color <= 0:
                        continue
                    err = self.pay_mana(state, ManaAmount(**{color: 1}), allow_activate_only=True)
                    if err is None:
                        paid = True
                        break
                if not paid:
                    return ExecError(
                        VerificationStatus.MANA_RESTRICTION,
                        f"cannot pay hybrid {'/'.join(cost.colors)}",
                    )
            elif isinstance(cost, AddCounterCost):
                qty = cost.quantity
                if cost.counter_type in {"m1m1", "-1/-1"}:
                    qty = self.m1m1_put_quantity(state, qty)
                elif cost.counter_type in {"p1p1", "+1/+1"}:
                    qty = self.p1p1_put_quantity(state, qty, permanent=perm)
                if qty > 0:
                    key = cost.counter_type
                    perm.counters[key] = perm.counters.get(key, 0) + qty
                    state.bump("counter", qty)
            elif isinstance(cost, RemoveCounterCost):
                if not step.target:
                    return ExecError(
                        VerificationStatus.ILLEGAL_ACTION,
                        "remove-counter cost needs target",
                    )
                host = state.permanents.get(step.target)
                if host is None:
                    return ExecError(
                        VerificationStatus.ILLEGAL_TARGET, "remove-counter host missing"
                    )
                if host.zone != Zone.BATTLEFIELD or host.controller != "you":
                    return ExecError(
                        VerificationStatus.ILLEGAL_TARGET,
                        "remove-counter host not controlled BF",
                    )
                if cost.selector == "creature_controlled" and not host.is_creature:
                    return ExecError(
                        VerificationStatus.ILLEGAL_TARGET,
                        "remove-counter host not a creature",
                    )
                key = cost.counter_type
                have = host.counters.get(key, 0)
                if have < cost.quantity:
                    return ExecError(
                        VerificationStatus.RESOURCE_DEFICIT,
                        f"need {cost.quantity} {key} counters",
                    )
                host.counters[key] = have - cost.quantity
                if host.counters[key] <= 0:
                    del host.counters[key]
                state.bump("counter", cost.quantity)
                # Host was only for the cost; do not pass through as effect target.
                step = step.model_copy(update={"target": None})
            elif isinstance(cost, UntapSymbolCost):
                untap_perm = perm
                if not cost.source_self:
                    if not step.target:
                        return ExecError(
                            VerificationStatus.ILLEGAL_ACTION,
                            "untap symbol cost needs host",
                        )
                    untap_perm = state.permanents.get(step.target)
                    if untap_perm is None:
                        return ExecError(
                            VerificationStatus.ILLEGAL_ACTION, "untap host missing"
                        )
                    if not untap_perm.is_creature:
                        return ExecError(
                            VerificationStatus.ILLEGAL_ACTION,
                            "untap symbol host must be creature",
                        )
                if not untap_perm.tapped:
                    return ExecError(
                        VerificationStatus.ILLEGAL_ACTION,
                        "must be tapped to pay untap symbol",
                    )
                self._untap_permanent(state, untap_perm)
                if not cost.source_self:
                    step = step.model_copy(update={"target": None})
            elif isinstance(cost, SacrificeCost):
                if cost.selector == "self":
                    if not self.matches_sacrifice_selector(perm, "self"):
                        return ExecError(
                            VerificationStatus.RESOURCE_DEFICIT,
                            "self not on battlefield",
                        )
                    self.sacrifice(state, perm)
                else:
                    fodder_id = step.target
                    if fodder_id:
                        err = self._validate_explicit_sacrifice(
                            state, fodder_id, cost.selector
                        )
                        if err:
                            return err
                    else:
                        fodder_id = self._pick_fodder(state, cost.selector)
                        if not fodder_id:
                            return ExecError(
                                VerificationStatus.RESOURCE_DEFICIT,
                                "no sacrifice fodder",
                            )
                    fodder = state.permanents[fodder_id]
                    self.sacrifice(state, fodder)
            elif isinstance(cost, TapCreatureCost):
                need = max(int(cost.quantity or 1), 1)
                tapped_ids: list[str] = []
                if step.cost_target and need == 1:
                    cand = state.permanents.get(step.cost_target)
                    if (
                        cand is not None
                        and cand.zone == Zone.BATTLEFIELD
                        and cand.controller == "you"
                        and cand.is_creature
                        and not cand.tapped
                        and (cost.allow_source or cand.object_id != perm.object_id)
                    ):
                        tapped_ids.append(cand.object_id)
                    else:
                        return ExecError(
                            VerificationStatus.ILLEGAL_TARGET,
                            "tap-creature cost_target illegal",
                        )
                while len(tapped_ids) < need:
                    picked = self._pick_tap_creature(
                        state,
                        source=perm,
                        allow_source=cost.allow_source,
                        exclude=set(tapped_ids),
                    )
                    if not picked:
                        return ExecError(
                            VerificationStatus.RESOURCE_DEFICIT,
                            "no untapped creature to tap for cost",
                        )
                    tapped_ids.append(picked)
                for tapped_id in tapped_ids:
                    tap_perm = state.permanents[tapped_id]
                    if tap_perm.tapped:
                        return ExecError(
                            VerificationStatus.ILLEGAL_ACTION, "already tapped"
                        )
                    # Not {T} on the creature — summoning sickness does not apply (CR 302.6).
                    tap_perm.tapped = True

        err = self.apply_effects(state, perm, ab.effects, step.target)
        if err:
            return err
        if ab.once_per_turn:
            perm.once_per_turn_used.add(ab.ability_id)
        return None

    def _pick_fodder(self, state: GameState, selector: str) -> str | None:
        # Prefer tokens for creature_controlled (generic fodder over essentials).
        if selector == "creature_controlled":
            for p in state.permanents.values():
                if (
                    self.matches_sacrifice_selector(p, selector)
                    and p.is_token
                ):
                    return p.object_id
        for p in state.permanents.values():
            if self.matches_sacrifice_selector(p, selector):
                return p.object_id
        return None

    def _pick_tap_creature(
        self,
        state: GameState,
        *,
        source: Permanent,
        allow_source: bool,
        exclude: set[str] | None = None,
    ) -> str | None:
        """Pick an untapped controlled creature to tap for Earthcraft-class costs.

        Summoning sickness does not apply: the creature is not activating its own {T}.
        Prefer creatures with self ``{Q}`` costs (Patrol Signaler) so Earthcraft can
        set up untap-symbol activations; among others prefer tokens (Nest squirrels).
        """
        skip = exclude or set()
        candidates: list[Permanent] = []
        for p in state.permanents.values():
            if p.object_id in skip:
                continue
            if p.zone != Zone.BATTLEFIELD or p.controller != "you":
                continue
            if not p.is_creature or p.tapped:
                continue
            if not allow_source and p.object_id == source.object_id:
                continue
            candidates.append(p)
        if not candidates:
            return None

        def sort_key(p: Permanent) -> tuple:
            card = self.semantics.get(p.oracle_id)
            has_self_q = False
            if card is not None:
                for ab in card.abilities:
                    if not isinstance(ab, ActivatedAbility):
                        continue
                    if any(
                        isinstance(c, UntapSymbolCost) and c.source_self for c in ab.costs
                    ):
                        has_self_q = True
                        break
            return (not has_self_q, not p.is_token, p.object_id)

        candidates.sort(key=sort_key)
        return candidates[0].object_id

    def resolve_trigger(self, state: GameState, step: ActionStep) -> ExecError | None:
        if not state.pending_triggers:
            return ExecError(VerificationStatus.ILLEGAL_ACTION, "no pending triggers")
        # Combo player orders favorably when actor/ability_id are unspecified.
        # When either is supplied, require an exact pending match — no idx-0 fallback.
        idx: int | None = None
        if step.ability_id or step.actor:
            for i, tr in enumerate(state.pending_triggers):
                if step.ability_id and tr["ability_id"] != step.ability_id:
                    continue
                if step.actor and tr["source_id"] != step.actor:
                    continue
                idx = i
                break
            if idx is None:
                return ExecError(
                    VerificationStatus.ILLEGAL_ACTION,
                    "no matching pending trigger",
                )
        else:
            idx = 0
        tr = state.pending_triggers.pop(idx)
        if tr["ability_id"] == "__undying_return__":
            return self._resolve_undying_return(state, tr)
        source = state.permanents[tr["source_id"]]
        ab = self.find_ability(source.oracle_id, tr["ability_id"])
        if not isinstance(ab, TriggeredAbility):
            return ExecError(VerificationStatus.ILLEGAL_ACTION, "bad trigger")
        # CR 603.4: re-check intervening-if on resolution.
        if ab.intervening_if == "cast":
            subject = state.permanents.get(tr.get("subject_id") or source.object_id)
            if subject is None or not subject.was_cast:
                return None
        return self.apply_effects(
            state,
            source,
            ab.effects,
            step.target or tr.get("subject_id"),
            trigger_amount=tr.get("amount"),
            trigger_subject_id=tr.get("subject_id"),
        )

    def _resolve_undying_return(
        self, state: GameState, tr: dict
    ) -> ExecError | None:
        """CR 702.92a/c synthetic return — no card ability lookup."""
        subject_id = tr.get("subject_id") or tr["source_id"]
        perm = state.permanents.get(subject_id)
        if perm is None:
            return ExecError(
                VerificationStatus.ILLEGAL_ACTION, "undying subject missing"
            )
        if perm.zone != Zone.GRAVEYARD:
            return ExecError(
                VerificationStatus.ILLEGAL_ACTION,
                "undying return requires graveyard",
            )
        perm.zone = Zone.BATTLEFIELD
        perm.tapped = False
        perm.summoning_sick = True
        perm.damage_marked = 0
        perm.counters["p1p1"] = perm.counters.get("p1p1", 0) + 1
        state.bump("return_to_battlefield")
        self._on_etb(state, perm)
        return None

    def run_step(self, state: GameState, step: ActionStep) -> ExecError | None:
        err = self._run_step_body(state, step)
        if err:
            return err
        self.apply_state_based_actions(state)
        return None

    def _run_step_body(self, state: GameState, step: ActionStep) -> ExecError | None:
        op = step.op
        if op == "activate":
            return self.activate(state, step)
        if op == "resolve_trigger":
            return self.resolve_trigger(state, step)
        if op == "sacrifice":
            if not step.actor:
                return ExecError(VerificationStatus.ILLEGAL_ACTION, "sacrifice needs actor")
            perm = state.permanents.get(step.actor)
            if not perm:
                return ExecError(VerificationStatus.ILLEGAL_ACTION, "missing permanent")
            if not self.matches_sacrifice_selector(perm, "self"):
                return ExecError(
                    VerificationStatus.ILLEGAL_TARGET,
                    "cannot sacrifice illegal permanent",
                )
            self.sacrifice(state, perm)
            return None
        if op == "choose_may":
            # Combo player: yes advances proof when choose_may True.
            if step.choose_may is False:
                return ExecError(
                    VerificationStatus.NOT_A_LOOP, "combo player declined may"
                )
            return None
        if op == "noop":
            return None
        if op == "seed_gain_life":
            # Explicit Path-b generic life-gain seed (ADR 0002 fodder-style).
            qty = 1
            state.life_you += qty
            state.bump("life_gain", qty)
            source = state.permanents.get(step.actor) if step.actor else None
            if source is None:
                return ExecError(
                    VerificationStatus.ILLEGAL_ACTION,
                    "seed_gain_life needs actor with GAIN_LIFE triggers",
                )
            self._queue_triggers(state, TriggerEvent.GAIN_LIFE, source, amount=qty)
            return None
        if op == "seed_lose_life":
            # Path-b generic opponent life-loss seed (Mindcrank / Bloodchief class).
            qty = self._graveyard_drain_seed_amount()
            state.life_opponent -= qty
            state.bump("life_loss", qty)
            source = state.permanents.get(step.actor) if step.actor else None
            if source is None:
                return ExecError(
                    VerificationStatus.ILLEGAL_ACTION,
                    "seed_lose_life needs actor with OPPONENT_LOSE_LIFE triggers",
                )
            self._queue_triggers(
                state, TriggerEvent.OPPONENT_LOSE_LIFE, source, amount=qty
            )
            return None
        if op == "seed_create_token":
            # Generic token-create seed for CREATE_TOKEN feedback loops (Rosie class).
            source = state.permanents.get(step.actor) if step.actor else None
            if source is None:
                return ExecError(
                    VerificationStatus.ILLEGAL_ACTION,
                    "seed_create_token needs actor with CREATE_TOKEN triggers",
                )
            err = self.apply_effects(
                state,
                source,
                [
                    CreateTokenEffect(
                        name="Food",
                        power=0,
                        toughness=0,
                        quantity=1,
                        is_creature=False,
                        is_artifact=True,
                    )
                ],
                None,
            )
            return err
        if op == "seed_grant_lifelink":
            # Heliod-class: grant lifelink to a creature for the closed damage loop.
            if not step.target or step.target not in state.permanents:
                return ExecError(
                    VerificationStatus.ILLEGAL_TARGET,
                    "seed_grant_lifelink needs target creature",
                )
            perm = state.permanents[step.target]
            if not perm.is_creature:
                return ExecError(
                    VerificationStatus.ILLEGAL_TARGET,
                    "seed_grant_lifelink target must be a creature",
                )
            perm.lifelink = True
            return None
        if op == "seed_grant_undying":
            # Mikaeus-class: grant undying for counter-gated return (physics seed).
            if not step.target or step.target not in state.permanents:
                return ExecError(
                    VerificationStatus.ILLEGAL_TARGET,
                    "seed_grant_undying needs target creature",
                )
            perm = state.permanents[step.target]
            if not perm.is_creature:
                return ExecError(
                    VerificationStatus.ILLEGAL_TARGET,
                    "seed_grant_undying target must be a creature",
                )
            perm.undying = True
            return None
        if op == "seed_grant_tap_bounce":
            # Banishing Knack / Retraction Helix Instant: setup grant (witness-persistent).
            if not step.target or step.target not in state.permanents:
                return ExecError(
                    VerificationStatus.ILLEGAL_TARGET,
                    "seed_grant_tap_bounce needs target creature",
                )
            perm = state.permanents[step.target]
            if not perm.is_creature or perm.zone != Zone.BATTLEFIELD:
                return ExecError(
                    VerificationStatus.ILLEGAL_TARGET,
                    "seed_grant_tap_bounce target must be a battlefield creature",
                )
            perm.tap_bounce_nonland = True
            return None
        if op == "cast_from_hand":
            return self.cast_from_hand(state, step)
        if op == "activate_granted_tap_bounce":
            return self.activate_granted_tap_bounce(state, step)
        if op == "opponent_must_cooperate":
            return ExecError(
                VerificationStatus.OPPONENT_COOPERATION_REQUIRED,
                step.note or "opponent cooperation required",
            )
        return ExecError(VerificationStatus.UNSUPPORTED_RULE, f"unknown op {op}")

    def free_cast_max_mv(self, state: GameState) -> int | None:
        """Highest Aluren-class free-cast MV ceiling on the battlefield, if any."""
        best: int | None = None
        for perm in state.permanents.values():
            if perm.zone != Zone.BATTLEFIELD or perm.controller != "you":
                continue
            card = self.semantics.get(perm.oracle_id)
            if card is None:
                continue
            for ab in card.abilities:
                if isinstance(ab, FreeCastCreaturesByManaValue) and ab.supported:
                    best = (
                        ab.max_mana_value
                        if best is None
                        else max(best, ab.max_mana_value)
                    )
        return best

    def cast_from_hand(
        self, state: GameState, step: ActionStep
    ) -> ExecError | None:
        """Cast a permanent spell from hand (creatures + artifacts for rock/Tidespout)."""
        if not step.actor:
            return ExecError(VerificationStatus.ILLEGAL_ACTION, "cast needs actor")
        perm = state.permanents.get(step.actor)
        if perm is None:
            return ExecError(VerificationStatus.ILLEGAL_ACTION, "cast actor missing")
        if perm.zone != Zone.HAND or perm.controller != "you":
            return ExecError(
                VerificationStatus.ILLEGAL_ACTION, "cast requires card in hand"
            )
        if not (perm.is_creature or perm.is_artifact):
            return ExecError(
                VerificationStatus.UNSUPPORTED_SEMANTICS,
                "cast_from_hand models creatures and artifacts only",
            )
        card = self.semantics.get(perm.oracle_id)
        if card is None:
            return ExecError(VerificationStatus.ILLEGAL_ACTION, "cast missing semantics")
        free_max = self.free_cast_max_mv(state)
        free = free_max is not None and card.mana_value <= free_max
        if not free:
            err = self.pay_mana(state, card.mana_cost)
            if err:
                return err
        perm.zone = Zone.BATTLEFIELD
        perm.tapped = False
        perm.summoning_sick = bool(perm.is_creature)
        perm.damage_marked = 0
        perm.was_cast = True
        state.bump("cast")
        # CAST triggers see the spell as cast; subject is the permanent that entered.
        self._queue_triggers(state, TriggerEvent.CAST, perm)
        self._on_etb(state, perm)
        return None

    def activate_granted_tap_bounce(
        self, state: GameState, step: ActionStep
    ) -> ExecError | None:
        """Knack/Helix grant: {T}: return target nonland permanent to hand."""
        if not step.actor or not step.target:
            return ExecError(
                VerificationStatus.ILLEGAL_ACTION,
                "granted tap-bounce needs actor and target",
            )
        actor = state.permanents.get(step.actor)
        if actor is None:
            return ExecError(VerificationStatus.ILLEGAL_ACTION, "actor missing")
        if (
            actor.zone != Zone.BATTLEFIELD
            or actor.controller != "you"
            or not actor.tap_bounce_nonland
        ):
            return ExecError(
                VerificationStatus.ILLEGAL_ACTION,
                "actor lacks granted tap-bounce",
            )
        if actor.tapped:
            return ExecError(VerificationStatus.ILLEGAL_ACTION, "already tapped")
        if actor.summoning_sick:
            return ExecError(VerificationStatus.TIMING_VIOLATION, "summoning sick")
        target = state.permanents.get(step.target)
        if target is None or target.zone != Zone.BATTLEFIELD:
            return ExecError(
                VerificationStatus.ILLEGAL_TARGET,
                "bounce target must be on the battlefield",
            )
        card = self.semantics.get(target.oracle_id)
        types = [t.casefold() for t in (card.types if card else [])]
        if "land" in types:
            return ExecError(
                VerificationStatus.ILLEGAL_TARGET,
                "bounce target must be nonland",
            )
        actor.tapped = True
        target.zone = Zone.HAND
        target.tapped = False
        return None

    def run_sequence(
        self, state: GameState, steps: list[ActionStep]
    ) -> ExecError | None:
        for step in steps:
            err = self.run_step(state, step)
            if err:
                return err
        return None
