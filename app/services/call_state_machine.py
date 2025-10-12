"""  # noqa: E501
Call State Machine Validator

Enforces valid state transitions for call lifecycle.
Prevents invalid state jumps due to race conditions or out-of-order events.
"""
from typing import Dict, Set, Optional
from loguru import logger

from app.models import CallStatus

# Import metrics if available
try:
    from app.services.metrics import track_state_transition
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    track_state_transition = None


class CallStateMachine:
    """State machine for call lifecycle management"""
    
    # Define valid state transitions
    VALID_TRANSITIONS: Dict[CallStatus, Set[CallStatus]] = {
        CallStatus.PENDING: {
            CallStatus.DIALING,
            CallStatus.FAILED,
        },
        CallStatus.DIALING: {
            CallStatus.RINGING,
            CallStatus.BUSY,
            CallStatus.NO_ANSWER,
            CallStatus.FAILED,
            CallStatus.ANSWERED,  # Some providers skip RINGING
        },
        CallStatus.RINGING: {
            CallStatus.ANSWERED,
            CallStatus.NO_ANSWER,
            CallStatus.BUSY,
            CallStatus.FAILED,
        },
        CallStatus.ANSWERED: {
            CallStatus.COMPLETED,
            CallStatus.FAILED,
        },
        # Terminal states (no further transitions allowed)
        CallStatus.COMPLETED: set(),
        CallStatus.BUSY: set(),
        CallStatus.NO_ANSWER: set(),
        CallStatus.FAILED: set(),
    }
    
    # Terminal states that cannot transition further
    TERMINAL_STATES = {
        CallStatus.COMPLETED,
        CallStatus.BUSY,
        CallStatus.NO_ANSWER,
        CallStatus.FAILED,
    }
    
    @classmethod
    def is_valid_transition(
        cls,
        current_status: CallStatus,
        new_status: CallStatus
    ) -> bool:
        """Check if a state transition is valid"""
        # Same state is always valid (idempotent)
        if current_status == new_status:
            return True
        
        # Check if transition is in valid set
        valid_next_states = cls.VALID_TRANSITIONS.get(current_status, set())
        return new_status in valid_next_states
    
    @classmethod
    def is_terminal_state(cls, status: CallStatus) -> bool:
        """Check if a status is terminal (no further transitions)"""
        return status in cls.TERMINAL_STATES
    
    @classmethod
    def can_transition(
        cls,
        current_status: CallStatus,
        new_status: CallStatus,
        allow_terminal_override: bool = False
    ) -> tuple[bool, Optional[str]]:
        """
        Check if transition is allowed and return reason if not.
        
        Args:
            current_status: Current call status
            new_status: Desired new status
            allow_terminal_override: If True, allow transitions from terminal states
                                    (for administrative corrections)
        
        Returns:
            (is_valid, error_message)
        """
        # Same state is always valid
        if current_status == new_status:
            return True, None
        
        # Check if current state is terminal
        if cls.is_terminal_state(current_status) and not allow_terminal_override:
            return False, f"Cannot transition from terminal state {current_status.value}"
        
        # Check if transition is valid
        if not cls.is_valid_transition(current_status, new_status):
            valid_states = cls.VALID_TRANSITIONS.get(current_status, set())
            valid_names = [s.value for s in valid_states]
            return False, (
                f"Invalid transition: {current_status.value} → {new_status.value}. "
                f"Valid transitions: {valid_names or 'none'}"
            )
        
        return True, None
    
    @classmethod
    def get_valid_next_states(cls, current_status: CallStatus) -> Set[CallStatus]:
        """Get all valid next states for a given status"""
        return cls.VALID_TRANSITIONS.get(current_status, set()).copy()
    
    @classmethod
    def validate_and_log(
        cls,
        call_id: str,
        current_status: CallStatus,
        new_status: CallStatus,
        context: Optional[str] = None
    ) -> bool:
        """
        Validate transition and log the result.
        
        Returns:
            True if valid, False if invalid
        """
        is_valid, error_msg = cls.can_transition(current_status, new_status)
        
        # Track metrics if available
        if METRICS_AVAILABLE and track_state_transition:
            track_state_transition(
                from_state=current_status.value,
                to_state=new_status.value,
                success=is_valid
            )
        
        if is_valid:
            if current_status != new_status:  # Don't log idempotent transitions
                logger.info(
                    f"Call state transition: {current_status.value} → {new_status.value}",
                    extra={
                        "call_id": call_id,
                        "from_state": current_status.value,
                        "to_state": new_status.value,
                        "context": context,
                    }
                )
        else:
            logger.warning(
                f"Rejected invalid state transition: {error_msg}",
                extra={
                    "call_id": call_id,
                    "from_state": current_status.value,
                    "attempted_state": new_status.value,
                    "context": context,
                    "reason": error_msg,
                }
            )
        
        return is_valid


# Convenience function for common use case
def transition_call_status(
    call,
    new_status: CallStatus,
    context: Optional[str] = None,
    force: bool = False
) -> bool:
    """
    Attempt to transition a call to a new status.
    
    Args:
        call: Call model instance
        new_status: Desired new status
        context: Optional context for logging (e.g., "ARI event: ChannelDestroyed")
        force: If True, allow transitions from terminal states
    
    Returns:
        True if transition was applied, False if rejected
    """
    machine = CallStateMachine()
    
    is_valid, error_msg = machine.can_transition(
        call.status,
        new_status,
        allow_terminal_override=force
    )
    
    if is_valid:
        if call.status != new_status:
            logger.info(
                f"Call state transition: {call.status.value} → {new_status.value}",
                extra={
                    "call_id": call.call_id,
                    "from_state": call.status.value,
                    "to_state": new_status.value,
                    "context": context,
                }
            )
        call.status = new_status
        return True
    else:
        logger.warning(
            f"Rejected invalid state transition: {error_msg}",
            extra={
                "call_id": call.call_id,
                "from_state": call.status.value,
                "attempted_state": new_status.value,
                "context": context,
                "reason": error_msg,
            }
        )
        return False
