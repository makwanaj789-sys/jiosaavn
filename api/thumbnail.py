import os
import io
import logging
import tempfile
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

logger = logging.getLogger(__name__)


def generate_now_playing_card(thumbnail_url: str, title: str, artist: str) -> str:
    """
    Downloads the YouTube thumbnail and creates a Spotify-style
    now-playing card: blurred background + centered square album art.
    Returns local filepath of the generated image.
    """
    try:
        response = requests.get(thumbnail_url, timeout=10)
        response.raise_for_status()
        original = Image.open(io.BytesIO(response.content)).convert("RGB")

        canvas_size = (1000, 1000)

        # Blurred, darkened background
        background = original.resize(canvas_size)
        background = background.filter(ImageFilter.GaussianBlur(30))
        overlay = Image.new("RGB", canvas_size, (0, 0, 0))
        background = Image.blend(background, overlay, 0.45)

        # Center square album art
        art_size = 640
        square = original.resize((art_size, art_size))

        # Rounded corners mask
        mask = Image.new("L", (art_size, art_size), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([0, 0, art_size, art_size], radius=24, fill=255)

        pos = ((canvas_size[0] - art_size) // 2, 120)
        background.paste(square, pos, mask)

        # Simple shadow-style border under art (subtle)
        draw_bg = ImageDraw.Draw(background)

        # Title text
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
            font_artist = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
        except Exception:
            font_title = ImageFont.load_default()
            font_artist = ImageFont.load_default()

        title_short = (title[:40] + "…") if len(title) > 40 else title
        artist_short = (artist[:45] + "…") if len(artist) > 45 else artist

        text_y = pos[1] + art_size + 40
        draw_bg.text((canvas_size[0] // 2, text_y), title_short, font=font_title, fill="white", anchor="mm")
        draw_bg.text((canvas_size[0] // 2, text_y + 50), artist_short, font=font_artist, fill=(200, 200, 200), anchor="mm")

        out_path = os.path.join(tempfile.gettempdir(), f"nowplaying_{os.getpid()}_{abs(hash(title))}.jpg")
        background.save(out_path, "JPEG", quality=90)

        return out_path

    except Exception as e:
        logger.error(f"Thumbnail generation error: {e}")
        return None