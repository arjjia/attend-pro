from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.dependencies import DbSession
from app.models import User
from app.schemas import LoginRequest, LoginResponse, UserPublic
from app.security import create_access_token, verify_password


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: DbSession) -> LoginResponse:
    user = await db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return LoginResponse(
        access_token=create_access_token(user.id),
        user=UserPublic.model_validate(user),
    )
