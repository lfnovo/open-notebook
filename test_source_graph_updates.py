#!/usr/bin/env python3
"""
Test script to verify the updated source graph functionality.
This script demonstrates the new multi-notebook support and source update functionality.
"""

import asyncio
from typing import List
from content_core.common import ProcessSourceState
from open_notebook.graphs.source import SourceState, source_graph
from open_notebook.domain.notebook import Source, Notebook
from open_notebook.domain.transformation import Transformation


async def test_source_graph_update():
    """Test the updated source graph with multi-notebook support"""
    
    print("Testing updated source graph functionality...")
    
    # Mock data for testing
    # First, create a source to update
    test_source = Source(
        title="Original Title",
        full_text="Original content here"
    )
    await test_source.save()
    print(f"Created test source with ID: {test_source.id}")
    
    # Create test notebooks
    notebooks = []
    for i in range(2):
        notebook = Notebook(
            name=f"Test Notebook {i+1}",
            description=f"Test notebook {i+1} for source graph testing"
        )
        await notebook.save()
        notebooks.append(notebook)
        print(f"Created notebook {i+1} with ID: {notebook.id}")
    
    # Create mock content state
    content_state = ProcessSourceState(
        content="Updated content after processing",
        title="Updated Title",
        url="https://example.com/test",
        file_path=None
    )
    
    # Create test state with new structure
    state: SourceState = {
        "content_state": content_state,
        "apply_transformations": [],  # No transformations for this test
        "source_id": test_source.id,
        "notebook_ids": [notebook.id for notebook in notebooks],
        "source": test_source,
        "transformation": [],
        "embed": False  # Skip embedding for this test
    }
    
    print("Running source graph with updated parameters...")
    
    try:
        # Execute the graph
        result = await source_graph.ainvoke(state)
        
        print("Graph execution completed successfully!")
        print(f"Updated source ID: {result['source'].id}")
        print(f"Updated source title: {result['source'].title}")
        print(f"Updated source content length: {len(result['source'].full_text or '')}")
        
        # Verify the source was updated correctly
        updated_source = await Source.get(test_source.id)
        assert updated_source.title == "Updated Title"
        assert updated_source.full_text == "Updated content after processing"
        
        print("✓ Source update verification passed")
        
        # Verify notebook associations
        for i, notebook in enumerate(notebooks):
            sources = await notebook.get_sources()
            source_ids = [s.id for s in sources]
            assert test_source.id in source_ids
            print(f"✓ Source correctly associated with notebook {i+1}")
        
        print("\n✅ All tests passed! The source graph updates work correctly.")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        raise
    
    finally:
        # Clean up test data
        print("\nCleaning up test data...")
        try:
            await test_source.delete()
            for notebook in notebooks:
                await notebook.delete()
            print("✓ Test data cleaned up")
        except Exception as e:
            print(f"Warning: Failed to clean up test data: {e}")


async def test_empty_notebook_ids():
    """Test handling of empty/None notebook IDs"""
    
    print("\nTesting empty notebook IDs handling...")
    
    # Create a test source
    test_source = Source(
        title="Test Source",
        full_text="Test content"
    )
    await test_source.save()
    
    content_state = ProcessSourceState(
        content="Updated content",
        title="Updated Title",
        url="https://example.com/test",
        file_path=None
    )
    
    # Test with empty list
    state: SourceState = {
        "content_state": content_state,
        "apply_transformations": [],
        "source_id": test_source.id,
        "notebook_ids": [],  # Empty list
        "source": test_source,
        "transformation": [],
        "embed": False
    }
    
    try:
        result = await source_graph.ainvoke(state)
        print("✓ Empty notebook_ids list handled correctly")
        
        # Test with list containing None values
        state["notebook_ids"] = [None, "", "  "]  # Various empty values
        result = await source_graph.ainvoke(state)
        print("✓ Notebook IDs with None/empty values handled correctly")
        
    except Exception as e:
        print(f"❌ Empty notebook IDs test failed: {str(e)}")
        raise
    
    finally:
        await test_source.delete()
        print("✓ Test cleanup completed")


if __name__ == "__main__":
    asyncio.run(test_source_graph_update())
    asyncio.run(test_empty_notebook_ids())