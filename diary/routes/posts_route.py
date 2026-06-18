import os
import subprocess
import tempfile
import uuid
import mimetypes

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Post, User, React, Comment, Notification, Media
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


def _process_video(data: bytes, ext: str) -> tuple[bytes | None, bytes | None]:
    """Optimize video (faststart) and generate thumbnail.
    Returns (optimized_bytes, thumbnail_bytes) or (None, None) on failure.
    """
    thumb = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as vf:
            vf.write(data)
            vf.flush()
            in_path = vf.name

        out_path = in_path + "_out" + ext
        thumb_path = in_path + "_thumb.jpg"

        # faststart: move moov atom to beginning (mp4 only, no re-encode)
        optimize = ext.lower() == ".mp4"
        if optimize:
            subprocess.run(
                ["ffmpeg", "-y", "-i", in_path, "-c", "copy", "-movflags", "+faststart", out_path],
                capture_output=True, timeout=120,
            )
            if not os.path.exists(out_path):
                optimize = False

        # generate thumbnail at 1s
        subprocess.run(
            ["ffmpeg", "-y", "-i", out_path if optimize else in_path,
             "-ss", "00:00:01", "-vframes", "1", "-q:v", "3", thumb_path],
            capture_output=True, timeout=30,
        )

        os.unlink(in_path)

        if os.path.exists(thumb_path):
            with open(thumb_path, "rb") as f:
                thumb = f.read()
            os.unlink(thumb_path)

        if optimize and os.path.exists(out_path):
            with open(out_path, "rb") as f:
                optimized = f.read()
            os.unlink(out_path)
            return optimized, thumb

        if os.path.exists(out_path):
            os.unlink(out_path)

        return None, thumb
    except Exception:
        return None, None


@router.post("/upload")
async def upload_files(files: list[UploadFile] = File(...), db: AsyncSession = Depends(get_db)):
    urls = []
    for f in files:
        ext = os.path.splitext(f.filename or "file")[1] or ".bin"
        name = f"{uuid.uuid4().hex}{ext}"
        data = await f.read()
        mime = f.content_type or mimetypes.guess_type(f.filename or "file")[0] or "application/octet-stream"
        thumb = None
        if mime.startswith("video/"):
            optimized, thumb = _process_video(data, ext)
            if optimized is not None:
                data = optimized
        media = Media(
            filename=name,
            original_name=f.filename or "file",
            mime_type=mime,
            data=data,
            thumbnail=thumb,
            size=len(data),
        )
        db.add(media)
        urls.append(f"/api/media/{name}")
    await db.commit()
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
