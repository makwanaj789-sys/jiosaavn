# api/__init__.py

# 🔥 Sirf wahi import karo jo exist karte hain
from . import search_engine
from . import youtube
from . import provider  # Agar provider.py hai toh

# Agar admin file nahi hai toh yeh line hatao
# from . import admin  # ❌ REMOVE

__all__ = [
    'search_engine',
    'youtube',
    'provider',  # Agar hai toh
]