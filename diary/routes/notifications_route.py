from fastapi import APIRouter, Depends
from sqlalchemy import select, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Notification, User
from auth import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user:
        return []
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(desc(Notification.created_at))
        .limit(50)
    )
    notifs = result.scalars().all()
    return [
        {
            "id": n.id,
            "type": n.type,
            "message": n.message,
            "related_user_id": n.related_user_id,
            "related_post_id": n.related_post_id,
            "read": n.read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifs
    ]


@router.get("/unread-count")
async def unread_count(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user:
        return {"count": 0}
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == user.id, Notification.read == False
        )
    )
    return {"count": len(result.all())}


@router.post("/{notif_id}/read")
async def mark_read(
    notif_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user:
        return {"error": "Not authenticated"}
    notif = await db.get(Notification, notif_id)
    if notif and notif.user_id == user.id:
        notif.read = True
        await db.commit()
    return {"message": "Marked as read"}


@router.post("/read-all")
async def read_all(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user:
        return {"error": "Not authenticated"}
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read == False)
        .values(read=True)
    )
    await db.commit()
    return {"message": "All marked as read"}
