# jiosaavn/plugins/__init__.py

"""
Plugins Package - Sabhi Bot Handlers
"""

# 🔥 SABHI FILES IMPORT KARO
from . import admin
from . import commands
from . import download_handler
from . import search_handler
from . import text
from . import inline_query
from . import chosen_inline_result
from . import raw_debug


# 🔥 SABHI FILES KO __all__ MEIN ADD KARO
__all__ = [
    'admin',
    'commands',
    'download_handler',
    'search_handler',
    'text',
    'inline_query',
    'chosen_inline_result',
    'raw_debug',
]

# Debug ke liye (optional)
print(f"✅ Plugins loaded: {', '.join(__all__)}")