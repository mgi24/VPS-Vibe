from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import update

from database import get_db
from models import User, Notification
from auth import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "approved": u.approved,
            "request_poster": u.request_poster,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.post("/users/{user_id}/approve")
async def approve_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.approved = True
    await db.commit()
    return {"message": "User approved"}


@router.post("/users/{user_id}/role")
async def set_role(
    user_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.get("role") not in ("admin", "poster", "general"):
        raise HTTPException(status_code=400, detail="Invalid role")
    user.role = body["role"]
    user.request_poster = False

    await db.execute(
        update(Notification)
        .where(
            Notification.type == "poster_request",
            Notification.related_user_id == user_id,
        )
        .values(read=True)
    )

    await db.commit()
    return {"message": f"Role changed to {body['role']}"}


@router.get("/poster-requests")
async def poster_requests(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(
        select(User).where(User.request_poster == True).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]
