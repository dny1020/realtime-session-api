from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import uuid
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel
from loguru import logger

from config.settings import get_settings

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    sub: str
    jti: str  # JWT ID for blacklisting


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def create_access_token(
    subject: str, 
    expires_minutes: Optional[int] = None,
    jti: Optional[str] = None
) -> Tuple[str, str]:
    """
    Create JWT access token with unique JTI
    
    Returns:
        (token, jti): Token string and JWT ID for blacklisting
    """
    now = datetime.now(timezone.utc)
    exp_delta = timedelta(minutes=expires_minutes or settings.access_token_expire_minutes)
    
    # Generate unique JWT ID if not provided
    if not jti:
        jti = str(uuid.uuid4())
    
    to_encode = {
        "sub": subject,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int((now + exp_delta).timestamp()),
        "type": "access"
    }
    
    if settings.jwt_issuer:
        to_encode["iss"] = settings.jwt_issuer
    if settings.jwt_audience:
        to_encode["aud"] = settings.jwt_audience
    
    token = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return token, jti


def create_refresh_token(subject: str) -> Tuple[str, str, int]:
    """
    Create JWT refresh token
    
    Returns:
        (token, jti, exp): Token string, JWT ID, and expiration timestamp
    """
    now = datetime.now(timezone.utc)
    exp_delta = timedelta(days=settings.refresh_token_expire_days)
    exp_time = now + exp_delta
    
    jti = str(uuid.uuid4())
    
    to_encode = {
        "sub": subject,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(exp_time.timestamp()),
        "type": "refresh"
    }
    
    if settings.jwt_issuer:
        to_encode["iss"] = settings.jwt_issuer
    if settings.jwt_audience:
        to_encode["aud"] = settings.jwt_audience
    
    token = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return token, jti, int(exp_time.timestamp())


def create_token_pair(subject: str) -> TokenPair:
    """
    Create access and refresh token pair
    
    Returns:
        TokenPair with both tokens
    """
    access_token, _ = create_access_token(subject)
    refresh_token, _, _ = create_refresh_token(subject)
    
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60
    )


def decode_token(token: str, token_type: str = "access") -> TokenData:
    """
    Decode and validate JWT token
    
    Args:
        token: JWT token string
        token_type: Expected token type ("access" or "refresh")
        
    Returns:
        TokenData with subject and JTI
        
    Raises:
        JWTError: If token is invalid or wrong type
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            audience=settings.jwt_audience or None,
            issuer=settings.jwt_issuer or None,
            options={"verify_aud": bool(settings.jwt_audience)},
        )
        
        subject = payload.get("sub")
        jti = payload.get("jti")
        typ = payload.get("type")
        
        if not subject:
            raise JWTError("Missing subject")
        if not jti:
            raise JWTError("Missing JWT ID")
        if typ != token_type:
            raise JWTError(f"Invalid token type: expected {token_type}, got {typ}")
        
        return TokenData(sub=subject, jti=jti)
        
    except JWTError as e:
        logger.warning(f"Token decode error: {e}")
        raise e


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """
    Get current user from JWT token with blacklist check
    
    Dependency for protected endpoints
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode token
        data = decode_token(token, token_type="access")
        
        # Check if token is blacklisted (if Redis is available)
        try:
            from app.services.redis_service import get_redis_service
            redis = await get_redis_service()
            
            if await redis.is_token_blacklisted(data.jti):
                logger.warning(
                    "Blacklisted token used",
                    extra={"jti": data.jti, "subject": data.sub}
                )
                raise credentials_exception
        except Exception as e:
            # If Redis check fails, log but don't block (fail open for availability)
            logger.error(f"Failed to check token blacklist: {e}")
        
        return data.sub
        
    except JWTError as e:
        logger.warning(f"Authentication failed: {e}")
        raise credentials_exception


async def revoke_token(token: str) -> bool:
    """
    Revoke a JWT token by adding it to blacklist
    
    Args:
        token: JWT token to revoke
        
    Returns:
        True if successfully blacklisted
    """
    try:
        # Decode to get JTI and expiration
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"verify_exp": False}  # Don't fail on expired tokens
        )
        
        jti = payload.get("jti")
        exp = payload.get("exp")
        
        if not jti or not exp:
            logger.warning("Cannot revoke token: missing JTI or exp")
            return False
        
        # Add to blacklist
        from app.services.redis_service import get_redis_service
        redis = await get_redis_service()
        
        success = await redis.blacklist_token(jti, exp)
        
        if success:
            logger.info(
                "Token revoked",
                extra={"jti": jti, "subject": payload.get("sub")}
            )
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to revoke token: {e}")
        return False


async def refresh_access_token(refresh_token: str) -> Optional[TokenPair]:
    """
    Create new access token from refresh token
    
    Args:
        refresh_token: Valid refresh token
        
    Returns:
        New TokenPair or None if refresh token is invalid
    """
    try:
        # Decode refresh token
        data = decode_token(refresh_token, token_type="refresh")
        
        # Check if refresh token is blacklisted
        from app.services.redis_service import get_redis_service
        redis = await get_redis_service()
        
        if await redis.is_token_blacklisted(data.jti):
            logger.warning(
                "Blacklisted refresh token used",
                extra={"jti": data.jti, "subject": data.sub}
            )
            return None
        
        # Create new token pair
        new_tokens = create_token_pair(data.sub)
        
        # Optionally revoke old refresh token (rotation)
        await redis.blacklist_token(
            data.jti,
            jwt.decode(
                refresh_token,
                settings.secret_key,
                algorithms=[settings.algorithm],
                options={"verify_exp": False}
            )["exp"]
        )
        
        logger.info(
            "Access token refreshed",
            extra={"subject": data.sub, "old_jti": data.jti}
        )
        
        return new_tokens
        
    except JWTError as e:
        logger.warning(f"Failed to refresh token: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error refreshing token: {e}")
        return None
