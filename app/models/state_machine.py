"""
Call State Machine Model

Defines the state machine rules and transitions for call lifecycle management.
This module provides the data model for state transitions, separate from the
service-level state machine validator.
"""
from typing import Dict, Set, List, Optional
from enum import Enum

from app.models import CallStatus


class StateTransitionRule:
    """Represents a single state transition rule"""
    
    def __init__(
        self,
        from_state: CallStatus,
        to_state: CallStatus,
        description: Optional[str] = None,
        can_retry: bool = False
    ):
        self.from_state = from_state
        self.to_state = to_state
        self.description = description
        self.can_retry = can_retry
    
    def __repr__(self):
        return f"<StateTransitionRule({self.from_state.value} → {self.to_state.value})>"


class CallStateGraph:
    """
    Defines the complete call state transition graph.
    
    This class encapsulates the business rules for valid call state transitions,
    providing a clear definition of the call lifecycle state machine.
    """
    
    # Define all valid state transitions with descriptions
    TRANSITIONS: List[StateTransitionRule] = [
        # From PENDING
        StateTransitionRule(
            CallStatus.PENDING,
            CallStatus.DIALING,
            "Call origination initiated via ARI"
        ),
        StateTransitionRule(
            CallStatus.PENDING,
            CallStatus.FAILED,
            "Call failed before dialing (e.g., invalid parameters)"
        ),
        
        # From DIALING
        StateTransitionRule(
            CallStatus.DIALING,
            CallStatus.RINGING,
            "Remote party is ringing"
        ),
        StateTransitionRule(
            CallStatus.DIALING,
            CallStatus.ANSWERED,
            "Call answered immediately (some providers skip RINGING)"
        ),
        StateTransitionRule(
            CallStatus.DIALING,
            CallStatus.BUSY,
            "Remote party is busy"
        ),
        StateTransitionRule(
            CallStatus.DIALING,
            CallStatus.NO_ANSWER,
            "No answer from remote party"
        ),
        StateTransitionRule(
            CallStatus.DIALING,
            CallStatus.FAILED,
            "Call failed during dialing"
        ),
        
        # From RINGING
        StateTransitionRule(
            CallStatus.RINGING,
            CallStatus.ANSWERED,
            "Remote party answered the call"
        ),
        StateTransitionRule(
            CallStatus.RINGING,
            CallStatus.NO_ANSWER,
            "Ringing timeout - no answer"
        ),
        StateTransitionRule(
            CallStatus.RINGING,
            CallStatus.BUSY,
            "Line became busy while ringing"
        ),
        StateTransitionRule(
            CallStatus.RINGING,
            CallStatus.FAILED,
            "Call failed while ringing"
        ),
        
        # From ANSWERED
        StateTransitionRule(
            CallStatus.ANSWERED,
            CallStatus.COMPLETED,
            "Call completed successfully and hung up"
        ),
        StateTransitionRule(
            CallStatus.ANSWERED,
            CallStatus.FAILED,
            "Call failed while in progress"
        ),
    ]
    
    # Pre-computed lookup maps for performance
    _transition_map: Optional[Dict[CallStatus, Set[CallStatus]]] = None
    _transition_rules: Optional[Dict[tuple, StateTransitionRule]] = None
    
    @classmethod
    def _build_maps(cls):
        """Build internal lookup maps for fast queries"""
        if cls._transition_map is None:
            cls._transition_map = {}
            cls._transition_rules = {}
            
            for rule in cls.TRANSITIONS:
                # Build transition map
                if rule.from_state not in cls._transition_map:
                    cls._transition_map[rule.from_state] = set()
                cls._transition_map[rule.from_state].add(rule.to_state)
                
                # Build rule lookup
                key = (rule.from_state, rule.to_state)
                cls._transition_rules[key] = rule
            
            # Add empty sets for terminal states
            for status in CallStatus:
                if status not in cls._transition_map:
                    cls._transition_map[status] = set()
    
    @classmethod
    def get_valid_transitions(cls, from_state: CallStatus) -> Set[CallStatus]:
        """Get all valid target states from the given state"""
        cls._build_maps()
        return cls._transition_map.get(from_state, set()).copy()
    
    @classmethod
    def is_valid_transition(cls, from_state: CallStatus, to_state: CallStatus) -> bool:
        """Check if a transition is valid"""
        if from_state == to_state:
            return True  # Idempotent transitions are always valid
        cls._build_maps()
        return to_state in cls._transition_map.get(from_state, set())
    
    @classmethod
    def get_transition_rule(
        cls,
        from_state: CallStatus,
        to_state: CallStatus
    ) -> Optional[StateTransitionRule]:
        """Get the rule for a specific transition"""
        cls._build_maps()
        return cls._transition_rules.get((from_state, to_state))
    
    @classmethod
    def is_terminal_state(cls, state: CallStatus) -> bool:
        """Check if a state is terminal (has no outgoing transitions)"""
        cls._build_maps()
        return len(cls._transition_map.get(state, set())) == 0
    
    @classmethod
    def get_terminal_states(cls) -> Set[CallStatus]:
        """Get all terminal states"""
        cls._build_maps()
        return {
            state for state in CallStatus
            if len(cls._transition_map.get(state, set())) == 0
        }
    
    @classmethod
    def get_all_states(cls) -> Set[CallStatus]:
        """Get all call states"""
        return set(CallStatus)
    
    @classmethod
    def can_reach_state(
        cls,
        from_state: CallStatus,
        target_state: CallStatus,
        max_depth: int = 10
    ) -> bool:
        """
        Check if target_state is reachable from from_state.
        Uses breadth-first search.
        """
        if from_state == target_state:
            return True
        
        cls._build_maps()
        visited = {from_state}
        queue = [(from_state, 0)]
        
        while queue:
            current, depth = queue.pop(0)
            
            if depth >= max_depth:
                continue
            
            for next_state in cls._transition_map.get(current, set()):
                if next_state == target_state:
                    return True
                
                if next_state not in visited:
                    visited.add(next_state)
                    queue.append((next_state, depth + 1))
        
        return False
    
    @classmethod
    def describe_transition(cls, from_state: CallStatus, to_state: CallStatus) -> str:
        """Get human-readable description of a transition"""
        rule = cls.get_transition_rule(from_state, to_state)
        if rule and rule.description:
            return rule.description
        return f"Transition from {from_state.value} to {to_state.value}"
    
    @classmethod
    def validate_state_machine(cls) -> List[str]:
        """
        Validate the state machine configuration.
        Returns list of validation errors (empty if valid).
        """
        errors = []
        cls._build_maps()
        
        # Check that all states are represented
        all_states = set(CallStatus)
        states_in_graph = set(cls._transition_map.keys())
        missing_states = all_states - states_in_graph
        
        # Missing states are OK if they're terminal states
        for state in missing_states:
            if not cls.is_terminal_state(state):
                errors.append(f"Non-terminal state {state.value} has no outgoing transitions")
        
        # Check for unreachable states (except PENDING which is the start state)
        for state in CallStatus:
            if state == CallStatus.PENDING:
                continue
            if not cls.can_reach_state(CallStatus.PENDING, state):
                errors.append(f"State {state.value} is unreachable from PENDING")
        
        return errors


# Terminal states that represent end of call lifecycle
TERMINAL_STATES = {
    CallStatus.COMPLETED,
    CallStatus.BUSY,
    CallStatus.NO_ANSWER,
    CallStatus.FAILED,
}

# Active states where call is in progress
ACTIVE_STATES = {
    CallStatus.PENDING,
    CallStatus.DIALING,
    CallStatus.RINGING,
    CallStatus.ANSWERED,
}


def get_state_category(state: CallStatus) -> str:
    """
    Categorize a call state.
    
    Returns:
        "active" if call is in progress
        "terminal" if call has ended
    """
    if state in TERMINAL_STATES:
        return "terminal"
    elif state in ACTIVE_STATES:
        return "active"
    else:
        return "unknown"


def is_successful_completion(state: CallStatus) -> bool:
    """Check if a terminal state represents successful call completion"""
    return state in {CallStatus.COMPLETED, CallStatus.ANSWERED}


def is_failed_completion(state: CallStatus) -> bool:
    """Check if a terminal state represents failed call"""
    return state in {CallStatus.BUSY, CallStatus.NO_ANSWER, CallStatus.FAILED}
