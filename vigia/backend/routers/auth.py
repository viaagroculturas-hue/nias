from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import jwt, JWTError
from config import get_settings
import hashlib

router = APIRouter()
settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# Em produção: usuários no banco com senha bcrypt
# Para o MVP: usuário único via env var
_DEMO_USER = {"username": "vigia", "password_hash": ""}


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


def _criar_token(sub: str, expires_hours: int = None) -> str:
    h = expires_hours or settings.jwt_expire_hours
    payload = {
        "sub": sub,
        "exp": datetime.utcnow() + timedelta(hours=h),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")


@router.post("/token", response_model=Token)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    # Validação simples para MVP — substituir por banco em produção
    if form.username != "vigia":
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    token = _criar_token(form.username)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.jwt_expire_hours * 3600,
    }


@router.get("/me")
async def me(user: str = Depends(get_current_user)):
    return {"username": user, "sistema": "VIGÍA"}
