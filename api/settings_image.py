import os
import io
import logging
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets"
)
os.makedirs(CACHE_DIR, exist_ok=True)

SETTINGS_CARD_PATH = os.path.join(CACHE_DIR, "settings_card.jpg")


def build_settings_card(pfp_path: str) -> str:
    """
    Builds the settings card once from the bot's profile photo,
    then reuses the cached file forever.
    """
    if os.path.exists(SETTINGS_CARD_PATH):
        return SETTINGS_CARD_PATH

    try:
        original = Image.open(pfp_path).convert("RGB")
        canvas = (1280, 720)

        bg = original.resize(canvas).filter(ImageFilter.GaussianBlur(40))
        bg = Image.blend(bg, Image.new("RGB", canvas, (0, 0, 0)), 0.6)

        art = 340
        square = original.resize((art, art))
        mask = Image.new("L", (art, art), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, art, art], radius=24, fill=255)

        px = (canvas[0] - art) // 2
        py = 110
        bg.paste(square, (px, py), mask)

        d = ImageDraw.Draw(bg)
        try:
            f_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
            f_mid = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
            f_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except Exception:
            f_big = f_mid = f_sm = ImageFont.load_default()

        cy = py + art // 2
        d.text((px // 2, cy), "AARTI", font=f_big, fill="white", anchor="mm")
        d.text((px + art + (canvas[0] - px - art) // 2, cy), "MUSIC", font=f_big, fill="white", anchor="mm")

        d.text((canvas[0] // 2, py + art + 50), "SETTINGS", font=f_mid, fill="white", anchor="mm")
        d.text(
            (canvas[0] // 2, py + art + 95),
            "Search  •  Stream  •  Save  •  Shuffle",
            font=f_sm, fill=(200, 200, 200), anchor="mm"
        )

        bg.save(SETTINGS_CARD_PATH, "JPEG", quality=92)
        logger.info(f"✅ Settings card generated: {SETTINGS_CARD_PATH}")
        return SETTINGS_CARD_PATH

    except Exception as e:
        logger.error(f"Settings card generation error: {e}")
        return None