from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.security import decode_session_token


bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    attendpro_session: Annotated[str | None, Cookie()] = None,
) -> User:
    token = credentials.credentials if credentials else attendpro_session
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication session",
    )
    if not token:
        raise unauthorized
    try:
        user_id = decode_session_token(token)
    except ValueError:
        raise unauthorized from None
    user = await db.get(User, user_id)
    if user is None or not user.active:
        raise unauthorized
    return user


async def get_teacher(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher role required")
    return user


async def get_student(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student role required")
    return user


DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
TeacherUser = Annotated[User, Depends(get_teacher)]
StudentUser = Annotated[User, Depends(get_student)]
