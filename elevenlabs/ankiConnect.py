#!/usr/bin/env python3
"""
Anki TTS Generator for Bulgarian Cards
Generates TTS audio for Bulgarian text in Anki cards and adds them to the cards.
"""

import json
import requests
import os
import time
import base64
from typing import List, Dict, Optional
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

# Load environment variables from .env file
load_dotenv()

class AnkiConnect:
    """Interface for communicating with Anki via AnkiConnect add-on"""
    
    def __init__(self, url: str = "http://localhost:8765"):
        self.url = url
    
    def request(self, action: str, params: Optional[Dict] = None) -> Dict:
        """Send request to AnkiConnect"""
        if params is None:
            params = {}
            
        request_data = {
            "action": action,
            "version": 6,
            "params": params
        }
        
        try:
            response = requests.post(self.url, json=request_data)
            response.raise_for_status()
            result = response.json()
            
            if result.get("error"):
                raise Exception(f"AnkiConnect error: {result['error']}")
                
            return result["result"]
        except requests.exceptions.ConnectionError:
            raise Exception("Could not connect to Anki. Make sure Anki is running and AnkiConnect add-on is installed.")
    
    def get_deck_names(self) -> List[str]:
        """Get all deck names"""
        return self.request("deckNames")
    
    def find_cards_in_deck(self, deck_name: str) -> List[int]:
        """Find all cards in a specific deck"""
        query = f"deck:{deck_name}"
        return self.request("findCards", {"query": query})
    
    def get_cards_info(self, card_ids: List[int]) -> List[Dict]:
        """Get detailed information about cards"""
        return self.request("cardsInfo", {"cards": card_ids})
    
    def get_note_info(self, note_ids: List[int]) -> List[Dict]:
        """Get note information"""
        return self.request("notesInfo", {"notes": note_ids})
    
    def store_media_file(self, filename: str, data: bytes) -> str:
        """Store media file in Anki's media folder"""
        encoded_data = base64.b64encode(data).decode('utf-8')
        self.request("storeMediaFile", {
            "filename": filename,
            "data": encoded_data
        })
        return filename
    
    def update_note_fields(self, note_id: int, fields: Dict[str, str]):
        """Update note fields"""
        self.request("updateNoteFields", {
            "note": {
                "id": note_id,
                "fields": fields
            }
        })
    
    def media_file_exists(self, filename: str) -> bool:
        """Check if a media file exists in Anki's media collection AND contains valid data"""
        try:
            result = self.request("retrieveMediaFile", {"filename": filename})
            if result is None:
                return False
            
            # Decode the base64 data to check if it's valid and non-empty
            try:
                audio_data = base64.b64decode(result)
                # Check if file has reasonable size (at least 1KB for valid MP3)
                if len(audio_data) < 1024:
                    print(f"Warning: Media file '{filename}' exists but is too small ({len(audio_data)} bytes) - likely empty or corrupted")
                    return False
                
                # Basic MP3 header check - MP3 files start with specific bytes
                if not (audio_data.startswith(b'ID3') or 
                       audio_data.startswith(b'\xff\xfb') or 
                       audio_data.startswith(b'\xff\xfa') or
                       audio_data.startswith(b'\xff\xf3') or
                       audio_data.startswith(b'\xff\xf2')):
                    print(f"Warning: Media file '{filename}' exists but doesn't appear to be valid MP3 format")
                    return False
                
                return True
                
            except Exception as decode_error:
                print(f"Warning: Could not decode media file '{filename}': {decode_error}")
                return False
                
        except Exception:
            return False
    
    def delete_media_file(self, filename: str) -> bool:
        """Delete a media file from Anki's media collection"""
        try:
            self.request("deleteMediaFile", {"filename": filename})
            return True
        except Exception as e:
            print(f"Warning: Could not delete media file '{filename}': {e}")
            return False

class ElevenLabsTTS:
    """Interface for ElevenLabs TTS API using official SDK"""
    
    def __init__(self, api_key: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM"):
        self.client = ElevenLabs(api_key=api_key)
        self.voice_id = voice_id  # Default voice (Rachel)
    
    def generate_speech(self, text: str, stability: float = 0.75, similarity_boost: float = 0.75) -> bytes:
        """Generate speech from text using ElevenLabs SDK"""
        try:
            # Validate text length - ElevenLabs requires minimum text length
            if len(text.strip()) < 3:
                # Pad very short text to meet minimum requirements
                text = text.strip() + "."
            
            audio_generator = self.client.text_to_speech.convert(
                text=text,
                voice_id=self.voice_id,
                model_id="eleven_multilingual_v2",  # Supports Bulgarian
                voice_settings=VoiceSettings(
                    stability=stability,
                    similarity_boost=similarity_boost,
                    style=0.0,
                    use_speaker_boost=True
                ),
                output_format="mp3_44100_128"
            )
            
            # Convert generator to bytes
            audio_bytes = b""
            for chunk in audio_generator:
                audio_bytes += chunk
            
            return audio_bytes
            
        except Exception as e:
            # Handle specific ElevenLabs errors
            if "400" in str(e) or "Bad Request" in str(e):
                raise Exception(f"Text too short or invalid for TTS: '{text}'. Try longer text.")
            else:
                raise Exception(f"ElevenLabs TTS error: {str(e)}")
    
    def get_available_voices(self) -> List[Dict]:
        """Get list of available voices using SDK"""
        try:
            voices_response = self.client.voices.get_all()
            return [
                {
                    "voice_id": voice.voice_id,
                    "name": voice.name,
                    "description": getattr(voice, 'description', 'No description'),
                    "category": getattr(voice, 'category', 'Unknown')
                }
                for voice in voices_response.voices
            ]
        except Exception as e:
            raise Exception(f"Error fetching voices: {str(e)}")

class BulgarianTTSProcessor:
    """Main processor for adding TTS to Bulgarian Anki cards"""
    
    def __init__(self, elevenlabs_api_key: str, voice_id: str = None):
        self.anki = AnkiConnect()
        self.tts = ElevenLabsTTS(elevenlabs_api_key, voice_id or "21m00Tcm4TlvDq8ikWAM")
        self.cache_dir = Path("tts_cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        # Load settings from environment
        self.rate_limit_delay = float(os.getenv('RATE_LIMIT_DELAY', '0.5'))
        self.tts_stability = float(os.getenv('TTS_STABILITY', '0.75'))
        self.tts_similarity = float(os.getenv('TTS_SIMILARITY_BOOST', '0.75'))
    
    def detect_bulgarian_text(self, text: str) -> bool:
        """Simple Bulgarian text detection"""
        # Bulgarian Cyrillic range: U+0400-U+04FF
        bulgarian_chars = sum(1 for char in text if '\u0400' <= char <= '\u04FF')
        return bulgarian_chars > len(text) * 0.3  # At least 30% Bulgarian characters
    
    def clean_text_for_tts(self, text: str) -> str:
        """Clean text for TTS generation"""
        # Remove HTML tags
        import re
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove pronunciation guides or other formatting
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\(.*?\)', '', text)
        
        return text.strip()
    
    def is_text_suitable_for_tts(self, text: str) -> tuple[bool, str]:
        """Check if text is suitable for TTS generation"""
        if not text or not text.strip():
            return False, "Empty text"
        
        # Check minimum length
        if len(text.strip()) < 1:
            return False, "Text too short"
        
        # Check if it's just punctuation or numbers
        import re
        if re.match(r'^[^\w\u0400-\u04FF]+$', text):
            return False, "Text contains only punctuation/symbols"
        
        # Check if it's meaningful Bulgarian text
        if not self.detect_bulgarian_text(text):
            return False, "Text doesn't appear to be Bulgarian"
        
        return True, "OK"
    
    def generate_filename(self, text: str) -> str:
        """Generate unique filename for TTS audio"""
        # Create hash of text for unique filename
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()[:8]
        return f"tts_bg_{text_hash}.mp3"
    
    def get_cached_audio(self, text: str) -> Optional[bytes]:
        """Check if audio is already cached"""
        filename = self.generate_filename(text)
        cache_path = self.cache_dir / filename
        
        if cache_path.exists():
            return cache_path.read_bytes()
        return None
    
    def cache_audio(self, text: str, audio_data: bytes):
        """Cache audio data"""
        filename = self.generate_filename(text)
        cache_path = self.cache_dir / filename
        cache_path.write_bytes(audio_data)
    
    def process_deck(self, deck_name: str, bulgarian_field: str = "Front", 
                    audio_field: str = "Audio", dry_run: bool = False):
        """Process all cards in a deck"""
        # breakpoint()  # Uncomment this line to debug
        print(f"Processing deck: {deck_name}")
        
        # Get all cards in deck
        card_ids = self.anki.find_cards_in_deck(deck_name)
        print(f"Found {len(card_ids)} cards in deck")
        
        if not card_ids:
            print("No cards found in deck")
            return
        
        # Get card information
        cards_info = self.anki.get_cards_info(card_ids)
        note_ids = [card["note"] for card in cards_info]
        notes_info = self.anki.get_note_info(note_ids)
        
        processed = 0
        skipped = 0
        errors = 0
        
        for note in notes_info:
            try:
                # Get Bulgarian text from specified field
                if bulgarian_field not in note["fields"]:
                    print(f"Field '{bulgarian_field}' not found in note {note['noteId']}")
                    skipped += 1
                    continue
                
                bulgarian_text = note["fields"][bulgarian_field]["value"]
                
                if not bulgarian_text.strip():
                    skipped += 1
                    continue
                
                # Clean and validate text
                clean_text = self.clean_text_for_tts(bulgarian_text)
                
                # Check if text is suitable for TTS
                is_suitable, reason = self.is_text_suitable_for_tts(clean_text)
                if not is_suitable:
                    print(f"Skipping text '{clean_text[:20]}...': {reason}")
                    skipped += 1
                    continue
                
                # Check if audio field already has content and validate it
                if audio_field in note["fields"] and note["fields"][audio_field]["value"].strip():
                    audio_field_content = note["fields"][audio_field]["value"].strip()
                    
                    # Extract filename from [sound:filename.mp3] format
                    import re
                    sound_match = re.search(r'\[sound:([^\]]+)\]', audio_field_content)
                    
                    if sound_match:
                        existing_filename = sound_match.group(1)
                        
                        # Check if the referenced file is valid
                        if self.anki.media_file_exists(existing_filename):
                            print(f"Audio field has valid content for note {note['noteId']} (file: {existing_filename})")
                            skipped += 1
                            continue
                        else:
                            print(f"Audio field references invalid file '{existing_filename}' for note {note['noteId']} - will regenerate")
                            # Clear the invalid reference so we can regenerate
                            if not dry_run:
                                self.anki.update_note_fields(note["noteId"], {audio_field: ""})
                    else:
                        print(f"Audio field has unrecognized content for note {note['noteId']}: '{audio_field_content}' - will regenerate")
                        # Clear the unrecognized content so we can regenerate  
                        if not dry_run:
                            self.anki.update_note_fields(note["noteId"], {audio_field: ""})
                
                # Generate filename and check if media file already exists in Anki
                filename = self.generate_filename(clean_text)
                if self.anki.media_file_exists(filename):
                    print(f"Audio file '{filename}' already exists in Anki media collection for note {note['noteId']}")
                    # Add the audio field reference if it's missing
                    if audio_field not in note["fields"] or not note["fields"][audio_field]["value"].strip():
                        audio_html = f"[sound:{filename}]"
                        fields_to_update = {audio_field: audio_html}
                        if not dry_run:
                            self.anki.update_note_fields(note["noteId"], fields_to_update)
                        print(f"Added existing audio reference to note {note['noteId']}")
                    skipped += 1
                    continue
                
                print(f"Processing: {clean_text[:50]}...")
                
                if dry_run:
                    print(f"[DRY RUN] Would generate TTS for: {clean_text}")
                    processed += 1
                    continue
                
                # Check cache first
                audio_data = self.get_cached_audio(clean_text)
                
                if not audio_data:
                    # Generate TTS
                    audio_data = self.tts.generate_speech(
                        clean_text, 
                        stability=self.tts_stability,
                        similarity_boost=self.tts_similarity
                    )
                    self.cache_audio(clean_text, audio_data)
                    print("Generated new TTS audio")
                else:
                    print("Using cached audio")
                
                # Always store in Anki media folder to ensure it exists there
                self.anki.store_media_file(filename, audio_data)
                
                # Update note with audio field
                audio_html = f"[sound:{filename}]"
                fields_to_update = {audio_field: audio_html}
                self.anki.update_note_fields(note["noteId"], fields_to_update)
                
                processed += 1
                print(f"Successfully added audio to note {note['noteId']}")
                
                # Small delay to avoid rate limiting
                time.sleep(self.rate_limit_delay)
                
            except Exception as e:
                print(f"Error processing note {note['noteId']}: {str(e)}")
                errors += 1
        
        print(f"\nProcessing complete!")
        print(f"Processed: {processed}")
        print(f"Skipped: {skipped}")
        print(f"Errors: {errors}")
    
    def list_decks(self):
        """List all available decks"""
        decks = self.anki.get_deck_names()
        print("Available decks:")
        for i, deck in enumerate(decks, 1):
            print(f"{i}. {deck}")
        return decks
    
    def list_voices(self):
        """List available TTS voices"""
        try:
            voices = self.tts.get_available_voices()
            print("Available voices:")
            for voice in voices:
                print(f"- {voice['name']} (ID: {voice['voice_id']}) - {voice.get('description', 'No description')}")
        except Exception as e:
            print(f"Error fetching voices: {str(e)}")

def main():
    """Main function with command-line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Add TTS audio to Bulgarian Anki cards")
    parser.add_argument("--api-key", help="ElevenLabs API key (can also be set via ELEVENLABS_API_KEY env var)")
    parser.add_argument("--deck", help="Deck name to process")
    parser.add_argument("--bulgarian-field", help="Field containing Bulgarian text (default from env or 'Front')")
    parser.add_argument("--audio-field", help="Field to add audio to (default from env or 'Audio')")
    parser.add_argument("--voice-id", help="ElevenLabs voice ID to use (can also be set via ELEVENLABS_VOICE_ID env var)")
    parser.add_argument("--list-decks", action="store_true", help="List available decks")
    parser.add_argument("--list-voices", action="store_true", help="List available voices")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without making changes")
    
    args = parser.parse_args()
    
    try:
        # Get API key from command line or environment
        api_key = args.api_key or os.getenv('ELEVENLABS_API_KEY')
        if not api_key:
            print("Error: ElevenLabs API key is required. Set it via --api-key argument or ELEVENLABS_API_KEY environment variable.")
            return 1
        
        # Get voice ID from command line or environment
        voice_id = args.voice_id or os.getenv('ELEVENLABS_VOICE_ID')
        
        # Get field names from command line or environment
        bulgarian_field = args.bulgarian_field or os.getenv('DEFAULT_BULGARIAN_FIELD', 'Front')
        audio_field = args.audio_field or os.getenv('DEFAULT_AUDIO_FIELD', 'Audio')
        
        processor = BulgarianTTSProcessor(api_key, voice_id)
        
        if args.list_decks:
            processor.list_decks()
            return
        
        if args.list_voices:
            processor.list_voices()
            return
        
        if not args.deck:
            print("Please specify a deck name with --deck or use --list-decks to see available decks")
            return
        
        processor.process_deck(
            deck_name=args.deck,
            bulgarian_field=bulgarian_field,
            audio_field=audio_field,
            dry_run=args.dry_run
        )
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())
