"""Auth endpoints: register, login, refresh, me, logout."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.deps import get_current_user
from backend.auth.schemas import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserOut,
)
from backend.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from backend.db.models import User
from backend.db.session import get_db
from jose import JWTError

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_to_out(user: User) -> UserOut:
    return UserOut(uid=str(user.id), email=user.email, displayName=user.display_name)


def _make_tokens(user: User) -> TokenPair:
    sub = str(user.id)
    return TokenPair(
        access_token=create_access_token(sub),
        refresh_token=create_refresh_token(sub),
    )


@router.post("/register", response_model=AuthResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        display_name=req.displayName,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return AuthResponse(user=_user_to_out(user), tokens=_make_tokens(user))


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid email or password")
    return AuthResponse(user=_user_to_out(user), tokens=_make_tokens(user))


@router.post("/refresh", response_model=TokenPair)
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    try:
        payload = decode_token(req.refresh_token, expected_type="refresh")
        user_id = payload.get("sub")
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid refresh token: {e}")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    return _make_tokens(user)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return _user_to_out(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout() -> None:
    # Stateless JWT — client just discards tokens. Endpoint kept for symmetry.
    return None
