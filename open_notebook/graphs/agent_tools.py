"""
Agent Tools for Open Notebook
Provides a set of tools that the Agent can use to interact with the knowledge base.
"""

from datetime import datetime
from typing import List, Optional

from langchain.tools import tool
from loguru import logger
from pydantic import BaseModel, Field


# Tool Input Schemas
class SearchInput(BaseModel):
    """Input schema for search_knowledge_base tool."""
    query: str = Field(description="The search query to find relevant content")
    search_type: str = Field(
        default="vector",
        description="Search type: 'vector' for semantic search, 'text' for keyword search"
    )
    limit: int = Field(default=5, description="Maximum number of results to return")
    include_sources: bool = Field(default=True, description="Include sources in search")
    include_notes: bool = Field(default=True, description="Include notes in search")


class SourceInput(BaseModel):
    """Input schema for source-related tools."""
    source_id: str = Field(description="The ID of the source (e.g., 'source:abc123')")


class CreateNoteInput(BaseModel):
    """Input schema for create_note tool."""
    title: str = Field(description="Title of the note")
    content: str = Field(description="Content of the note in markdown format")
    notebook_id: Optional[str] = Field(
        default=None,
        description="Optional notebook ID to add the note to"
    )


class UpdateNoteInput(BaseModel):
    """Input schema for update_note tool."""
    note_id: str = Field(description="The ID of the note to update")
    content: str = Field(description="New content for the note")
    title: Optional[str] = Field(default=None, description="Optional new title")


class TransformationInput(BaseModel):
    """Input schema for run_transformation tool."""
    source_id: str = Field(description="The ID of the source to transform")
    transformation_type: str = Field(
        description="Type of transformation: 'summary', 'key_points', 'questions', 'translate'"
    )


# Tool Implementations
@tool(args_schema=SearchInput)
async def search_knowledge_base(
    query: str,
    search_type: str = "vector",
    limit: int = 5,
    include_sources: bool = True,
    include_notes: bool = True
) -> str:
    """
    Search the knowledge base for relevant content.
    
    Use this tool when you need to find information from the user's sources and notes.
    Returns a list of matching documents with their IDs, titles, and content snippets.
    """
    from open_notebook.domain.notebook import vector_search, text_search
    
    try:
        if search_type == "vector":
            results = await vector_search(
                query, 
                limit, 
                source=include_sources, 
                note=include_notes
            )
        else:
            results = await text_search(
                query, 
                limit, 
                source=include_sources, 
                note=include_notes
            )
        
        if not results:
            return f"No results found for query: '{query}'"
        
        # Format results for the agent
        formatted_results = []
        for r in results:
            item = {
                "id": r.get("id", "unknown"),
                "title": r.get("title", "Untitled"),
                "type": "source" if "source:" in str(r.get("id", "")) else "note",
                "snippet": (r.get("content", "") or r.get("full_text", ""))[:200] + "..."
            }
            formatted_results.append(
                f"- [{item['type'].upper()}] {item['id']}: {item['title']}\n  {item['snippet']}"
            )
        
        return f"Found {len(results)} results:\n" + "\n\n".join(formatted_results)
    
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return f"Search failed: {str(e)}"


@tool(args_schema=SourceInput)
async def get_source_content(source_id: str) -> str:
    """
    Get the full content of a specific source.
    
    Use this when you need to read the complete text of a source document.
    The source_id should be in the format 'source:abc123'.
    """
    from open_notebook.domain.notebook import Source
    
    try:
        source = await Source.get(source_id)
        if not source:
            return f"Source not found: {source_id}"
        
        content = source.full_text or "No content available"
        title = source.title or "Untitled"
        
        # Truncate if too long
        if len(content) > 10000:
            content = content[:10000] + "\n\n[Content truncated due to length]"
        
        return f"# {title}\n\nSource ID: {source_id}\n\n{content}"
    
    except Exception as e:
        logger.error(f"Failed to get source content: {e}")
        return f"Failed to get source: {str(e)}"


@tool(args_schema=SourceInput)
async def get_source_insights(source_id: str) -> str:
    """
    Get all insights (summaries, key points, etc.) for a specific source.
    
    Use this to get pre-generated analysis of a source without reading the full content.
    """
    from open_notebook.domain.notebook import Source
    
    try:
        source = await Source.get(source_id)
        if not source:
            return f"Source not found: {source_id}"
        
        insights = await source.get_insights()
        if not insights:
            return f"No insights available for source: {source_id}"
        
        formatted_insights = []
        for insight in insights:
            formatted_insights.append(
                f"## {insight.insight_type}\n\n{insight.content}"
            )
        
        return f"# Insights for: {source.title or 'Untitled'}\n\n" + "\n\n---\n\n".join(formatted_insights)
    
    except Exception as e:
        logger.error(f"Failed to get insights: {e}")
        return f"Failed to get insights: {str(e)}"


@tool(args_schema=CreateNoteInput)
async def create_note(
    title: str,
    content: str,
    notebook_id: Optional[str] = None
) -> str:
    """
    Create a new note in the knowledge base.
    
    Use this to save research findings, summaries, or any other information.
    If notebook_id is provided, the note will be added to that notebook.
    """
    from open_notebook.domain.notebook import Note
    
    try:
        note = Note(
            title=title,
            content=content,
            note_type="ai"
        )
        await note.save()
        
        if notebook_id:
            await note.add_to_notebook(notebook_id)
            return f"Note created successfully!\nID: {note.id}\nTitle: {title}\nAdded to notebook: {notebook_id}"
        
        return f"Note created successfully!\nID: {note.id}\nTitle: {title}"
    
    except Exception as e:
        logger.error(f"Failed to create note: {e}")
        return f"Failed to create note: {str(e)}"


@tool(args_schema=UpdateNoteInput)
async def update_note(
    note_id: str,
    content: str,
    title: Optional[str] = None
) -> str:
    """
    Update an existing note.
    
    Use this to modify the content or title of an existing note.
    """
    from open_notebook.domain.notebook import Note
    
    try:
        note = await Note.get(note_id)
        if not note:
            return f"Note not found: {note_id}"
        
        note.content = content
        if title:
            note.title = title
        
        await note.save()
        return f"Note updated successfully!\nID: {note_id}\nTitle: {note.title}"
    
    except Exception as e:
        logger.error(f"Failed to update note: {e}")
        return f"Failed to update note: {str(e)}"


@tool
async def list_notebook_sources(notebook_id: str) -> str:
    """
    List all sources in a specific notebook.
    
    Use this to see what sources are available in a notebook before searching.
    """
    from open_notebook.domain.notebook import Notebook
    
    try:
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            return f"Notebook not found: {notebook_id}"
        
        sources = await notebook.get_sources()
        if not sources:
            return f"No sources in notebook: {notebook.name}"
        
        formatted_sources = []
        for src in sources:
            formatted_sources.append(
                f"- {src.id}: {src.title or 'Untitled'}"
            )
        
        return f"Sources in '{notebook.name}':\n" + "\n".join(formatted_sources)
    
    except Exception as e:
        logger.error(f"Failed to list sources: {e}")
        return f"Failed to list sources: {str(e)}"


@tool
async def list_notebook_notes(notebook_id: str) -> str:
    """
    List all notes in a specific notebook.
    
    Use this to see what notes exist in a notebook.
    """
    from open_notebook.domain.notebook import Notebook
    
    try:
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            return f"Notebook not found: {notebook_id}"
        
        notes = await notebook.get_notes()
        if not notes:
            return f"No notes in notebook: {notebook.name}"
        
        formatted_notes = []
        for note in notes:
            formatted_notes.append(
                f"- {note.id}: {note.title or 'Untitled'}"
            )
        
        return f"Notes in '{notebook.name}':\n" + "\n".join(formatted_notes)
    
    except Exception as e:
        logger.error(f"Failed to list notes: {e}")
        return f"Failed to list notes: {str(e)}"


@tool
def get_current_datetime() -> str:
    """
    Get the current date and time.
    
    Use this when you need to know the current time or date.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Tool registry for easy access
AGENT_TOOLS = [
    search_knowledge_base,
    get_source_content,
    get_source_insights,
    create_note,
    update_note,
    list_notebook_sources,
    list_notebook_notes,
    get_current_datetime,
]
