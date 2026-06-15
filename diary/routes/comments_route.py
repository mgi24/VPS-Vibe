from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Post, Comment, User, Notification
from schemas import CommentCreate
from auth import get_current_user

router = APIRouter(prefix="/api/posts", tags=["comments"])


@router.get("/{post_id}/comments")
async def list_comments(post_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Comment).where(Comment.post_id == post_id).order_by(desc(Comment.created_at))
    )
    comments = result.scalars().all()
    out = []
    for c in comments:
        author_name = c.guest_name or "Unknown"
        author_pic = "/assets/default-profile.png"
        if c.user_id:
            user = await db.get(User, c.user_id)
            if user:
                author_name = user.username
                author_pic = user.profile_pic
        out.append(
            {
                "id": c.id,
                "content": c.content,
                "author_name": author_name,
                "author_pic": author_pic,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
        )
    return out


@router.post("/{post_id}/comments")
async def create_comment(
    post_id: int,
    body: CommentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    user = await get_current_user(request, db)
    comment = Comment(
        post_id=post_id,
        user_id=user.id if user else None,
        guest_name=body.guest_name if not user else None,
        content=body.content,
    )

    if not user and not body.guest_name:
        raise HTTPException(status_code=400, detail="Guest name required")

    if not user and body.guest_name:
        existing = await db.execute(
            select(User).where(User.username == body.guest_name)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Name taken by registered user. Please login or use another name.",
            )

    db.add(comment)
    await db.flush()

    commenter_name = user.username if user else body.guest_name
    if post.user_id != (user.id if user else None):
        notif = Notification(
            user_id=post.user_id,
            type="new_comment",
            message=f"{commenter_name} berkomentar di post Anda",
            related_user_id=user.id if user else None,
            related_post_id=post_id,
        )
        db.add(notif)

    await db.commit()
    return {"message": "Comment added", "id": comment.id}
