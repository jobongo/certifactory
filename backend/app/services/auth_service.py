from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)
    def verify_password(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)
    def create_access_token(self, user_id: str, role: str, expire_minutes: int | None = None) -> str:
        minutes = expire_minutes or settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        payload = {"sub": user_id, "role": role, "exp": expire, "type": "access"}
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    def create_refresh_token(self, user_id: str, role: str, expire_days: int | None = None) -> str:
        days = expire_days or settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        expire = datetime.now(timezone.utc) + timedelta(days=days)
        payload = {"sub": user_id, "role": role, "exp": expire, "type": "refresh"}
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    def decode_token(self, token: str) -> dict | None:
        try:
            return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        except JWTError:
            return None
