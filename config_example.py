# Configuration Example for Bulgarian TTS Anki Script
# Copy this file to config.py and fill in your details

# ElevenLabs API Configuration
ELEVENLABS_API_KEY = "your_elevenlabs_api_key_here"

# Voice Settings (optional - uses default if not specified)
# You can get voice IDs by running: python ankiConnect.py --list-voices --api-key YOUR_KEY
VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Default voice (Rachel)

# Anki Configuration
ANKI_CONNECT_URL = "http://localhost:8765"  # Default AnkiConnect URL

# Field Configuration (adjust based on your card templates)
DEFAULT_BULGARIAN_FIELD = "Front"  # Field containing Bulgarian text
DEFAULT_AUDIO_FIELD = "Audio"      # Field where audio will be added

# TTS Settings
TTS_STABILITY = 0.75      # Voice stability (0.0 - 1.0)
TTS_SIMILARITY = 0.75     # Voice similarity boost (0.0 - 1.0)

# Processing Settings
RATE_LIMIT_DELAY = 0.5    # Delay between API calls (seconds)
CACHE_ENABLED = True      # Enable local audio caching 