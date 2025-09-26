from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config.settings import get_settings
from app.models.user import User

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v2/token")


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    sub: str


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    now = datetime.now(timezone.utc)
    exp_delta = timedelta(minutes=expires_minutes or settings.access_token_expire_minutes)
    exp_ts = int((now + exp_delta).timestamp())
    to_encode = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": exp_ts,
    }
    if settings.jwt_issuer:
        to_encode["iss"] = settings.jwt_issuer
    if settings.jwt_audience:
        to_encode["aud"] = settings.jwt_audience
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    try:
        options = {"verify_aud": bool(settings.jwt_audience)}
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            audience=settings.jwt_audience if settings.jwt_audience else None,
            issuer=settings.jwt_issuer if settings.jwt_issuer else None,
            options=options,
        )
        subject: Optional[str] = payload.get("sub")
        if not subject:
            raise JWTError("Missing subject")
        return TokenData(sub=subject)
    except JWTError as e:
        raise e


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username, User.is_active == True).first()  # noqa: E712


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        data = decode_token(token)
        return data.sub
    except JWTError:
        raise credentials_exception
