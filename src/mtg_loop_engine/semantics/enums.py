"""Shared enumerations for semantics, verification, and proofs."""

from __future__ import annotations

from enum import StrEnum


class Zone(StrEnum):
    BATTLEFIELD = "battlefield"
    GRAVEYARD = "graveyard"
    HAND = "hand"
    EXILE = "exile"
    LIBRARY = "library"
    STACK = "stack"
    COMMAND = "command"


class ComparisonOp(StrEnum):
    EXACT = "exact"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"


class SemanticCoverage(StrEnum):
    COMPLETE = "complete"
    PARTIAL_IRRELEVANT_TO_PROOF = "partial_irrelevant_to_proof"
    PARTIAL_RELEVANT_TO_PROOF = "partial_relevant_to_proof"


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    NOT_A_LOOP = "not_a_loop"
    RESOURCE_DEFICIT = "resource_deficit"
    STATE_NOT_RECURRENT = "state_not_recurrent"
    ILLEGAL_ACTION = "illegal_action"
    ILLEGAL_TARGET = "illegal_target"
    TIMING_VIOLATION = "timing_violation"
    MANA_RESTRICTION = "mana_restriction"
    FINITE_RESOURCE_CONSUMED = "finite_resource_consumed"
    ONCE_PER_TURN_LIMIT = "once_per_turn_limit"
    OPPONENT_COOPERATION_REQUIRED = "opponent_cooperation_required"
    EXTERNAL_FUNCTIONAL_PIECE_REQUIRED = "external_functional_piece_required"
    UNSUPPORTED_SEMANTICS = "unsupported_semantics"
    UNSUPPORTED_RULE = "unsupported_rule"
    NONDETERMINISTIC = "nondeterministic"
    INDETERMINATE = "indeterminate"


class ProofKind(StrEnum):
    VALID = "valid"
    NORMALIZED = "normalized"


class LoopType(StrEnum):
    ARBITRARY_REPEATABLE = "arbitrary_repeatable"
    RESOURCE_BOUNDED = "resource_bounded"
    STATE_BOUNDED = "state_bounded"
    FORCED_LOOP = "forced_loop"
    NONPRODUCTIVE_LOOP = "nonproductive_loop"
    NOT_A_LOOP = "not_a_loop"


class OutputType(StrEnum):
    MANA = "mana"
    TOKEN = "token"
    COUNTER = "counter"
    LIFE_GAIN = "life_gain"
    LIFE_LOSS = "life_loss"
    DAMAGE = "damage"
    DRAW = "draw"
    MILL = "mill"
    ETB = "etb"
    LTB = "ltb"
    DEATH = "death"
    SACRIFICE = "sacrifice"
    CAST = "cast"
    SPELL_COPY = "spell_copy"
    UNTAP = "untap"
    POWER = "power"
    TOUGHNESS = "toughness"
    OTHER = "other"


class Consequence(StrEnum):
    ACCUMULATES = "accumulates"
    REPEATABLE_EVENT = "repeatable_event"
    LETHAL = "lethal"
    MILLS_LIBRARY = "mills_library"
    DRAWS_LIBRARY = "draws_library"
    WIN_CONDITION = "win_condition"
    LOCK = "lock"
    OTHER = "other"


class TriggerEvent(StrEnum):
    ENTER_BATTLEFIELD = "enter_battlefield"
    LEAVE_BATTLEFIELD = "leave_battlefield"
    DIES = "dies"
    SACRIFICED = "sacrificed"
    TAP = "tap"
    UNTAP = "untap"
    COUNTER_ADDED = "counter_added"


class ChoiceController(StrEnum):
    COMBO_PLAYER = "combo_player"
    OPPONENT = "opponent"
