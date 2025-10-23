from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Annotated
from pydantic import BaseModel, Field
import json
import uuid
import asyncio
from datetime import datetime

from app.database import get_db
from app.services.asterisk import get_asterisk_service, AsteriskService
from app.models.call import Call, CallStatus
from config.settings import get_settings
from app.auth.jwt import get_current_user
from app.services.metrics import (
    track_call_originated,
    call_origination_latency,
)
from app.validators import (
    PhoneNumberValidator,
    AsteriskContextValidator,
    AsteriskExtensionValidator,
    CallerIDValidator,
)

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


class CallStatusResponse(BaseModel):
    """Response model for call status"""
    call_id: str
    phone_number: str
    status: str
    channel: Optional[str] = None
    context: str
    extension: str
    caller_id: str
    created_at: datetime
    dialed_at: Optional[datetime] = None
    answered_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration: Optional[int] = None
    failure_reason: Optional[str] = None
    attempt_number: int
    is_active: bool
    is_completed: bool


def _get_effective_params(call_request: Optional[CallRequest]) -> Dict[str, any]:
    """Extract effective parameters with fallback to defaults"""
    return {
        'context': call_request.context if call_request and call_request.context else settings.default_context,
        'extension': call_request.extension if call_request and call_request.extension else settings.default_extension,
        'priority': call_request.priority if call_request and call_request.priority is not None else settings.default_priority,
        'timeout': call_request.timeout if call_request and call_request.timeout is not None else settings.default_timeout,
        'caller_id': call_request.caller_id if call_request and call_request.caller_id else settings.default_caller_id,
        'variables': call_request.variables if call_request and call_request.variables else None,
    }


@router.post("/interaction/{number}", response_model=CallResponse)
async def originate_call(
    number: str,  # Remove Annotated - validation now done by validator
    call_request: Optional[CallRequest] = None,
    asterisk_service: AsteriskService = Depends(get_asterisk_service),
    db: Optional[Session] = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Originate an outbound call to a specific number"""
    
    # Validate and sanitize phone number
    try:
        validated_number = PhoneNumberValidator.validate(number)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid phone number: {str(e)}")
    
    params = _get_effective_params(call_request)
    
    # Validate Asterisk parameters
    try:
        params['context'] = AsteriskContextValidator.validate(params['context'])
        params['extension'] = AsteriskExtensionValidator.validate(params['extension'])
        params['caller_id'] = CallerIDValidator.sanitize(params['caller_id'])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")

    call_id = str(uuid.uuid4())
    db_call = None
    
    try:
        # Create call record in database (if enabled)
        if db is not None:
            db_call = Call(
                call_id=call_id,
                phone_number=validated_number,  # Use validated number
                status=CallStatus.PENDING,
                context=params['context'],
                extension=params['extension'],
                priority=params['priority'],
                timeout=params['timeout'],
                caller_id=params['caller_id'],
                call_metadata=json.dumps(params['variables']) if params['variables'] else None,
            )
            db.add(db_call)
            db.commit()
            db.refresh(db_call)

        # Originate call via Asterisk ARI with timing
        start_time = asyncio.get_event_loop().time()
        asterisk_result = await asterisk_service.originate_call(
            phone_number=validated_number,  # Use validated number
            context=params['context'],
            extension=params['extension'],
            priority=params['priority'],
            timeout=params['timeout'],
            caller_id=params['caller_id'],
            variables=params['variables'],
        )
        latency = asyncio.get_event_loop().time() - start_time
        call_origination_latency.observe(latency)
        
        if asterisk_result["success"]:
            # Update record with Asterisk channel info
            if db_call:
                db_call.status = CallStatus.DIALING
                db_call.dialed_at = datetime.utcnow()
                db_call.channel = asterisk_result.get("channel")
                db.commit()
            
            # Track successful origination
            track_call_originated(success=True)
            
            return CallResponse(
                success=True,
                call_id=call_id,
                phone_number=validated_number,  # Use validated number
                message="Call originated successfully",
                channel=asterisk_result.get("channel"),
                status=CallStatus.DIALING.value,
                created_at=datetime.utcnow()
            )
        else:
            # Update record with failure
            if db_call:
                db_call.status = CallStatus.FAILED
                db_call.failure_reason = asterisk_result.get("error", "Unknown error")
                db_call.ended_at = datetime.utcnow()
                db.commit()
            
            # Track failed origination
            track_call_originated(success=False)
            
            return CallResponse(
                success=False,
                call_id=call_id,
                phone_number=validated_number,  # Use validated number
                message="Error originating call",
                status=CallStatus.FAILED.value,
                created_at=datetime.utcnow(),
                error=asterisk_result.get("error")
            )
            
    except Exception as e:
        if db:
            db.rollback()
            # Try to mark call as failed
            if db_call:
                try:
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


@router.get("/interaction/{call_id}/status", response_model=CallStatusResponse)
@router.get("/status/{call_id}", response_model=CallStatusResponse)
@router.get("/calls/{call_id}", response_model=CallStatusResponse, tags=["Calls"])
async def get_call_status(
    call_id: Annotated[str, Field(description="Call ID (UUID)", min_length=8, max_length=255)],
    db: Optional[Session] = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Get the current status of a call by its ID"""
    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database disabled")
    
    db_call = db.query(Call).filter(Call.call_id == call_id).first()
    if not db_call:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found")
    
    return CallStatusResponse(
        call_id=db_call.call_id,
        phone_number=db_call.phone_number,
        status=db_call.status.value,
        channel=db_call.channel,
        context=db_call.context,
        extension=db_call.extension,
        caller_id=db_call.caller_id,
        created_at=db_call.created_at,
        dialed_at=db_call.dialed_at,
        answered_at=db_call.answered_at,
        ended_at=db_call.ended_at,
        duration=db_call.duration,
        failure_reason=db_call.failure_reason,
        attempt_number=db_call.attempt_number,
        is_active=db_call.is_active,
        is_completed=db_call.is_completed
    )


@router.post("/calls", response_model=CallResponse, tags=["Calls"])
async def create_call(
    payload: CallCreate,
    asterisk_service: AsteriskService = Depends(get_asterisk_service),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Create a new outbound call (RESTful endpoint)"""
    return await originate_call(
        number=payload.phone_number,
        call_request=payload,
        asterisk_service=asterisk_service,
        db=db,
        current_user=current_user,
    )