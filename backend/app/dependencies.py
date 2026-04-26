from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.auth_service import AuthService

_bearer = HTTPBearer()


@dataclass
class CurrentUser:
    id:       int
    role:     str
    username: str


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> CurrentUser:
    try:
        payload = AuthService.decode_access_token(credentials.credentials)
        return CurrentUser(
            id=int(payload["sub"]),
            role=payload["role"],
            username=payload.get("username", ""),
        )
    except (PermissionError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def require_role(roles: list[str]):
    async def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Insufficient permissions")
        return user
    return _check
