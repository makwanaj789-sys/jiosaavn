# handlers/__init__.py

from . import admin
from . import commands
from . import download_handler
from . import search_handler
from . import text

# 🔥 YEH DO LINE ADD KARO - Inline handlers ke liye
from . import inline
from . import chosen_inline

# 🔥 YEH LINE BHI ADD KARO (agar api folder hai toh)
from . import youtube  # Agar youtube.py handlers mein hai toh

__all__ = [
    'commands',
    'download_handler',
    'search_handler',
    'inline',        # ✅ ADD
    'chosen_inline', # ✅ ADD
    'youtube'        # ✅ ADD (agar zaroorat ho)
]