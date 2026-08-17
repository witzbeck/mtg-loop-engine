"""Minimal game state for witness execution."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from mtg_loop_engine.semantics.enums import Zone
from mtg_loop_engine.semantics.ir import ManaAmount
from mtg_loop_engine.proofs.models import InitialStateSpec, PermanentSpec


@dataclass
class Permanent:
    object_id: str
    oracle_id: str
    name: str
    controller: str = "you"
    zone: Zone = Zone.BATTLEFIELD
    tapped: bool = False
    summoning_sick: bool = False
    counters: dict[str, int] = field(default_factory=dict)
    is_token: bool = False
    is_creature: bool = False
    is_artifact: bool = False
    power: int | None = None
    toughness: int | None = None
    once_per_turn_used: set[str] = field(default_factory=set)

    def copy(self) -> Permanent:
        return Permanent(
            object_id=self.object_id,
            oracle_id=self.oracle_id,
            name=self.name,
            controller=self.controller,
            zone=self.zone,
            tapped=self.tapped,
            summoning_sick=self.summoning_sick,
            counters=dict(self.counters),
            is_token=self.is_token,
            is_creature=self.is_creature,
            is_artifact=self.is_artifact,
            power=self.power,
            toughness=self.toughness,
            once_per_turn_used=set(self.once_per_turn_used),
        )


@dataclass
class GameState:
    permanents: dict[str, Permanent]
    mana: ManaAmount
    life_you: int = 40
    life_opponent: int = 40
    event_counters: dict[str, int] = field(default_factory=dict)
    pending_triggers: list[dict[str, Any]] = field(default_factory=list)
    _token_seq: int = 0

    @classmethod
    def from_spec(cls, spec: InitialStateSpec) -> GameState:
        permanents = {
            p.object_id: Permanent(
                object_id=p.object_id,
                oracle_id=p.oracle_id,
                name=p.name,
                controller=p.controller,
                zone=p.zone,
                tapped=p.tapped,
                summoning_sick=p.summoning_sick,
                counters=dict(p.counters),
                is_token=p.is_token,
                is_creature=p.is_creature,
                is_artifact=p.is_artifact,
                power=p.power,
                toughness=p.toughness,
            )
            for p in spec.permanents
        }
        return cls(
            permanents=permanents,
            mana=spec.mana.model_copy(deep=True),
            life_you=spec.life_you,
            life_opponent=spec.life_opponent,
            event_counters=dict(spec.event_counters),
        )

    def copy(self) -> GameState:
        return GameState(
            permanents={k: v.copy() for k, v in self.permanents.items()},
            mana=self.mana.model_copy(deep=True),
            life_you=self.life_you,
            life_opponent=self.life_opponent,
            event_counters=dict(self.event_counters),
            pending_triggers=deepcopy(self.pending_triggers),
            _token_seq=self._token_seq,
        )

    def bump(self, key: str, n: int = 1) -> None:
        self.event_counters[key] = self.event_counters.get(key, 0) + n

    def next_token_id(self) -> str:
        self._token_seq += 1
        return f"token-{self._token_seq}"

    def get_path(self, path: str) -> Any:
        """Resolve a LoopRelevantState path against this state."""
        parts = path.split(".")
        if not parts:
            raise KeyError(path)
        head = parts[0]
        if head == "mana":
            color = parts[1]
            return getattr(self.mana, color)
        if head == "events":
            return self.event_counters.get(parts[1], 0)
        if head == "life":
            who = parts[1]
            return self.life_you if who == "you" else self.life_opponent
        if head == "permanents":
            obj_id = parts[1]
            perm = self.permanents[obj_id]
            attr = parts[2]
            if attr == "zone":
                return perm.zone.value if isinstance(perm.zone, Zone) else perm.zone
            if attr == "tapped":
                return perm.tapped
            if attr == "counters":
                return perm.counters.get(parts[3], 0)
            if attr == "summoning_sick":
                return perm.summoning_sick
            raise KeyError(path)
        if head == "count":
            # count.battlefield.creature_tokens
            zone = Zone(parts[1])
            kind = parts[2]
            vals = [p for p in self.permanents.values() if p.zone == zone]
            if kind == "creature_tokens":
                return sum(1 for p in vals if p.is_token and p.is_creature)
            if kind == "creatures":
                return sum(1 for p in vals if p.is_creature)
            if kind == "artifacts":
                return sum(1 for p in vals if p.is_artifact)
            raise KeyError(path)
        raise KeyError(path)


def permanent_from_spec(spec: PermanentSpec) -> Permanent:
    return Permanent(
        object_id=spec.object_id,
        oracle_id=spec.oracle_id,
        name=spec.name,
        controller=spec.controller,
        zone=spec.zone,
        tapped=spec.tapped,
        summoning_sick=spec.summoning_sick,
        counters=dict(spec.counters),
        is_token=spec.is_token,
        is_creature=spec.is_creature,
        is_artifact=spec.is_artifact,
        power=spec.power,
        toughness=spec.toughness,
    )
