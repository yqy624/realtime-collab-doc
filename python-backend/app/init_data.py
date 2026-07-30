import bcrypt

from app.models.chat_message import ChatMessage
from app.models.document import Document
from app.models.user import User
from app.models.database import SessionLocal


def init_data():
    db = SessionLocal()
    try:
        admin = _create_user(db, "admin", "admin@example.com", "Admin", "0D8ABC")
        _create_user(db, "user1", "user1@example.com", "User1", "8E44AD")
        _create_user(db, "user2", "user2@example.com", "User2", "16A085")
        _create_default_document(db, admin)
        db.commit()
    finally:
        db.close()


def _create_user(db, username: str, email: str, avatar_name: str, color: str) -> User:
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        return existing
    pw_hash = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode("utf-8")
    user = User(
        username=username,
        email=email,
        password_hash=pw_hash,
        avatar_url=f"https://ui-avatars.com/api/?name={avatar_name}&background={color}&color=fff",
    )
    db.add(user)
    db.flush()
    return user


def _create_default_document(db, admin: User):
    existing = (db.query(Document)
                .filter(Document.creator_id == admin.id, Document.title == "欢迎使用实时协作文档系统")
                .first())
    if existing:
        return

    doc = Document(
        title="欢迎使用实时协作文档系统",
        content="这是一个公开示例文档。\n\n你可以打开两个账号同时编辑，体验实时协作、在线状态、光标同步和聊天功能。",
        creator_id=admin.id,
        is_public=True,
        revision=0,
    )
    db.add(doc)
    db.flush()

    chat = ChatMessage(
        document_id=doc.id,
        sender_id=admin.id,
        message="欢迎来到协作空间，试试发送 @user1 消息。",
        message_type="TEXT",
    )
    db.add(chat)
