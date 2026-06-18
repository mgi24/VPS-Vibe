import asyncio
import os
import subprocess
import tempfile

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

from sqlalchemy import select, text as sa_text
from database import engine, AsyncSession, get_db
from models import Media


async def migrate():
    async with AsyncSession(engine) as db:
        result = await db.execute(
            select(Media).where(Media.mime_type.startswith("video/"))
        )
        videos = result.scalars().all()
        total = len(videos)
        print(f"Found {total} video(s) to process")

        for idx, media in enumerate(videos, 1):
            ext = os.path.splitext(media.filename or "")[1] or ".mp4"
            data = media.data
            old_size = len(data)
            thumb = None
            optimized = None

            print(f"[{idx}/{total}] Processing: {media.filename} ({old_size / 1024 / 1024:.1f} MB)")

            try:
                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as vf:
                    vf.write(data)
                    vf.flush()
                    in_path = vf.name

                out_path = in_path + "_out" + ext
                thumb_path = in_path + "_thumb.jpg"
                optimize = ext.lower() == ".mp4"

                if optimize:
                    r = subprocess.run(
                        ["ffmpeg", "-y", "-i", in_path, "-c", "copy", "-movflags", "+faststart", out_path],
                        capture_output=True, timeout=120,
                    )
                    if r.returncode != 0 or not os.path.exists(out_path):
                        print(f"  ⚠ faststart failed, skipping optimization")
                        optimize = False

                r = subprocess.run(
                    ["ffmpeg", "-y", "-i", out_path if optimize else in_path,
                     "-ss", "00:00:01", "-vframes", "1", "-q:v", "3", thumb_path],
                    capture_output=True, timeout=30,
                )
                if r.returncode == 0 and os.path.exists(thumb_path):
                    with open(thumb_path, "rb") as f:
                        thumb = f.read()
                    os.unlink(thumb_path)

                if optimize and os.path.exists(out_path):
                    with open(out_path, "rb") as f:
                        optimized = f.read()
                    os.unlink(out_path)
                elif os.path.exists(out_path):
                    os.unlink(out_path)

                os.unlink(in_path)

            except Exception as e:
                print(f"  ✗ Error: {e}")
                continue

            if optimized is not None:
                media.data = optimized
                media.size = len(optimized)
                new_size = len(optimized)
                print(f"  ✓ Faststart: {old_size / 1024 / 1024:.1f} → {new_size / 1024 / 1024:.1f} MB")

            if thumb is not None:
                media.thumbnail = thumb
                print(f"  ✓ Thumbnail: {len(thumb) / 1024:.1f} KB")

            await db.flush()

        await db.commit()
        print(f"\nDone! Processed {total} video(s)")


if __name__ == "__main__":
    asyncio.run(migrate())
