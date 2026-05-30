from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ...core.config import settings
from ...core.response import fail, ok
from ...core.security import create_access_token
from ..deps import get_current_user

router = APIRouter(prefix="/auth", tags=["认证"])


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginBody):
    if body.username != settings.admin_username or body.password != settings.admin_password:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail=fail(40100, "用户名或密码错误"))
    token, expires = create_access_token(body.username)
    return ok({"access_token": token, "expires_in": expires})


@router.post("/refresh")
def refresh(user: str = Depends(get_current_user)):
    token, expires = create_access_token(user)
    return ok({"access_token": token, "expires_in": expires})


@router.get("/me")
def me(user: str = Depends(get_current_user)):
    return ok({"username": user})
