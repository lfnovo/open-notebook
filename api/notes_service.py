"""
Notes service layer using API.
"""

from typing import List, Optional

from loguru import logger

from api.client import api_client
from open_notebook.domain.notebook import Note


class NotesService:
    """Service layer for notes operations using API."""
    
    def __init__(self):
        logger.info("Using API for notes operations")
    
    def get_all_notes(self, notebook_id: Optional[str] = None) -> List[Note]:
        """Get all notes with optional notebook filtering."""
        notes_data = api_client.get_notes(notebook_id=notebook_id)
        # Convert API response to Note objects
        notes = []
        for note_data in notes_data:
            note = Note(
                title=note_data["title"],
                content=note_data["content"],
                note_type=note_data["note_type"],
            )
            note.id = note_data["id"]
            note.created = note_data["created"]
            note.updated = note_data["updated"]
            notes.append(note)
        return notes
    
    def get_note(self, note_id: str) -> Note:
        """Get a specific note."""
        note_response = api_client.get_note(note_id)
        note_data = note_response if isinstance(note_response, dict) else note_response[0]
        note = Note(
            title=note_data["title"],
            content=note_data["content"],
            note_type=note_data["note_type"],
        )
        note.id = note_data["id"]
        note.created = note_data["created"]
        note.updated = note_data["updated"]
        return note
    
    def create_note(
        self,
        content: str,
        title: Optional[str] = None,
        note_type: str = "human",
        notebook_id: Optional[str] = None
    ) -> Note:
        """Create a new note."""
        note_response = api_client.create_note(
            content=content,
            title=title,
            note_type=note_type,
            notebook_id=notebook_id
        )
        note_data = note_response if isinstance(note_response, dict) else note_response[0]
        note = Note(
            title=note_data["title"],
            content=note_data["content"],
            note_type=note_data["note_type"],
        )
        note.id = note_data["id"]
        note.created = note_data["created"]
        note.updated = note_data["updated"]
        return note
    
    def update_note(self, note: Note) -> Note:
        """Update a note."""
        updates = {
            "title": note.title,
            "content": note.content,
            "note_type": note.note_type,
        }
        note_response = api_client.update_note(note.id or "", **updates)
        note_data = note_response if isinstance(note_response, dict) else note_response[0]

        # Update the note object with the response
        note.title = note_data["title"]
        note.content = note_data["content"]
        note.note_type = note_data["note_type"]
        note.updated = note_data["updated"]

        return note
    
    def delete_note(self, note_id: str) -> bool:
        """Delete a note."""
        api_client.delete_note(note_id)
        return True


# Global service instance
notes_service = NotesService()