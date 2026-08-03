# jiosaavn/plugins/__init__.py

"""
Plugins Package - Sabhi Bot Handlers
"""

# 🔥 SABHI FILES IMPORT KARO
from . import admin
from . import commands
from . import download_handler
from . import inline
from . import search_handler
from . import text
from . import inline_query
from . import download_callback
from . import chosen_inline_result

# 🔥 SABHI FILES KO __all__ MEIN ADD KARO
__all__ = [
    'admin',
    'commands',
    'download_handler',
    'inline',
    'search_handler',
    'text',
    'inline_query',
    'download_callback',
    'chosen_inline_result',
]

# Debug ke liye (optional)
print(f"✅ Plugins loaded: {', '.join(__all__)}")