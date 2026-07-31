# text.py

def get_song_text(song_data, is_youtube=False):
    """Get formatted text for song display."""
    
    title = song_data.get("title", "Unknown Title")
    artist = song_data.get("name", "Unknown Artist")
    
    more_info = song_data.get("more_info", {})
    album = more_info.get("album", "")
    duration = more_info.get("duration", "N/A")
    year = more_info.get("year", "")
    
    # Source emoji
    source_emoji = "▶️" if is_youtube else "🎵"
    source_name = "YouTube" if is_youtube else "JioSaavn"
    
    text = f"""
**🎵 {title}**

**👨‍🎤 Artist:** {artist}
**💿 Album:** {album}
**⏱️ Duration:** {duration}
**📅 Year:** {year}
**📡 Source:** {source_emoji} {source_name}

_This track was picked by @AartiMusicBot_
"""
    
    return text