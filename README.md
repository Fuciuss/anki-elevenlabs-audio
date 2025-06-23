# Bulgarian TTS for Anki Cards

This script automatically generates Text-to-Speech (TTS) audio for Bulgarian text in your Anki cards using ElevenLabs API and adds the audio files to your cards.

## Features

- 🎯 **Automatic Bulgarian text detection** - Only processes cards containing Cyrillic text
- 🎵 **High-quality TTS** - Uses ElevenLabs multilingual model for Bulgarian pronunciation
- 💾 **Smart caching** - Avoids regenerating audio for identical text
- 🔄 **Batch processing** - Process entire decks at once
- 🛡️ **Safe operation** - Checks for existing audio to avoid duplicates
- 🔍 **Dry run mode** - Preview what will be processed without making changes

## Prerequisites

1. **Anki** with **AnkiConnect add-on** installed
2. **ElevenLabs API key** (get one at [elevenlabs.io](https://elevenlabs.io))
3. **Python 3.7+**

## Setup

### 1. Install AnkiConnect Add-on

1. Open Anki
2. Go to **Tools** → **Add-ons** → **Get Add-ons**
3. Enter code: `2055492159`
4. Restart Anki

### 2. Install Python Dependencies

Using UV (recommended):
```bash
uv sync
```

Or using pip:
```bash
pip install -e .
```

### 3. Configure Environment Variables

Create a `.env` file from the example:

```bash
cp env.example .env
```

Edit `.env` and add your actual API key and settings:

```bash
# Required
ELEVENLABS_API_KEY=your_actual_elevenlabs_api_key_here

# Optional settings
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
DEFAULT_BULGARIAN_FIELD=Front
DEFAULT_AUDIO_FIELD=Audio
TTS_STABILITY=0.75
TTS_SIMILARITY_BOOST=0.75
RATE_LIMIT_DELAY=0.5
```

**Important**: Never commit your `.env` file to version control as it contains your API keys!

## Usage

### Basic Usage

Make sure Anki is running and you have configured your `.env` file, then:

```bash
# List available decks
uv run python elevenlabs/ankiConnect.py --list-decks

# Process a specific deck (dry run first to see what will happen)
uv run python elevenlabs/ankiConnect.py --deck "Bulgarian Vocabulary" --dry-run

# Actually process the deck
uv run python elevenlabs/ankiConnect.py --deck "Bulgarian Vocabulary"
```

**Note**: With environment variables configured, you no longer need to pass `--api-key` for every command!

### Advanced Options

```bash
# Use specific fields (overrides environment settings)
uv run python elevenlabs/ankiConnect.py \
  --deck "My Bulgarian Deck" \
  --bulgarian-field "Bulgarian" \
  --audio-field "Pronunciation"

# Use a specific voice (overrides environment setting)
uv run python elevenlabs/ankiConnect.py \
  --deck "Bulgarian Vocabulary" \
  --voice-id "21m00Tcm4TlvDq8ikWAM"

# You can still override the API key if needed
uv run python elevenlabs/ankiConnect.py \
  --api-key "different_api_key" \
  --deck "Bulgarian Vocabulary"
```

### List Available Voices

```bash
uv run python elevenlabs/ankiConnect.py --list-voices
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--api-key` | ElevenLabs API key (overrides env var) | From `ELEVENLABS_API_KEY` |
| `--deck` | Name of the Anki deck to process | - |
| `--bulgarian-field` | Field containing Bulgarian text | From `DEFAULT_BULGARIAN_FIELD` or "Front" |
| `--audio-field` | Field where audio will be added | From `DEFAULT_AUDIO_FIELD` or "Audio" |
| `--voice-id` | ElevenLabs voice ID to use | From `ELEVENLABS_VOICE_ID` or default |
| `--list-decks` | List all available decks | - |
| `--list-voices` | List available TTS voices | - |
| `--dry-run` | Preview without making changes | false |

## Environment Variables

The script supports the following environment variables (set them in your `.env` file):

| Variable | Description | Default |
|----------|-------------|---------|
| `ELEVENLABS_API_KEY` | Your ElevenLabs API key (required) | - |
| `ELEVENLABS_VOICE_ID` | Voice ID to use for TTS | Rachel (default) |
| `DEFAULT_BULGARIAN_FIELD` | Default field containing Bulgarian text | "Front" |
| `DEFAULT_AUDIO_FIELD` | Default field for adding audio | "Audio" |
| `TTS_STABILITY` | Voice stability setting (0.0-1.0) | 0.75 |
| `TTS_SIMILARITY_BOOST` | Voice similarity boost (0.0-1.0) | 0.75 |
| `RATE_LIMIT_DELAY` | Delay between API calls (seconds) | 0.5 |
| `ANKI_CONNECT_URL` | AnkiConnect server URL | http://localhost:8765 |

## How It Works

1. **Connects to Anki** via AnkiConnect API
2. **Retrieves cards** from the specified deck
3. **Detects Bulgarian text** using Cyrillic character analysis
4. **Cleans text** by removing HTML tags and formatting
5. **Generates TTS audio** using ElevenLabs API
6. **Caches audio files** locally to avoid regeneration
7. **Adds audio to Anki** cards in the specified field

## Text Processing

The script automatically:
- Removes HTML tags from card text
- Strips pronunciation guides in brackets `[...]` or parentheses `(...)`
- Detects Bulgarian text (must be at least 30% Cyrillic characters)
- Skips cards that already have audio

## Audio Files

- Audio files are stored in Anki's media folder
- Files are named with format: `tts_bg_[hash].mp3`
- Local cache prevents regenerating identical audio
- Audio is embedded in cards using `[sound:filename.mp3]` format

## Troubleshooting

### "Could not connect to Anki"
- Make sure Anki is running
- Verify AnkiConnect add-on is installed
- Check if port 8765 is available

### "Text doesn't appear to be Bulgarian" or "Text too short"
- Check if your text contains Cyrillic characters
- The script requires at least 30% Cyrillic characters
- Very short text (1-2 characters) may be automatically padded with a period
- Empty text or punctuation-only text will be skipped
- You can adjust the detection threshold in the code if needed

### API Rate Limiting
- The script includes automatic delays between requests
- If you hit rate limits, the script will show an error
- Consider upgrading your ElevenLabs plan for higher limits

### Audio Field Issues
- Make sure your card template has the specified audio field
- The script won't overwrite existing audio content
- Use `--dry-run` to see what fields are available

## Cost Considerations

ElevenLabs charges per character processed. Consider:
- Using `--dry-run` first to see how many characters will be processed
- The script caches audio to avoid duplicate charges
- Bulgarian text is typically charged at standard rates

## Card Template Setup

Your Anki card template should include an audio field. Example template:

**Front:**
```html
{{Bulgarian}}
{{Audio}}
```

**Back:**
```html
{{English}}
```

## Contributing

Feel free to submit issues or pull requests to improve the script!

## License

This project is open source. Use it responsibly and in accordance with ElevenLabs' terms of service. 