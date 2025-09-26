from sqlalchemy.orm import declarative_base
import enum

# Base for all ORM models
Base = declarative_base()


class CallStatus(enum.Enum):
    PENDING = "pending"
    DIALING = "dialing"
    RINGING = "ringing"
    ANSWERED = "answered"
    BUSY = "busy"
    NO_ANSWER = "no_answer"
    FAILED = "failed"
    COMPLETED = "completed"


# Import models to register them with Base.metadata
# These imports must be at the end to avoid circular dependencies
from .call import Call  # noqa: E402,F401
from .user import User  # noqa: E402,F401