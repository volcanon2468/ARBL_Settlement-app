from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from app.infrastructure.config import settings
from app.core.security import create_access_token
router = APIRouter()


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
def login(request: LoginRequest, response: Response):
    if request.password != settings.APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")
    token = create_access_token()
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False,
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key="auth_token",
        httponly=True,
        samesite="lax",
        secure=False
    )
    return {"success": True}
