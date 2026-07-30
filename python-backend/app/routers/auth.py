from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.schemas.models import ApiResponse, AuthRequest, AuthResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(body: AuthRequest, db: Session = Depends(get_db)):
    try:
        result = AuthService(db).register(body.username, body.password, body.email)
        return ApiResponse.ok(result)
    except ValueError as e:
        return ApiResponse.fail(str(e))


@router.post("/login")
def login(body: AuthRequest, db: Session = Depends(get_db)):
    try:
        result = AuthService(db).login(body.username, body.password)
        return ApiResponse.ok(result)
    except ValueError as e:
        return ApiResponse.fail(str(e))
