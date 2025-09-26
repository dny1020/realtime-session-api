from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from typing import Dict
from typing import Optional, Annotated
from pydantic import BaseModel, Field
import json
import uuid
from datetime import datetime

from app.database import get_db
from app.services.asterisk import get_asterisk_service, AsteriskService
from app.models.call import Call, CallStatus
from config.settings import get_settings
from app.auth.jwt import get_current_user
from app.instrumentation.metrics import (
    CALLS_LAUNCHED,
    CALLS_SUCCESS,
    CALLS_FAILED,
    ORIGINATE_LATENCY_SECONDS,
    CALLS_TOTAL,
    CALLS_LAUNCHED_V2,
    CALLS_SUCCESS_V2,
    CALLS_FAILED_V2,
    CALLS_V2,
)
import time

settings = get_settings()
router = APIRouter()


class CallRequest(BaseModel):
    """Call model for request"""
    context: Optional[str] = Field(None, description="Asterisk context", min_length=1, max_length=50)
    extension: Optional[str] = Field(None, description="Destination extension", min_length=1, max_length=50)
    priority: Optional[int] = Field(None, description="Call priority", ge=1, le=10)
    timeout: Optional[int] = Field(None, description="Timeout in milliseconds", gt=0, le=600000)
    caller_id: Optional[str] = Field(None, description="Caller ID of the call", min_length=1, max_length=50)
    variables: Optional[Dict[str, str]] = Field(None, description="Additional variables")


class CallResponse(BaseModel):
    """Call model for response"""
    success: bool
    call_id: str
    phone_number: str
    message: str
    channel: Optional[str] = None
    status: str
    created_at: datetime
    error: Optional[str] = None


class CallCreate(CallRequest):
    """Payload RESTful for creating a call (/calls)."""
    phone_number: str = Field(..., description="Phone number to call")


@router.post("/interaction/{number}", response_model=CallResponse)
async def originate_call(
    number: Annotated[str, Path(description="Phone number in E.164 or digits with optional +", min_length=7, max_length=20, pattern=r"^[+0-9]+$")],
    call_request: Optional[CallRequest] = None,
    asterisk_service: AsteriskService = Depends(get_asterisk_service),
    db: Optional[Session] = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Originate an outbound call to a specific number
    
    Args:
        number: Phone number to call
        call_request: Optional call parameters
        asterisk_service: Asterisk service
        db: Database session

    Returns:
        CallResponse: Information about the originated call
    """

    # Compute effective parameters with defaults
    effective_context = (call_request.context if call_request and call_request.context else settings.default_context)
    effective_extension = (call_request.extension if call_request and call_request.extension else settings.default_extension)
    effective_priority = (call_request.priority if call_request and call_request.priority is not None else settings.default_priority)
    effective_timeout = (call_request.timeout if call_request and call_request.timeout is not None else settings.default_timeout)
    effective_caller_id = (call_request.caller_id if call_request and call_request.caller_id else settings.default_caller_id)
    effective_vars = (call_request.variables if call_request and call_request.variables else None)

    # Generate unique ID for the call
    call_id = str(uuid.uuid4())
    
    try:
        # Register attempt at API level
        if settings.metrics_enabled:
            try:
                # legacy + v2
                CALLS_TOTAL.inc()
                CALLS_V2.inc()
            except Exception:
                pass

        # Create call record in database (if DB enabled)
        if db is not None and not settings.disable_db:
            db_call = Call(
                call_id=call_id,
                phone_number=number,
                status=CallStatus.PENDING,
                context=effective_context,
                extension=effective_extension,
                priority=effective_priority,
                timeout=effective_timeout,
                caller_id=effective_caller_id,
                call_metadata=json.dumps(effective_vars) if effective_vars else None,
            )
            db.add(db_call)
            db.commit()
            db.refresh(db_call)
        if settings.metrics_enabled:
            try:
                CALLS_LAUNCHED.inc()
                CALLS_LAUNCHED_V2.inc()
            except Exception:
                pass

        # Execute directly (no Celery/Workers in this version)
        start_t = time.perf_counter()
        asterisk_result = await asterisk_service.originate_call(
            phone_number=number,
            context=effective_context,
            extension=effective_extension,
            priority=effective_priority,
            timeout=effective_timeout,
            caller_id=effective_caller_id,
            variables=effective_vars,
        )
        if settings.metrics_enabled:
            try:
                ORIGINATE_LATENCY_SECONDS.observe(time.perf_counter() - start_t)
            except Exception:
                pass
        
        if asterisk_result["success"]:
            # Update record with Asterisk information
            if db is not None and not settings.disable_db:
                db_call.status = CallStatus.DIALING
                db_call.dialed_at = datetime.utcnow()
                db_call.channel = asterisk_result.get("channel")
                db.commit()
            if settings.metrics_enabled:
                try:
                    CALLS_SUCCESS.inc()
                    CALLS_SUCCESS_V2.inc()
                except Exception:
                    pass
            
            return CallResponse(
                success=True,
                call_id=call_id,
                phone_number=number,
                message="Call originated successfully",
                channel=asterisk_result.get("channel"),
                status=CallStatus.DIALING.value,
                created_at=datetime.utcnow()
            )
        else:
            # Update record with error
            if db is not None and not settings.disable_db:
                db_call.status = CallStatus.FAILED
                db_call.failure_reason = asterisk_result.get("error", "Unknown error")
                db_call.ended_at = datetime.utcnow()
                db.commit()
            if settings.metrics_enabled:
                try:
                    CALLS_FAILED.inc()
                    CALLS_FAILED_V2.inc()
                except Exception:
                    pass
            
            return CallResponse(
                success=False,
                call_id=call_id,
                phone_number=number,
                message="Error originating call",
                status=CallStatus.FAILED.value,
                created_at=datetime.utcnow(),
                error=asterisk_result.get("error")
            )
            
    except Exception as e:
        if db is not None and not settings.disable_db:
            db.rollback()
        if settings.metrics_enabled:
            try:
                CALLS_FAILED.inc()
                CALLS_FAILED_V2.inc()
            except Exception:
                pass
        
        # Try to update call record as failed if it was created
        try:
            if db is not None and not settings.disable_db and 'db_call' in locals():
                db_call.status = CallStatus.FAILED
                db_call.failure_reason = str(e)
                db_call.ended_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/interaction/{call_id}/status")
async def get_call_status(
    call_id: Annotated[str, Path(description="Call ID (UUID)", min_length=8, max_length=255)],
    db: Optional[Session] = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Get the current status of a call by its ID.
    
    Args:
        call_id: Call ID
        db: Database session

    Returns:
        Dict with call status information
    """
    
    # Search call in database
    if settings.disable_db or db is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="DB disabled")
    db_call = db.query(Call).filter(Call.call_id == call_id).first()
    
    if not db_call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    return {
        "call_id": db_call.call_id,
        "phone_number": db_call.phone_number,
        "status": db_call.status.value,
        "channel": db_call.channel,
        "context": db_call.context,
        "extension": db_call.extension,
        "caller_id": db_call.caller_id,
        "created_at": db_call.created_at,
        "dialed_at": db_call.dialed_at,
        "answered_at": db_call.answered_at,
        "ended_at": db_call.ended_at,
        "duration": db_call.duration,
        "failure_reason": db_call.failure_reason,
        "attempt_number": db_call.attempt_number,
        "is_active": db_call.is_active,
        "is_completed": db_call.is_completed
    }


# Alias : GET /api/v2/status/{call_id}
@router.get("/status/{call_id}")
async def get_call_status_alias(
    call_id: Annotated[str, Path(description="Call ID (UUID)", min_length=8, max_length=255)],
    db: Optional[Session] = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    return await get_call_status(call_id, db, current_user)


# RESTful aliases (resource calls)
@router.post("/calls", response_model=CallResponse, tags=["Calls"])
async def create_call(
    payload: CallCreate,
    asterisk_service: AsteriskService = Depends(get_asterisk_service),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Make a call as resource REST: POST /calls
    """
    return await originate_call(
        number=payload.phone_number,
        call_request=payload,
        asterisk_service=asterisk_service,
        db=db,
        current_user=current_user,
    )


@router.get("/calls/{call_id}", tags=["Calls"])
async def get_call(
    call_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Get call resource: GET /calls/{call_id}"""
    return await get_call_status(call_id, db, current_user)