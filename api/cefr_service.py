"""
CEFR classification service with multi-model voting and RAG integration.
"""
import json
from typing import Dict, List, Optional, Tuple

from ai_prompter import Prompter
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from open_notebook.database.repository import repo_query
from open_notebook.domain.anki import CEFRVote, DutchWordFrequency
from open_notebook.domain.models import model_manager
from open_notebook.graphs.utils import provision_langchain_model
from open_notebook.utils import clean_thinking_content


class CEFRService:
    """
    Service for CEFR level classification using multi-model voting.
    
    Uses 3 models:
    - 1 Dutch-native model (e.g., BramVanroy/fietje-2)
    - 2 multilingual models (e.g., GPT-4, Claude)
    
    Incorporates:
    - Word frequency from OpenSubtitles Dutch corpus
    - RAG context from sources tagged with #cefr-reference
    """

    def __init__(self):
        logger.info("Initializing CEFR service")
        self.voting_models = []  # Will be configured from settings

    async def classify_text(
        self,
        text: str,
        use_rag: bool = True,
        use_frequency: bool = True,
    ) -> Tuple[str, float, List[CEFRVote]]:
        """
        Classify Dutch text to CEFR level using multi-model voting.
        
        Args:
            text: Dutch text to classify
            use_rag: Whether to include context from #cefr-reference sources
            use_frequency: Whether to include word frequency data
        
        Returns:
            Tuple of (consensus_level, confidence, votes)
        """
        try:
            # Get word frequency data if requested
            word_frequency_info = None
            if use_frequency:
                word_frequency_info = await self._get_word_frequency_info(text)
            
            # Get RAG context if requested
            context_from_sources = None
            if use_rag:
                context_from_sources = await self._get_cefr_reference_context(text)
            
            # Get votes from multiple models
            votes = await self._collect_votes(
                text=text,
                word_frequency=word_frequency_info,
                context_from_sources=context_from_sources,
            )
            
            if not votes:
                logger.warning(f"No votes collected for text: {text[:50]}...")
                return "B1", 0.0, []
            
            # Calculate consensus
            consensus_level, confidence = self._calculate_consensus(votes)
            
            logger.info(f"CEFR classification: {consensus_level} (confidence: {confidence:.2f})")
            return consensus_level, confidence, votes
            
        except Exception as e:
            logger.error(f"Error classifying text: {str(e)}")
            # Return default B1 with low confidence on error
            return "B1", 0.0, []

    async def _get_word_frequency_info(self, text: str) -> Optional[str]:
        """Get word frequency information for words in text."""
        try:
            words = text.lower().split()
            frequency_data = []
            
            for word in words[:10]:  # Limit to first 10 words to avoid huge queries
                word_clean = word.strip(".,!?;:\"'")
                freq = await DutchWordFrequency.get_word_frequency(word_clean)
                if freq:
                    frequency_data.append(f"- '{word_clean}': rank {freq.rank}, frequency {freq.frequency}")
            
            if frequency_data:
                return "\n".join(frequency_data)
            return None
            
        except Exception as e:
            logger.warning(f"Error getting word frequency: {str(e)}")
            return None

    async def _get_cefr_reference_context(self, text: str) -> Optional[str]:
        """
        Get relevant context from sources tagged with #cefr-reference.
        
        This uses semantic search to find relevant passages from CEFR reference materials.
        """
        try:
            # Search for sources with #cefr-reference tag
            sources = await repo_query(
                """
                SELECT id, title, full_text 
                FROM source 
                WHERE 'cefr-reference' IN topics 
                OR 'cefr' IN topics
                LIMIT 5
                """
            )
            
            if not sources:
                return None
            
            # For now, return excerpts from reference sources
            # TODO: Implement semantic search to find most relevant passages
            context_parts = []
            for source in sources[:3]:  # Limit to 3 sources
                title = source.get("title", "Untitled")
                full_text = source.get("full_text", "")
                if full_text:
                    # Take first 500 characters as context
                    excerpt = full_text[:500] + "..." if len(full_text) > 500 else full_text
                    context_parts.append(f"**{title}**\n{excerpt}")
            
            return "\n\n".join(context_parts) if context_parts else None
            
        except Exception as e:
            logger.warning(f"Error getting CEFR reference context: {str(e)}")
            return None

    async def _collect_votes(
        self,
        text: str,
        word_frequency: Optional[str],
        context_from_sources: Optional[str],
    ) -> List[CEFRVote]:
        """Collect votes from multiple models."""
        votes = []
        
        # Get configured models for CEFR classification
        # For now, use chat models - in production, configure specific models
        try:
            defaults = await model_manager.get_defaults()
            
            # Model 1: Default chat model (multilingual)
            if defaults.default_chat_model:
                vote = await self._get_model_vote(
                    model_id=defaults.default_chat_model,
                    text=text,
                    word_frequency=word_frequency,
                    context_from_sources=context_from_sources,
                )
                if vote:
                    votes.append(vote)
            
            # Model 2: Large context model (multilingual)
            if defaults.large_context_model and defaults.large_context_model != defaults.default_chat_model:
                vote = await self._get_model_vote(
                    model_id=defaults.large_context_model,
                    text=text,
                    word_frequency=word_frequency,
                    context_from_sources=context_from_sources,
                )
                if vote:
                    votes.append(vote)
            
            # Model 3: Transformation model (could be Dutch-native)
            if defaults.default_transformation_model and defaults.default_transformation_model not in [
                defaults.default_chat_model,
                defaults.large_context_model,
            ]:
                vote = await self._get_model_vote(
                    model_id=defaults.default_transformation_model,
                    text=text,
                    word_frequency=word_frequency,
                    context_from_sources=context_from_sources,
                )
                if vote:
                    votes.append(vote)
            
            logger.info(f"Collected {len(votes)} votes for CEFR classification")
            return votes
            
        except Exception as e:
            logger.error(f"Error collecting votes: {str(e)}")
            return []

    async def _get_model_vote(
        self,
        model_id: str,
        text: str,
        word_frequency: Optional[str],
        context_from_sources: Optional[str],
    ) -> Optional[CEFRVote]:
        """Get a single model's vote on CEFR classification."""
        try:
            # Render the prompt template
            prompt_data = {
                "text": text,
                "word_frequency": word_frequency,
                "context_from_sources": context_from_sources,
            }
            
            system_prompt = Prompter(prompt_template="anki/cefr_classification").render(
                data=prompt_data
            )
            
            # Get model response
            chain = await provision_langchain_model(
                system_prompt,
                model_id,
                "language",
                max_tokens=1000,
                temperature=0.1,  # Low temperature for consistency
            )
            
            payload = [
                SystemMessage(content=system_prompt),
                HumanMessage(content="Analyze and classify the text."),
            ]
            
            response = await chain.ainvoke(payload)
            response_content = clean_thinking_content(
                response.content if isinstance(response.content, str) else str(response.content)
            )
            
            # Parse JSON response
            result = json.loads(response_content)
            
            vote = CEFRVote(
                model_id=model_id,
                level=result["level"].upper(),
                confidence=float(result["confidence"]),
                reasoning=result.get("reasoning"),
            )
            
            logger.info(f"Model {model_id} voted: {vote.level} (confidence: {vote.confidence:.2f})")
            return vote
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing model response as JSON for {model_id}: {str(e)}")
            logger.error(f"Response was: {response_content[:200]}")
            return None
        except Exception as e:
            logger.error(f"Error getting vote from model {model_id}: {str(e)}")
            return None

    def _calculate_consensus(self, votes: List[CEFRVote]) -> Tuple[str, float]:
        """
        Calculate consensus CEFR level from votes.
        
        Uses weighted voting where confidence scores are the weights.
        Returns the most common level and average confidence.
        """
        if not votes:
            return "B1", 0.0
        
        # Count weighted votes
        level_weights: Dict[str, float] = {}
        for vote in votes:
            level_weights[vote.level] = level_weights.get(vote.level, 0.0) + vote.confidence
        
        # Find consensus level (highest weight)
        consensus_level = max(level_weights.items(), key=lambda x: x[1])[0]
        
        # Calculate average confidence for consensus level
        consensus_votes = [v for v in votes if v.level == consensus_level]
        avg_confidence = sum(v.confidence for v in consensus_votes) / len(consensus_votes)
        
        # Adjust confidence based on agreement
        agreement_factor = len(consensus_votes) / len(votes)
        final_confidence = avg_confidence * agreement_factor
        
        return consensus_level, final_confidence


# Global service instance
cefr_service = CEFRService()
