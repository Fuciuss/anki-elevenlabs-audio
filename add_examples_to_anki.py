#!/usr/bin/env python3
"""
Add Bulgarian and English Examples to Anki Cards
This script reads examples from bulgarian_words_1000_v2.tsv and adds them to existing cards in the Anki deck.
"""

import csv
import json
import requests
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class AnkiConnect:
    """Simple AnkiConnect interface for updating cards"""
    
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
    
    def find_notes_in_deck(self, deck_name: str) -> List[int]:
        """Find all note IDs in a specific deck"""
        query = f"deck:\"{deck_name}\""
        return self.request("findNotes", {"query": query})
    
    def get_notes_info(self, note_ids: List[int]) -> List[Dict]:
        """Get note information"""
        return self.request("notesInfo", {"notes": note_ids})
    
    def get_model_names(self) -> List[str]:
        """Get all note type (model) names"""
        return self.request("modelNames")
    
    def get_model_field_names(self, model_name: str) -> List[str]:
        """Get field names for a specific note type"""
        return self.request("modelFieldNames", {"modelName": model_name})
    
    def add_model_field(self, model_name: str, field_name: str, index: Optional[int] = None):
        """Add a new field to a note type"""
        params = {
            "modelName": model_name,
            "fieldName": field_name
        }
        if index is not None:
            params["index"] = index
        
        return self.request("addField", params)
    
    def update_note_fields(self, note_id: int, fields: Dict[str, str]):
        """Update note fields"""
        self.request("updateNoteFields", {
            "note": {
                "id": note_id,
                "fields": fields
            }
        })


class ExampleUpdater:
    """Updates Anki cards with examples from TSV file"""
    
    def __init__(self, tsv_file: str, deck_name: str = "Rees-Bulgarian-Vocab"):
        self.tsv_file = Path(tsv_file)
        self.deck_name = deck_name
        self.anki = AnkiConnect()
        self.examples_data = {}
        
    def load_examples_from_tsv(self):
        """Load examples from TSV file"""
        print(f"Loading examples from {self.tsv_file}...")
        
        if not self.tsv_file.exists():
            raise FileNotFoundError(f"TSV file not found: {self.tsv_file}")
        
        with open(self.tsv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file, delimiter='\t')
            
            for row in reader:
                bulgarian = row.get('Bulgarian', '').strip()
                english = row.get('English', '').strip()
                bulgarian_example = row.get('Bulgarian_Example', '').strip()
                english_example = row.get('English_Example', '').strip()
                
                if bulgarian and bulgarian_example and english_example:
                    # Use Bulgarian text as key to match with Front field
                    self.examples_data[bulgarian] = {
                        'english': english,
                        'bulgarian_example': bulgarian_example,
                        'english_example': english_example
                    }
        
        print(f"Loaded {len(self.examples_data)} examples from TSV file")
    
    def check_deck_exists(self) -> bool:
        """Check if the target deck exists"""
        deck_names = self.anki.get_deck_names()
        return self.deck_name in deck_names
    
    def get_notes_from_deck(self) -> List[Dict]:
        """Get all notes from the target deck"""
        note_ids = self.anki.find_notes_in_deck(self.deck_name)
        if not note_ids:
            raise Exception(f"No notes found in deck '{self.deck_name}'")
        
        notes = self.anki.get_notes_info(note_ids)
        print(f"Found {len(notes)} notes in deck '{self.deck_name}'")
        return notes
    
    def ensure_example_fields_exist(self, notes: List[Dict]):
        """Ensure the note type has fields for examples"""
        if not notes:
            return
        
        # Get the note type from the first note
        model_name = notes[0]['modelName']
        print(f"Working with note type: {model_name}")
        
        # Get current fields
        current_fields = self.anki.get_model_field_names(model_name)
        print(f"Current fields: {current_fields}")
        
        # Add Bulgarian_Example field if it doesn't exist
        if 'Bulgarian_Example' not in current_fields:
            print("Adding 'Bulgarian_Example' field...")
            try:
                self.anki.add_model_field(model_name, 'Bulgarian_Example')
                print("✓ Added Bulgarian_Example field")
            except Exception as e:
                print(f"Warning: Could not add Bulgarian_Example field: {e}")
        
        # Add English_Example field if it doesn't exist
        if 'English_Example' not in current_fields:
            print("Adding 'English_Example' field...")
            try:
                self.anki.add_model_field(model_name, 'English_Example')
                print("✓ Added English_Example field")
            except Exception as e:
                print(f"Warning: Could not add English_Example field: {e}")
    
    def match_and_update_notes(self, notes: List[Dict], dry_run: bool = False) -> Tuple[int, int, int]:
        """Match notes with examples and update them"""
        updated_count = 0
        matched_count = 0
        skipped_count = 0
        
        print(f"\n{'DRY RUN - ' if dry_run else ''}Matching and updating notes...")
        
        for note in notes:
            note_id = note['noteId']
            fields = note['fields']
            
            # Get Bulgarian text from Front field
            front_text = fields.get('Front', {}).get('value', '').strip()
            
            if not front_text:
                print(f"Warning: Note {note_id} has empty Front field")
                skipped_count += 1
                continue
            
            # Check if we have examples for this Bulgarian text
            if front_text in self.examples_data:
                matched_count += 1
                example_data = self.examples_data[front_text]
                
                # Check if examples are already present
                current_bg_example = fields.get('Bulgarian_Example', {}).get('value', '').strip()
                current_en_example = fields.get('English_Example', {}).get('value', '').strip()
                
                if current_bg_example and current_en_example:
                    print(f"  Note {note_id} ({front_text}): Already has examples, skipping")
                    skipped_count += 1
                    continue
                
                # Prepare update fields
                update_fields = {}
                
                if not current_bg_example:
                    update_fields['Bulgarian_Example'] = example_data['bulgarian_example']
                
                if not current_en_example:
                    update_fields['English_Example'] = example_data['english_example']
                
                if update_fields:
                    print(f"  {'[DRY RUN] ' if dry_run else ''}Updating note {note_id} ({front_text})")
                    print(f"    Bulgarian Example: {example_data['bulgarian_example']}")
                    print(f"    English Example: {example_data['english_example']}")
                    
                    if not dry_run:
                        try:
                            self.anki.update_note_fields(note_id, update_fields)
                            updated_count += 1
                        except Exception as e:
                            print(f"    Error updating note {note_id}: {e}")
                            skipped_count += 1
                    else:
                        updated_count += 1
                else:
                    skipped_count += 1
            else:
                print(f"  No examples found for: {front_text}")
                skipped_count += 1
        
        return updated_count, matched_count, skipped_count
    
    def run(self, dry_run: bool = False):
        """Main execution method"""
        print("=" * 60)
        print("ANKI EXAMPLES UPDATER")
        print("=" * 60)
        
        try:
            # Load examples from TSV
            self.load_examples_from_tsv()
            
            # Check if deck exists
            if not self.check_deck_exists():
                raise Exception(f"Deck '{self.deck_name}' not found. Available decks: {self.anki.get_deck_names()}")
            
            # Get notes from deck
            notes = self.get_notes_from_deck()
            
            # Ensure example fields exist in the note type
            self.ensure_example_fields_exist(notes)
            
            # Match and update notes
            updated, matched, skipped = self.match_and_update_notes(notes, dry_run)
            
            # Summary
            print("\n" + "=" * 60)
            print("SUMMARY")
            print("=" * 60)
            print(f"Total notes in deck: {len(notes)}")
            print(f"Notes matched with examples: {matched}")
            print(f"Notes {'would be ' if dry_run else ''}updated: {updated}")
            print(f"Notes skipped: {skipped}")
            
            if dry_run:
                print("\nThis was a DRY RUN. No changes were made.")
                print("Run again with --execute to make actual changes.")
            else:
                print(f"\n✓ Successfully updated {updated} notes!")
            
        except Exception as e:
            print(f"Error: {e}")
            return False
        
        return True


def main():
    """Main function with command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Add Bulgarian and English examples to Anki cards from TSV file"
    )
    parser.add_argument(
        "--tsv-file", 
        default="bulgarian_words_1000_v2.tsv",
        help="Path to TSV file with examples (default: bulgarian_words_1000_v2.tsv)"
    )
    parser.add_argument(
        "--deck-name",
        default="Rees-Bulgarian-Vocab", 
        help="Name of Anki deck to update (default: Rees-Bulgarian-Vocab)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes"
    )
    parser.add_argument(
        "--execute",
        action="store_true", 
        help="Actually make the changes (default is dry run)"
    )
    
    args = parser.parse_args()
    
    # Default to dry run unless --execute is specified
    dry_run = not args.execute
    
    updater = ExampleUpdater(args.tsv_file, args.deck_name)
    success = updater.run(dry_run=dry_run)
    
    if success and dry_run:
        print("\nTo execute the changes, run:")
        print(f"python {__file__} --execute")


if __name__ == "__main__":
    main() 