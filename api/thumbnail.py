import os
import io
import logging
import tempfile
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

logger = logging.getLogger(__name__)


def generate_now_playing_card(thumbnail_url: str, title: str, artist: str) -> str:
    try:
        response = requests.get(thumbnail_url, timeout=10)
        if response.status_code != 200:
            fallback_url = thumbnail_url.replace("maxresdefault", "hqdefault")
            response = requests.get(fallback_url, timeout=10)
        response.raise_for_status()
        original = Image.open(io.BytesIO(response.content)).convert("RGB")

        canvas_size = (1280, 720)

        # Blurred, darkened background
        background = original.resize(canvas_size)
        background = background.filter(ImageFilter.GaussianBlur(35))
        overlay = Image.new("RGB", canvas_size, (0, 0, 0))
        background = Image.blend(background, overlay, 0.55)

        # Centered square album art with rounded corners
        art_size = 400
        square = original.resize((art_size, art_size))

        mask = Image.new("L", (art_size, art_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([0, 0, art_size, art_size], radius=24, fill=255)

        pos_x = (canvas_size[0] - art_size) // 2
        pos_y = 90
        background.paste(square, (pos_x, pos_y), mask)

        draw = ImageDraw.Draw(background)

        # Fonts
        try:
            font_brand = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
            font_artist = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            font_tag = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except Exception:
            font_brand = font_title = font_artist = font_tag = ImageFont.load_default()

        # 🔥 Top branding bar
        draw.rectangle([0, 0, canvas_size[0], 60], fill=(0, 0, 0))
        draw.text(
            (canvas_size[0] // 2, 30),
            "♫  A A R T I   M U S I C  ♫",
            font=font_brand,
            fill=(255, 255, 255),
            anchor="mm"
        )

        # Accent line under the branding bar
        draw.rectangle([0, 60, canvas_size[0], 64], fill=(29, 185, 84))  # Spotify-ish green

        # Track title + artist
        title_short = (title[:42] + "…") if len(title) > 42 else title
        artist_short = (artist[:48] + "…") if len(artist) > 48 else artist

        text_y = pos_y + art_size + 45
        draw.text((canvas_size[0] // 2, text_y), title_short, font=font_title, fill="white", anchor="mm")
        draw.text((canvas_size[0] // 2, text_y + 42), artist_short, font=font_artist, fill=(200, 200, 200), anchor="mm")

        # 🔥 Bottom watermark
        draw.text(
            (canvas_size[0] // 2, canvas_size[1] - 30),
            "@AartiMusic_bot  •  your music, anywhere",
            font=font_tag,
            fill=(150, 150, 150),
            anchor="mm"
        )

        out_path = os.path.join(tempfile.gettempdir(), f"nowplaying_{os.getpid()}_{abs(hash(title))}.jpg")
        background.save(out_path, "JPEG", quality=92)

        return out_path

    except Exception as e:
        logger.error(f"Thumbnail generation error: {e}")
        return None