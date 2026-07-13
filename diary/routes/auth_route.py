import os
import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from schemas import RegisterRequest, LoginRequest
from auth import hash_password, verify_password, create_token, get_current_user

router = APIRouter(prefix="/api", tags=["auth"])

def strip_html(text: str | None) -> str | None:
    return re.sub(r'<[^>]*>', '', text) if text else text


@router.post("/register")
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.username.ilike(body.username)))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        username=strip_html(body.username),
        password_hash=hash_password(body.password),
        role="general",
        approved=False,
    )
    db.add(user)
    await db.commit()
    return {"message": "Registered. Wait for admin approval."}


@router.post("/login")
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.approved:
        raise HTTPException(status_code=403, detail="Akun belum di-approve admin")

    token = create_token(user.id, user.role)
    response.set_cookie(key="token", value=token, httponly=True, max_age=604800)
    return {
        "message": "Login success",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "profile_pic": user.profile_pic,
        },
    }


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("token")
    return {"message": "Logged out"}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    if not user:
        return {"user": None}
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "profile_pic": user.profile_pic,
            "approved": user.approved,
        }
    }


@router.put("/settings/password")
async def change_password(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not verify_password(body["old_password"], user.password_hash):
        raise HTTPException(status_code=400, detail="Wrong password")
    user.password_hash = hash_password(body["new_password"])
    await db.commit()
    return {"message": "Password changed"}


@router.put("/settings/username")
async def change_username(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    existing = await db.execute(select(User).where(User.username == body["new_username"]))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")
    user.username = body["new_username"]
    await db.commit()
    return {"message": "Username changed"}


@router.put("/settings/profile")
async def change_profile(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    form = await request.form()
    file = form.get("file")
    if not file:
        raise HTTPException(status_code=400, detail="File required")

    ext = os.path.splitext(file.filename or "photo.jpg")[1] or ".jpg"
    filename = f"profile_{user.id}{ext}"
    filepath = f"/home/mamad/diary/assets/{filename}"

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    user.profile_pic = f"/assets/{filename}"
    await db.commit()
    return {"profile_pic": user.profile_pic}
