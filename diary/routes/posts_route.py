import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Post, User, React, Comment, Notification
from schemas import PostCreate
from auth import get_current_user, require_poster

router = APIRouter(prefix="/api/posts", tags=["posts"])

SEGMENTS = {
    "umum": "#3b82f6",
    "teknologi": "#10b981",
    "hiburan": "#f59e0b",
    "olahraga": "#ef4444",
    "pendidikan": "#8b5cf6",
    "berita": "#ec4899",
}


@router.get("")
async def list_posts(
    request: Request,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10),
    offset: int = Query(0),
):
    result = await db.execute(
        select(Post).order_by(desc(Post.created_at)).offset(offset).limit(limit)
    )
    posts = result.scalars().all()

    out = []
    for post in posts:
        user = await db.get(User, post.user_id)
        react_count = await db.execute(select(React).where(React.post_id == post.id))
        comment_count = await db.execute(select(Comment).where(Comment.post_id == post.id))

        current_user = await get_current_user(request, db)
        user_reacted = None
        if current_user:
            r = await db.execute(
                select(React).where(React.post_id == post.id, React.user_id == current_user.id)
            )
            user_reacted = r.scalar_one_or_none()
        else:
            anon_id = request.cookies.get("anon_id")
            if anon_id:
                r = await db.execute(
                    select(React).where(React.post_id == post.id, React.anonymous_id == anon_id)
                )
                user_reacted = r.scalar_one_or_none()

        media_list = post.media_url.split(",") if post.media_url else []
        out.append(
            {
                "id": post.id,
                "type": post.type,
                "content": post.content,
                "media_url": post.media_url,
                "media_list": media_list,
                "segment": post.segment,
                "segment_color": SEGMENTS.get(post.segment, "#6b7280"),
                "created_at": post.created_at.isoformat() if post.created_at else None,
                "author": {
                    "id": user.id,
                    "username": user.username,
                    "profile_pic": user.profile_pic,
                },
                "react_count": len(react_count.all()),
                "comment_count": len(comment_count.all()),
                "user_reacted": bool(user_reacted),
            }
        )
    return out


@router.post("")
async def create_post(
    body: PostCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_poster),
):
    media_list = body.media_url.split(",") if body.media_url else []
    post_type = _detect_type(body.content or "", media_list)
    post = Post(
        user_id=user.id,
        type=post_type,
        content=body.content,
        media_url=body.media_url,
        segment=body.segment,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return {"message": "Post created", "id": post.id}


def _detect_type(content: str, media_urls: list) -> str:
    if media_urls:
        ext = os.path.splitext(media_urls[0])[1].lower()
        if ext in (".mp4", ".webm", ".ogg", ".mov", ".avi"):
            return "video"
        return "photo"
    if content and ("http://" in content or "https://" in content):
        return "link"
    return "text"


@router.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    urls = []
    for f in files:
        ext = os.path.splitext(f.filename or "file")[1] or ".bin"
        name = f"{uuid.uuid4().hex}{ext}"
        path = f"/home/mamad/diary/assets/uploads/{name}"
        content = await f.read()
        with open(path, "wb") as out:
            out.write(content)
        urls.append(f"/assets/uploads/{name}")
    return {"urls": urls}


@router.put("/{post_id}")
async def update_post(
    post_id: int,
    body: PostCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your post")
    media_list = body.media_url.split(",") if body.media_url else []
    post.type = _detect_type(body.content or "", media_list)
    post.content = body.content
    post.media_url = body.media_url
    post.segment = body.segment
    await db.commit()
    return {"message": "Post updated", "id": post.id}


@router.get("/{post_id}")
async def get_post(post_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    user = await db.get(User, post.user_id)
    react_count = await db.execute(select(React).where(React.post_id == post.id))
    comment_count = await db.execute(select(Comment).where(Comment.post_id == post.id))
    current_user = await get_current_user(request, db)
    user_reacted = None
    if current_user:
        r = await db.execute(select(React).where(React.post_id == post.id, React.user_id == current_user.id))
        user_reacted = r.scalar_one_or_none()
    else:
        anon_id = request.cookies.get("anon_id")
        if anon_id:
            r = await db.execute(select(React).where(React.post_id == post.id, React.anonymous_id == anon_id))
            user_reacted = r.scalar_one_or_none()

    media_list = post.media_url.split(",") if post.media_url else []
    return {
        "id": post.id,
        "type": post.type,
        "content": post.content,
        "media_url": post.media_url,
        "media_list": media_list,
        "segment": post.segment,
        "segment_color": SEGMENTS.get(post.segment, "#6b7280"),
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "author": {"id": user.id, "username": user.username, "profile_pic": user.profile_pic},
        "react_count": len(react_count.all()),
        "comment_count": len(comment_count.all()),
        "user_reacted": bool(user_reacted),
    }


@router.delete("/{post_id}")
async def delete_post(
    post_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your post")
    await db.delete(post)
    await db.commit()
    return {"message": "Post deleted"}


@router.post("/{post_id}/request-poster")
async def request_poster(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user.request_poster = True

    admin_list = await db.execute(select(User).where(User.role == "admin"))
    for admin in admin_list.scalars().all():
        notif = Notification(
            user_id=admin.id,
            type="poster_request",
            message=f"{user.username} ingin jadi poster",
            related_user_id=user.id,
        )
        db.add(notif)

    await db.commit()
    return {"message": "Request sent to admin"}
