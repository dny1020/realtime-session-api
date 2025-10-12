from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token, verify_password
from app.database import get_db
from app.models.user import User
from app.services.metrics import track_auth_attempt

router = APIRouter()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/token", response_model=TokenResponse)
async def issue_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Issue JWT access token"""
    if not form_data.username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username required")

    if not db:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database disabled")

    user = db.query(User).filter(
        User.username == form_data.username,
        User.is_active == True
    ).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        track_auth_attempt(success=False)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    track_auth_attempt(success=True)
    return TokenResponse(access_token=create_access_token(subject=user.username))
