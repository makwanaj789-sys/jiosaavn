# jiosaavn/plugins/__init__.py

"""
Plugins Package - Sabhi Bot Handlers
"""

# 🔥 SABHI FILES IMPORT KARO
from . import admin
from . import chosen_inline
from . import commands
from . import download_handler
from . import inline
from . import search_handler
from . import text

# 🔥 SABHI FILES KO __all__ MEIN ADD KARO
__all__ = [
    'admin',
    'chosen_inline',
    'commands',
    'download_handler',
    'inline',
    'search_handler',
    'text',
]

# Debug ke liye (optional)
print(f"✅ Plugins loaded: {', '.join(__all__)}")