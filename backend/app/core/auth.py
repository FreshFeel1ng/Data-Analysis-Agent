import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Token decode failed: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌")


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    if token is None:
        logger.warning("No token provided in request")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供认证凭据")
    payload = decode_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        logger.warning("Token missing 'sub' claim")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭据")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        logger.warning(f"User not found: id={user_id}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    if not user.is_active:
        logger.warning(f"User disabled: id={user_id}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    return user
