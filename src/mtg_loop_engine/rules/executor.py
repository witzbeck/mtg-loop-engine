"""Rules-aware action executor for witness replay."""

from __future__ import annotations

from dataclasses import dataclass

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.semantics.enums import TriggerEvent, VerificationStatus, Zone
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    AddCounterCost,
    AddCounterEffect,
    AddManaEffect,
    CardSemantics,
    ContinuousCostReduction,
    CreateTokenEffect,
    DealDamageEffect,
    DrawEffect,
    GainLifeEffect,
    LoseLifeEffect,
    ManaAmount,
    ManaCost,
    MoveToZoneEffect,
    RemoveCounterEffect,
    ReplacementExileInsteadOfGraveyard,
    ReplacementReduceM1M1Counters,
    ReturnToBattlefieldEffect,
    SacrificeCost,
    TapCost,
    TapEffect,
    TriggeredAbility,
    UntapEffect,
)
from mtg_loop_engine.state.game import GameState, Permanent


@dataclass
class ExecError:
    status: VerificationStatus
    message: str


class Executor:
    """Replay setup/loop actions. Combo player chooses favorably; opponents adversarial."""

    def __init__(self, semantics: dict[str, CardSemantics]):
        self.semantics = semantics  # keyed by oracle_id

    def cost_reduction(
        self, state: GameState, *, ability: ActivatedAbility | None = None
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

    def pay_mana(self, state: GameState, amount: ManaAmount) -> ExecError | None:
        # Colors exact, then any_color may cover remaining colored needs.
        # Generic paid from colorless, then colored, then any_color.
        pool = state.mana
        need = amount.model_copy(deep=True)

        for color in ("white", "blue", "black", "red", "green", "colorless"):
            n = getattr(need, color)
            if not n:
                continue
            avail = getattr(pool, color)
            use = min(avail, n)
            if use:
                setattr(pool, color, avail - use)
                setattr(need, color, n - use)
            remaining = getattr(need, color)
            if remaining:
                if pool.any_color < remaining:
                    return ExecError(
                        VerificationStatus.MANA_RESTRICTION, f"need {color} {n}"
                    )
                pool.any_color -= remaining
                setattr(need, color, 0)

        generic = need.generic
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

    def apply_effects(
        self,
        state: GameState,
        source: Permanent,
        effects: list,
        target_id: str | None,
        *,
        trigger_amount: int | None = None,
    ) -> ExecError | None:
        for effect in effects:
            err = self._apply_one(
                state, source, effect, target_id, trigger_amount=trigger_amount
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
    ) -> ExecError | None:
        if isinstance(effect, AddManaEffect):
            if effect.equal_to_source_power:
                qty = max(int(source.power or 0), 0)
                if qty > 0:
                    color = effect.equal_to_source_power
                    setattr(
                        state.mana,
                        color,
                        getattr(state.mana, color) + qty,
                    )
                    state.bump("mana", qty)
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
                setattr(
                    state.mana,
                    color,
                    getattr(state.mana, color) + getattr(effect.amount, color),
                )
            state.bump("mana", effect.amount.total())
            return None

        if isinstance(effect, UntapEffect):
            if effect.target == "all_creatures":
                n = 0
                for perm in state.permanents.values():
                    if perm.zone == Zone.BATTLEFIELD and perm.is_creature:
                        perm.tapped = False
                        n += 1
                if n:
                    state.bump("untap", n)
                return None
            tid = source.object_id if effect.target == "self" else target_id
            if not tid or tid not in state.permanents:
                return ExecError(VerificationStatus.ILLEGAL_TARGET, "untap target missing")
            state.permanents[tid].tapped = False
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
            for _ in range(effect.quantity):
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
            if effect.target == "self":
                tid = source.object_id
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
            qty = effect.quantity
            if effect.counter_type in {"m1m1", "-1/-1"}:
                qty = self.m1m1_put_quantity(state, qty)
            if qty > 0:
                p.counters[effect.counter_type] = (
                    p.counters.get(effect.counter_type, 0) + qty
                )
                state.bump("counter_added", qty)
                self._queue_triggers(
                    state, TriggerEvent.COUNTER_ADDED, p, amount=qty
                )
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
            state.bump("return_to_battlefield")
            self._on_etb(state, source)
            return None

        if isinstance(effect, DealDamageEffect):
            if effect.target == "opponent":
                state.life_opponent -= effect.amount
                self._queue_triggers(
                    state,
                    TriggerEvent.OPPONENT_LOSE_LIFE,
                    source,
                    amount=effect.amount,
                )
            state.bump("damage", effect.amount)
            if source.lifelink and effect.amount > 0:
                state.life_you += effect.amount
                state.bump("life_gain", effect.amount)
                self._queue_triggers(
                    state, TriggerEvent.GAIN_LIFE, source, amount=effect.amount
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
            state.bump("draw", effect.amount)
            return None

        if isinstance(effect, LoseLifeEffect):
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

        if isinstance(effect, MoveToZoneEffect):
            source.zone = effect.zone
            return None

        return ExecError(
            VerificationStatus.UNSUPPORTED_SEMANTICS, f"unknown effect {effect}"
        )

    def _on_etb(self, state: GameState, permanent: Permanent) -> None:
        state.bump("etb")
        self._queue_triggers(state, TriggerEvent.ENTER_BATTLEFIELD, permanent)

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
                if ab.filter == "token_creature" and not (
                    subject.is_token and subject.is_creature
                ):
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
        # CR 700.4: "dies" means moves from the battlefield to the graveyard.
        # Exile replacements (e.g. Rest in Peace) suppress death events and DIES triggers.
        # Sacrifice events still fire before this replacement is applied.
        if self.has_exile_on_death(state) and permanent.is_creature:
            permanent.zone = Zone.EXILE
            permanent.tapped = False
            return
        state.bump("death")
        self._queue_triggers(state, TriggerEvent.DIES, permanent)
        permanent.zone = Zone.GRAVEYARD
        permanent.tapped = False

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

    def _validate_tap_host(self, tap_perm: Permanent | None) -> ExecError | None:
        """Host for enchanted-creature {T}: exist, BF, controlled, creature, untapped, not sick."""
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
        if not tap_perm.is_creature:
            return ExecError(
                VerificationStatus.ILLEGAL_TARGET, "tap host not a creature"
            )
        if tap_perm.tapped:
            return ExecError(VerificationStatus.ILLEGAL_ACTION, "already tapped")
        # CR 302.6: creatures with summoning sickness cannot {T} (including mana abilities).
        if tap_perm.summoning_sick:
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
        if ab.once_per_turn and ab.ability_id in perm.once_per_turn_used:
            return ExecError(VerificationStatus.ONCE_PER_TURN_LIMIT, ab.ability_id)

        # Costs
        reduction, mana_floor = self.cost_reduction(state, ability=ab)
        for cost in ab.costs:
            if isinstance(cost, TapCost):
                tap_perm = perm
                if not cost.source_self:
                    if not step.target:
                        return ExecError(
                            VerificationStatus.ILLEGAL_ACTION, "tap cost needs host"
                        )
                    tap_perm = state.permanents.get(step.target)
                    err = self._validate_tap_host(tap_perm)
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
                err = self.pay_mana(state, need)
                if err:
                    return err
            elif isinstance(cost, AddCounterCost):
                qty = cost.quantity
                if cost.counter_type in {"m1m1", "-1/-1"}:
                    qty = self.m1m1_put_quantity(state, qty)
                if qty > 0:
                    key = cost.counter_type
                    perm.counters[key] = perm.counters.get(key, 0) + qty
                    state.bump("counter", qty)
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
        source = state.permanents[tr["source_id"]]
        ab = self.find_ability(source.oracle_id, tr["ability_id"])
        if not isinstance(ab, TriggeredAbility):
            return ExecError(VerificationStatus.ILLEGAL_ACTION, "bad trigger")
        return self.apply_effects(
            state,
            source,
            ab.effects,
            step.target or tr.get("subject_id"),
            trigger_amount=tr.get("amount"),
        )

    def run_step(self, state: GameState, step: ActionStep) -> ExecError | None:
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
        if op == "opponent_must_cooperate":
            return ExecError(
                VerificationStatus.OPPONENT_COOPERATION_REQUIRED,
                step.note or "opponent cooperation required",
            )
        return ExecError(VerificationStatus.UNSUPPORTED_RULE, f"unknown op {op}")

    def run_sequence(
        self, state: GameState, steps: list[ActionStep]
    ) -> ExecError | None:
        for step in steps:
            err = self.run_step(state, step)
            if err:
                return err
        return None
