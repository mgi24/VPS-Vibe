import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Post, React, User
from auth import get_current_user

router = APIRouter(prefix="/api/posts", tags=["reacts"])


@router.post("/{post_id}/react")
async def toggle_react(post_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    post = await db.get(Post, post_id)
    if not post:
        return {"error": "Post not found"}

    user = await get_current_user(request, db)
    anon_id = None

    if user:
        result = await db.execute(
            select(React).where(React.post_id == post_id, React.user_id == user.id)
        )
        existing = result.scalar_one_or_none()
    else:
        anon_id = request.cookies.get("anon_id")
        if not anon_id:
            anon_id = str(uuid.uuid4())
        result = await db.execute(
            select(React).where(React.post_id == post_id, React.anonymous_id == anon_id)
        )
        existing = result.scalar_one_or_none()

    if existing:
        await db.delete(existing)
        await db.commit()
        reacted = False
    else:
        react = React(
            post_id=post_id,
            user_id=user.id if user else None,
            anonymous_id=anon_id if not user else None,
        )
        db.add(react)
        await db.commit()
        reacted = True

    count_result = await db.execute(select(React).where(React.post_id == post_id))
    count = len(count_result.all())

    response_data = {"reacted": reacted, "count": count}
    if not user and anon_id:
        response_data["anon_id"] = anon_id

    return response_data
