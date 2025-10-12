from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum, Index, CheckConstraint
from sqlalchemy.sql import func

from . import Base, CallStatus


class Call(Base):
    __tablename__ = "calls"
    __table_args__ = (
        Index("ix_calls_created_at", "created_at"),
        Index("ix_calls_status_created", "status", "created_at"),
        CheckConstraint("attempt_number >= 1", name="ck_calls_attempt_number_ge_1"),
        CheckConstraint("timeout > 0", name="ck_calls_timeout_pos"),
        CheckConstraint(
            "char_length(phone_number) >= 7 AND char_length(phone_number) <= 20",
            name="ck_calls_phone_number_len",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(String(255), unique=True, index=True, nullable=False)
    
    # Call details
    phone_number = Column(String(20), nullable=False, index=True)
    caller_id = Column(String(50), default="Outbound Call", nullable=False)
    
    # Status and routing
    status = Column(SQLEnum(CallStatus), default=CallStatus.PENDING, nullable=False)
    context = Column(String(50), default="outbound-ivr", nullable=False)
    extension = Column(String(50), default="s", nullable=False)
    priority = Column(Integer, default=1, nullable=False)
    timeout = Column(Integer, default=30000, nullable=False)
    
    # Asterisk channel
    channel = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    dialed_at = Column(DateTime(timezone=True), nullable=True)
    answered_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Duration in seconds
    duration = Column(Integer, nullable=True)

    # Failure reason (if any)
    failure_reason = Column(String(255), nullable=True)

    # Call attempt number
    attempt_number = Column(Integer, default=1, nullable=False)
    
    # Metadata (JSON as text)
    call_metadata = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Call(id={self.id}, phone_number='{self.phone_number}', status='{self.status}')>"
    
    @property
    def is_active(self):
        """Return True if the call is in progress"""
        return self.status in [CallStatus.PENDING, CallStatus.DIALING, CallStatus.RINGING]
    
    @property
    def is_completed(self):
        """Return True if the call has ended"""
        return self.status in [CallStatus.ANSWERED, CallStatus.BUSY, CallStatus.NO_ANSWER, 
                              CallStatus.FAILED, CallStatus.COMPLETED]