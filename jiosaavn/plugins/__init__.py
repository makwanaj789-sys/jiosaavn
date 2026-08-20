from . import admin
from . import commands
from . import download_handler
from . import search_handler
from . import text
from . import inline_query
from . import chosen_inline_result
from . import favorites
from . import settings
from . import voice_chat
from . import cache_warmer
from . import broadcast

# 🔥 SABHI FILES KO __all__ MEIN ADD KARO
__all__ = [
    'admin',
    'commands',
    'download_handler',
    'search_handler',
    'text',
    'inline_query',
    'chosen_inline_result',
    'favorites',
    'settings',
    'voice_chat',
    'cache_warmer',
    'broadcast',
    
]

# Debug ke liye (optional)
print(f"✅ Plugins loaded: {', '.join(__all__)}")