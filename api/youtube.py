import os
import tempfile
import asyncio
import yt_dlp
import re
import uuid


def is_url(text):
    youtube_regex = r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/'
    return re.match(youtube_regex, text) is not None


def _get_cookies_file():
    cookies_path = os.path.join(os.getcwd(), "cookies.txt")
    if os.path.exists(cookies_path):
        return cookies_path
    logger.warning("⚠️ cookies.txt not found!")
    return None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
            suffix=".txt"
        ) as f:
            f.write(cookies_data)
            return f.name

    except Exception as e:
        print(f"⚠️ Error creating cookies file: {e}")
        return None


async def download_video(query: str):
    print(f"🔍 DEBUG: Original query = {query}")

    cookies_path = _get_cookies_file()

    if not is_url(query):
        final_query = f"ytsearch10:{query}"
        download = False
    else:
        final_query = query
        download = True

    temp_dir = os.path.join(
        tempfile.gettempdir(),
        f"ytdl_{uuid.uuid4().hex[:8]}"
    )

    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "default_search": "ytsearch1",
        "geo_bypass": True,
        "extract_flat": False,
        "cookiefile": cookies_path,   # 🔥 FIX: ab cookies actually use ho rahi hain
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"]
            }
        },
        "outtmpl": os.path.join(temp_dir, "%(title)s.%(ext)s"),
    }

    try:
        loop = asyncio.get_running_loop()

        def sync_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(final_query, download=download)

        info = await loop.run_in_executor(None, sync_download)

        if download:
            filepath = None
            if info.get("requested_downloads"):
                filepath = info["requested_downloads"][0].get("filepath")

            if not filepath:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    filepath = ydl.prepare_filename(info)
                if not os.path.exists(filepath):
                    base = os.path.splitext(filepath)[0]
                    for ext in ("webm", "m4a", "mp3", "opus"):
                        candidate = base + "." + ext
                        if os.path.exists(candidate):
                            filepath = candidate
                            break

            return {
                "success": True,
                "data": {
                    "title": info.get("title"),
                    "duration": info.get("duration"),
                    "uploader": info.get("uploader"),
                    "filepath": filepath
                }
            }
        else:
            entries = info.get("entries", [])
            if not entries:
                return {"success": False, "error": "No results found"}

            results = [{
                "id": e.get("id"),
                "title": e.get("title"),
                "duration": e.get("duration"),
                "uploader": e.get("uploader"),
                "url": f"https://www.youtube.com/watch?v={e.get('id')}",
                "source": "youtube"
            } for e in entries]

            return {"success": True, "results": results, "total": len(results)}

    except Exception as e:
        print(f"❌ DEBUG: yt-dlp Exception = {e}")
        return {"success": False, "error": str(e)}

    finally:
        if cookies_path and os.path.exists(cookies_path):
            try:
                os.remove(cookies_path)
            except Exception:
                pass