import bcrypt

from app.models.user import User
from app.utils.jwt import create_token


class AuthService:
    def __init__(self, db):
        self.db = db

    def register(self, username: str, password: str, email: str | None = None) -> dict:
        if self.db.query(User).filter(User.username == username).first():
            raise ValueError("用户名已存在")

        email = email or f"{username}@example.com"
        if self.db.query(User).filter(User.email == email).first():
            raise ValueError("邮箱已存在")

        pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        user = User(
            username=username,
            email=email,
            password_hash=pw_hash,
            avatar_url=f"https://ui-avatars.com/api/?name={username}&background=random",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return self._build_response(user)

    def login(self, username: str, password: str) -> dict:
        user = self.db.query(User).filter(User.username == username).first()
        if not user:
            raise ValueError("用户不存在")

        if not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
            raise ValueError("密码错误")

        return self._build_response(user)

    def _build_response(self, user: User) -> dict:
        return {
            "token": create_token(user.username, user.id),
            "userId": user.id,
            "username": user.username,
            "email": user.email,
            "avatarUrl": user.avatar_url or "",
        }
