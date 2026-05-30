from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.response import fail
from ..core.security import decode_token


def get_current_user(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail=fail(40100, "未登录"))
    token = authorization[7:]
    sub = decode_token(token)
    if not sub:
        raise HTTPException(status_code=401, detail=fail(40100, "Token 失效"))
    return sub


DbSession = Depends(get_db)
AuthUser = Depends(get_current_user)
