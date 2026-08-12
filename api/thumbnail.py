import os
import io
import logging
import tempfile
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

logger = logging.getLogger(__name__)


def generate_now_playing_card(thumbnail_url: str, title: str, artist: str) -> str:
    try:
        # Try maxresdefault first for best quality, fallback to hqdefault
        response = requests.get(thumbnail_url, timeout=10)
        response.raise_for_status()
        original = Image.open(io.BytesIO(response.content)).convert("RGB")

        # Full HD canvas — matches native thumbnail resolution
        canvas_size = (1280, 720)

        # Blurred, darkened background (stretched to fill full canvas)
        background = original.resize(canvas_size)
        background = background.filter(ImageFilter.GaussianBlur(35))
        overlay = Image.new("RGB", canvas_size, (0, 0, 0))
        background = Image.blend(background, overlay, 0.5)

        # Centered square album art (proportional to canvas height)
        art_size = 460
        square = original.resize((art_size, art_size))

        mask = Image.new("L", (art_size, art_size), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([0, 0, art_size, art_size], radius=20, fill=255)

        pos_x = (canvas_size[0] - art_size) // 2
        pos_y = 60
        background.paste(square, (pos_x, pos_y), mask)

        draw_bg = ImageDraw.Draw(background)

        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
            font_artist = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except Exception:
            font_title = ImageFont.load_default()
            font_artist = ImageFont.load_default()

        title_short = (title[:45] + "…") if len(title) > 45 else title
        artist_short = (artist[:50] + "…") if len(artist) > 50 else artist

        text_y = pos_y + art_size + 35
        draw_bg.text((canvas_size[0] // 2, text_y), title_short, font=font_title, fill="white", anchor="mm")
        draw_bg.text((canvas_size[0] // 2, text_y + 40), artist_short, font=font_artist, fill=(210, 210, 210), anchor="mm")

        out_path = os.path.join(tempfile.gettempdir(), f"nowplaying_{os.getpid()}_{abs(hash(title))}.jpg")
        background.save(out_path, "JPEG", quality=92)

        return out_path

    except Exception as e:
        logger.error(f"Thumbnail generation error: {e}")
        return None