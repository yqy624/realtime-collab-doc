from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import settings


def create_token(username: str, user_id: int) -> str:
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(milliseconds=settings.jwt_expiration)
    payload = {
        "sub": username,
        "userId": user_id,
        "iat": now,
        "exp": expiry,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def verify_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload
    except JWTError:
        return None
