"""Rules-aware action executor for witness replay."""

from __future__ import annotations

from dataclasses import dataclass

from mtg_loop_engine.proofs.models import ActionStep
from mtg_loop_engine.semantics.enums import TriggerEvent, VerificationStatus, Zone
from mtg_loop_engine.semantics.ir import (
    ActivatedAbility,
    AddCounterEffect,
    AddManaEffect,
    CardSemantics,
    ContinuousCostReduction,
    CreateTokenEffect,
    DealDamageEffect,
    GainLifeEffect,
    LoseLifeEffect,
    ManaAmount,
    ManaCost,
    MoveToZoneEffect,
    RemoveCounterEffect,
    ReplacementExileInsteadOfGraveyard,
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

    def cost_reduction(self, state: GameState) -> int:
        reduction = 0
        for perm in state.permanents.values():
            if perm.zone != Zone.BATTLEFIELD or perm.controller != "you":
                continue
            card = self.semantics.get(perm.oracle_id)
            if not card:
                continue
            for ab in card.abilities:
                if isinstance(ab, ContinuousCostReduction):
                    reduction += ab.reduce_generic
        return reduction

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

        def take(attr: str, n: int) -> bool:
            avail = getattr(pool, attr)
            if avail < n:
                return False
            setattr(pool, attr, avail - n)
            return True

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
    ) -> ExecError | None:
        for effect in effects:
            err = self._apply_one(state, source, effect, target_id)
            if err:
                return err
        return None

    def _apply_one(
        self, state: GameState, source: Permanent, effect, target_id: str | None
    ) -> ExecError | None:
        if isinstance(effect, AddManaEffect):
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
            return None

        if isinstance(effect, AddCounterEffect):
            tid = source.object_id if effect.target == "self" else target_id
            if not tid or tid not in state.permanents:
                return ExecError(VerificationStatus.ILLEGAL_TARGET, "counter target")
            p = state.permanents[tid]
            p.counters[effect.counter_type] = (
                p.counters.get(effect.counter_type, 0) + effect.quantity
            )
            state.bump("counter_added", effect.quantity)
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
            state.bump("damage", effect.amount)
            return None

        if isinstance(effect, GainLifeEffect):
            state.life_you += effect.amount
            state.bump("life_gain", effect.amount)
            return None

        if isinstance(effect, LoseLifeEffect):
            if effect.who == "opponent":
                state.life_opponent -= effect.amount
            else:
                state.life_you -= effect.amount
            state.bump("life_loss", effect.amount)
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
        self, state: GameState, event: TriggerEvent, subject: Permanent
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
                state.pending_triggers.append(
                    {
                        "source_id": perm.object_id,
                        "ability_id": ab.ability_id,
                        "subject_id": subject.object_id,
                    }
                )

    def die(self, state: GameState, permanent: Permanent) -> None:
        state.bump("death")
        self._queue_triggers(state, TriggerEvent.DIES, permanent)
        if self.has_exile_on_death(state) and permanent.is_creature:
            permanent.zone = Zone.EXILE
        else:
            permanent.zone = Zone.GRAVEYARD
        permanent.tapped = False

    def sacrifice(self, state: GameState, permanent: Permanent) -> None:
        state.bump("sacrifice")
        self._queue_triggers(state, TriggerEvent.SACRIFICED, permanent)
        self.die(state, permanent)

    def activate(
        self, state: GameState, step: ActionStep
    ) -> ExecError | None:
        if not step.actor or not step.ability_id:
            return ExecError(VerificationStatus.ILLEGAL_ACTION, "activate needs actor/ability")
        perm = state.permanents.get(step.actor)
        if not perm:
            return ExecError(VerificationStatus.ILLEGAL_ACTION, "actor missing")
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
        if ab.once_per_turn and ab.ability_id in perm.once_per_turn_used:
            return ExecError(VerificationStatus.ONCE_PER_TURN_LIMIT, ab.ability_id)

        # Costs
        reduction = self.cost_reduction(state)
        for cost in ab.costs:
            if isinstance(cost, TapCost):
                if perm.tapped:
                    return ExecError(VerificationStatus.ILLEGAL_ACTION, "already tapped")
                if perm.is_creature and perm.summoning_sick and not ab.is_mana_ability:
                    # mana abilities also care about sickness for tap - simplify: block tap if sick
                    return ExecError(VerificationStatus.TIMING_VIOLATION, "summoning sick")
                perm.tapped = True
            elif isinstance(cost, ManaCost):
                need = cost.amount.model_copy(deep=True)
                reduced = min(reduction, need.generic)
                need.generic -= reduced
                reduction -= reduced
                err = self.pay_mana(state, need)
                if err:
                    return err
            elif isinstance(cost, SacrificeCost):
                if cost.selector == "self":
                    if perm.zone != Zone.BATTLEFIELD:
                        return ExecError(
                            VerificationStatus.RESOURCE_DEFICIT, "self not on battlefield"
                        )
                    self.sacrifice(state, perm)
                else:
                    fodder_id = step.target
                    if not fodder_id:
                        fodder_id = self._pick_fodder(state, cost.selector)
                    if not fodder_id:
                        return ExecError(
                            VerificationStatus.RESOURCE_DEFICIT, "no sacrifice fodder"
                        )
                    fodder = state.permanents[fodder_id]
                    if fodder.zone != Zone.BATTLEFIELD:
                        return ExecError(
                            VerificationStatus.RESOURCE_DEFICIT,
                            "sacrifice target not on battlefield",
                        )
                    self.sacrifice(state, fodder)

        err = self.apply_effects(state, perm, ab.effects, step.target)
        if err:
            return err
        if ab.once_per_turn:
            perm.once_per_turn_used.add(ab.ability_id)
        return None

    def _pick_fodder(self, state: GameState, selector: str) -> str | None:
        for p in state.permanents.values():
            if p.zone != Zone.BATTLEFIELD or p.controller != "you":
                continue
            if selector == "token_creature_controlled" and p.is_token and p.is_creature:
                return p.object_id
            if selector == "creature_controlled" and p.is_creature:
                # Prefer tokens / non-essential: tokens first
                if p.is_token:
                    return p.object_id
        for p in state.permanents.values():
            if (
                p.zone == Zone.BATTLEFIELD
                and p.controller == "you"
                and p.is_creature
                and selector == "creature_controlled"
            ):
                return p.object_id
        return None

    def resolve_trigger(self, state: GameState, step: ActionStep) -> ExecError | None:
        if not state.pending_triggers:
            return ExecError(VerificationStatus.ILLEGAL_ACTION, "no pending triggers")
        # Combo player orders favorably: pick matching ability_id/source if given.
        idx = 0
        if step.ability_id or step.actor:
            for i, tr in enumerate(state.pending_triggers):
                if step.ability_id and tr["ability_id"] != step.ability_id:
                    continue
                if step.actor and tr["source_id"] != step.actor:
                    continue
                idx = i
                break
        tr = state.pending_triggers.pop(idx)
        source = state.permanents[tr["source_id"]]
        ab = self.find_ability(source.oracle_id, tr["ability_id"])
        if not isinstance(ab, TriggeredAbility):
            return ExecError(VerificationStatus.ILLEGAL_ACTION, "bad trigger")
        return self.apply_effects(state, source, ab.effects, step.target or tr.get("subject_id"))

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
