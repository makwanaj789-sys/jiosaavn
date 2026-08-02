# handlers/__init__.py

from . import admin
from . import commands
from . import download_handler
from . import search_handler
from . import text
from . import inline
from . import chosen_inline

# 🔥 Youtube api folder mein hai toh alag se import
# from api import youtube  # Agar api folder mein hai

__all__ = [
    'admin',
    'commands',
    'download_handler',
    'search_handler',
    'text',
    'inline',
    'chosen_inline',
    # 'youtube'  # Comment karo agar api folder mein hai
]