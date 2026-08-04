from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.security import decode_access_token


bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        user_id = decode_access_token(credentials.credentials)
    except ValueError:
        raise unauthorized from None
    user = await db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


async def get_lecturer(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != "lecturer":
        raise HTTPException(status_code=403, detail="Lecturer role required")
    return user


async def get_student(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student role required")
    return user


DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
LecturerUser = Annotated[User, Depends(get_lecturer)]
StudentUser = Annotated[User, Depends(get_student)]
