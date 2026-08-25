"""Compatibility shim: Oracle gold APIs + physics card IR re-exports.

Oracle positives: ``oracle_cases.all_gold_core``.
Oracle hard negatives: ``hard_negatives.hard_negatives``.
Physics suite + card constants: ``corpus.physics_fixtures.synthetic_cases``.

Prefer importing Oracle APIs from ``mtg_loop_engine.corpus`` and physics cards
from ``physics_fixtures`` in new code. This module keeps historical import paths
working for unit tests.
"""

from mtg_loop_engine.corpus.gold_core.hard_negatives import hard_negatives
from mtg_loop_engine.corpus.gold_core.oracle_cases import all_gold_core
from mtg_loop_engine.corpus.physics_fixtures.synthetic_cases import (
    ASHNOD,
    BASALT,
    BASALT_EXPENSIVE,
    BLINKER,
    BLOOD_ARTIST,
    COOP_CARD,
    DRAMATIC,
    ETB_PING,
    GRAVECRAWLER,
    INTRUDER_ALARM,
    ONCE_TAPPER,
    PHOENIX,
    PHYREXIAN_ALTAR,
    REST_IN_PEACE,
    SAC_OUTLET,
    SCALED_GUN,
    SKELETON,
    SYNTHETIC_COST_REDUCER,
    SYNTHETIC_PUT_COUNTER,
    TOKEN_TAPPER,
    UNSUPPORTED_SCEPTER,
    _refs,
    gold_core_positives,
    gold_core_positives_fixed,
    gold_extended_catalog,
    physics_all_positives,
    physics_hard_negatives,
)

__all__ = [
    "ASHNOD",
    "BASALT",
    "BASALT_EXPENSIVE",
    "BLINKER",
    "BLOOD_ARTIST",
    "COOP_CARD",
    "DRAMATIC",
    "ETB_PING",
    "GRAVECRAWLER",
    "INTRUDER_ALARM",
    "ONCE_TAPPER",
    "PHOENIX",
    "PHYREXIAN_ALTAR",
    "REST_IN_PEACE",
    "SAC_OUTLET",
    "SCALED_GUN",
    "SKELETON",
    "SYNTHETIC_COST_REDUCER",
    "SYNTHETIC_PUT_COUNTER",
    "TOKEN_TAPPER",
    "UNSUPPORTED_SCEPTER",
    "_refs",
    "all_gold_core",
    "gold_core_positives",
    "gold_core_positives_fixed",
    "gold_extended_catalog",
    "hard_negatives",
    "physics_all_positives",
    "physics_hard_negatives",
]
