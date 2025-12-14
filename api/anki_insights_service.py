"""
Service for converting transformation insights into Anki cards.
"""
import json
import re
from typing import List, Dict, Optional
from loguru import logger

from open_notebook.domain.notebook import SourceInsight
from open_notebook.database.repository import repo_query


class AnkiInsightsService:
    """Service for parsing and converting Anki card insights."""
    
    ANKI_TRANSFORMATION_PATTERNS = [
        r"anki[_\s]",  # Matches "anki_" or "anki "
        r"flashcard",
        r"card[s]?\s*-\s*dutch",
    ]
    
    @staticmethod
    def is_anki_insight(insight_type: str) -> bool:
        """Check if an insight is an Anki card generation insight."""
        insight_lower = insight_type.lower()
        return any(re.search(pattern, insight_lower, re.IGNORECASE) 
                  for pattern in AnkiInsightsService.ANKI_TRANSFORMATION_PATTERNS)
    
    @staticmethod
    def parse_cards_from_insight(content: str) -> List[Dict]:
        """
        Parse Anki cards from insight content.
        
        Expects JSON array format:
        [
          {
            "front": "...",
            "back": "...",
            "notes": "...",
            "suggested_tags": [...]
          }
        ]
        
        Returns list of card dictionaries or empty list if parsing fails.
        """
        try:
            # Try direct JSON parse
            cards = json.loads(content)
            if isinstance(cards, list):
                return cards
            elif isinstance(cards, dict):
                return [cards]
            else:
                logger.warning(f"Unexpected JSON structure: {type(cards)}")
                return []
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```json\s*(\[.*?\])\s*```', content, re.DOTALL)
            if json_match:
                try:
                    cards = json.loads(json_match.group(1))
                    if isinstance(cards, list):
                        return cards
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON from code block: {e}")
            
            # Try to find JSON array anywhere in the content
            json_match = re.search(r'\[[\s\S]*?\{[\s\S]*?"front"[\s\S]*?\}[\s\S]*?\]', content)
            if json_match:
                try:
                    cards = json.loads(json_match.group(0))
                    if isinstance(cards, list):
                        return cards
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse extracted JSON: {e}")
            
            logger.error(f"Could not parse cards from insight content")
            return []
    
    @staticmethod
    async def get_anki_insights_for_source(source_id: str) -> List[tuple[SourceInsight, List[Dict]]]:
        """
        Get all Anki card insights for a source with parsed cards.
        
        Returns list of (insight, cards) tuples.
        """
        query = """
            SELECT * FROM source_insight 
            WHERE source = $source_id
            ORDER BY created DESC
        """
        results = await repo_query(query, {"source_id": source_id})
        
        anki_insights = []
        for row in results:
            insight = SourceInsight(**row)
            if AnkiInsightsService.is_anki_insight(insight.insight_type):
                cards = AnkiInsightsService.parse_cards_from_insight(insight.content)
                if cards:
                    anki_insights.append((insight, cards))
        
        return anki_insights
    
    @staticmethod
    async def get_anki_insights_for_notebook(notebook_id: str) -> List[tuple[SourceInsight, str, List[Dict]]]:
        """
        Get all Anki card insights for all sources in a notebook.
        
        Returns list of (insight, source_id, cards) tuples.
        """
        query = """
            SELECT 
                *,
                source AS source_id
            FROM source_insight
            WHERE source IN (
                SELECT value in FROM reference WHERE out = $notebook_id
            )
            ORDER BY created DESC
        """
        results = await repo_query(query, {"notebook_id": notebook_id})
        
        anki_insights = []
        for row in results:
            insight_data = {k: v for k, v in row.items() if k != 'source_id'}
            insight = SourceInsight(**insight_data)
            source_id = row.get('source_id')
            
            if AnkiInsightsService.is_anki_insight(insight.insight_type):
                cards = AnkiInsightsService.parse_cards_from_insight(insight.content)
                if cards:
                    anki_insights.append((insight, source_id, cards))
        
        return anki_insights


# Global service instance
anki_insights_service = AnkiInsightsService()
