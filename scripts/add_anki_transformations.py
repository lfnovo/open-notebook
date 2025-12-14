#!/usr/bin/env python3
"""
Script to add Anki card generation transformations to the database.
Run this from within the open_notebook container.
"""
import asyncio
from open_notebook.database.repository import repo_query

async def add_anki_transformations():
    """Add Anki card generation transformations for Dutch CEFR levels."""
    
    transformations = [
        {
            "id": "transformation:anki_dutch_a2",
            "name": "anki_dutch_a2",
            "title": "Anki Cards - Dutch A2",
            "description": "Generate vocabulary flashcards for A2 (Elementary) level Dutch learners. Focuses on common everyday vocabulary with simple tenses and basic phrases.",
            "prompt": "anki_transformation_dutch_a2",
            "apply_default": False
        },
        {
            "id": "transformation:anki_dutch_b1",
            "name": "anki_dutch_b1",
            "title": "Anki Cards - Dutch B1",
            "description": "Generate vocabulary flashcards for B1 (Intermediate) level Dutch learners. Includes workplace vocabulary, complex tenses, and idiomatic expressions.",
            "prompt": "anki_transformation_dutch_b1",
            "apply_default": False
        },
        {
            "id": "transformation:anki_dutch_b2",
            "name": "anki_dutch_b2",
            "title": "Anki Cards - Dutch B2",
            "description": "Generate vocabulary flashcards for B2 (Upper Intermediate) level Dutch learners. Covers abstract concepts, formal language, and professional vocabulary.",
            "prompt": "anki_transformation_dutch_b2",
            "apply_default": False
        },
        {
            "id": "transformation:anki_dutch_c1",
            "name": "anki_dutch_c1",
            "title": "Anki Cards - Dutch C1",
            "description": "Generate vocabulary flashcards for C1 (Advanced) level Dutch learners. Focuses on specialized terminology, literary language, and advanced discourse.",
            "prompt": "anki_transformation_dutch_c1",
            "apply_default": False
        },
        {
            "id": "transformation:anki_dutch_c2",
            "name": "anki_dutch_c2",
            "title": "Anki Cards - Dutch C2",
            "description": "Generate vocabulary flashcards for C2 (Proficiency) level Dutch learners. Includes rare vocabulary, archaic forms, regional variations, and highly specialized terminology.",
            "prompt": "anki_transformation_dutch_c2",
            "apply_default": False
        }
    ]
    
    for trans_data in transformations:
        trans_id = trans_data["id"]
        
        try:
            # Use direct query to create transformation
            query = f"""
                CREATE {trans_id} CONTENT {{
                    name: $name,
                    title: $title,
                    description: $description,
                    prompt: $prompt,
                    apply_default: $apply_default,
                    created: time::now(),
                    updated: time::now()
                }}
            """
            result = await repo_query(query, {
                "name": trans_data["name"],
                "title": trans_data["title"],
                "description": trans_data["description"],
                "prompt": trans_data["prompt"],
                "apply_default": trans_data["apply_default"]
            })
            print(f"✓ Created transformation: {trans_data['title']} ({trans_id})")
        except Exception as e:
            print(f"✗ Failed to create {trans_data['title']}: {e}")
    
    print(f"\nSuccessfully added {len(transformations)} Anki card generation transformations!")

if __name__ == "__main__":
    asyncio.run(add_anki_transformations())
