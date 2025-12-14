"""
Image service for Anki cards with API integration and caching.

Supports:
- Unsplash API
- Pexels API  
- Pixabay API
- Local image uploads
- 7-day cache with 500MB LRU management
"""
import hashlib
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx
from loguru import logger

from open_notebook.config import UPLOADS_FOLDER
from open_notebook.domain.anki import ImageCache, ImageMetadata


class ImageService:
    """Service for fetching and caching images from external APIs."""

    def __init__(self):
        logger.info("Initializing Image service")
        self.cache_dir = Path(UPLOADS_FOLDER) / "anki_data" / "images" / "cache"
        self.uploads_dir = Path(UPLOADS_FOLDER) / "anki_data" / "images" / "uploads"
        
        # Ensure directories exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        
        # API keys (will be loaded from environment)
        self.unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY")
        self.pexels_key = os.getenv("PEXELS_API_KEY")
        self.pixabay_key = os.getenv("PIXABAY_API_KEY")
        
        # Cache settings
        self.max_cache_size = 500 * 1024 * 1024  # 500MB
        self.cache_expiry_days = 7

    async def search_image(
        self,
        query: str,
        provider: str = "unsplash",
    ) -> Optional[ImageMetadata]:
        """
        Search for an image from external API.
        
        Args:
            query: Search query
            provider: "unsplash", "pexels", or "pixabay"
        
        Returns:
            ImageMetadata with attribution and cached path, or None if not found
        """
        try:
            # Check cache first
            cache_key = self._generate_cache_key(query, provider)
            cached_entry = await ImageCache.get_by_url(cache_key)
            
            if cached_entry and not self._is_expired(cached_entry):
                logger.info(f"Using cached image for query: {query}")
                return ImageMetadata(
                    url=cached_entry.url,
                    source=cached_entry.source,
                    attribution_text=cached_entry.attribution,
                    cached_path=cached_entry.cached_path,
                    cache_expiry=cached_entry.expires_at,
                )
            
            # Fetch from API
            if provider == "unsplash":
                return await self._search_unsplash(query)
            elif provider == "pexels":
                return await self._search_pexels(query)
            elif provider == "pixabay":
                return await self._search_pixabay(query)
            else:
                logger.warning(f"Unknown provider: {provider}")
                return None
                
        except Exception as e:
            logger.error(f"Error searching image: {str(e)}")
            return None

    async def _search_unsplash(self, query: str) -> Optional[ImageMetadata]:
        """Search Unsplash for images."""
        if not self.unsplash_key:
            logger.warning("Unsplash API key not configured")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.unsplash.com/search/photos",
                    params={"query": query, "per_page": 1},
                    headers={"Authorization": f"Client-ID {self.unsplash_key}"},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                
                if not data.get("results"):
                    logger.warning(f"No Unsplash results for: {query}")
                    return None
                
                photo = data["results"][0]
                image_url = photo["urls"]["regular"]
                attribution = f"Photo by {photo['user']['name']} on Unsplash"
                
                # Download and cache
                cached_path = await self._download_and_cache(
                    image_url=image_url,
                    query=query,
                    provider="unsplash",
                    attribution=attribution,
                )
                
                if not cached_path:
                    return None
                
                return ImageMetadata(
                    url=image_url,
                    source="unsplash",
                    license="Unsplash License",
                    attribution_text=attribution,
                    cached_path=cached_path,
                    cache_expiry=datetime.utcnow() + timedelta(days=self.cache_expiry_days),
                )
                
        except Exception as e:
            logger.error(f"Error searching Unsplash: {str(e)}")
            return None

    async def _search_pexels(self, query: str) -> Optional[ImageMetadata]:
        """Search Pexels for images."""
        if not self.pexels_key:
            logger.warning("Pexels API key not configured")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.pexels.com/v1/search",
                    params={"query": query, "per_page": 1},
                    headers={"Authorization": self.pexels_key},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                
                if not data.get("photos"):
                    logger.warning(f"No Pexels results for: {query}")
                    return None
                
                photo = data["photos"][0]
                image_url = photo["src"]["large"]
                attribution = f"Photo by {photo['photographer']} on Pexels"
                
                # Download and cache
                cached_path = await self._download_and_cache(
                    image_url=image_url,
                    query=query,
                    provider="pexels",
                    attribution=attribution,
                )
                
                if not cached_path:
                    return None
                
                return ImageMetadata(
                    url=image_url,
                    source="pexels",
                    license="Pexels License",
                    attribution_text=attribution,
                    cached_path=cached_path,
                    cache_expiry=datetime.utcnow() + timedelta(days=self.cache_expiry_days),
                )
                
        except Exception as e:
            logger.error(f"Error searching Pexels: {str(e)}")
            return None

    async def _search_pixabay(self, query: str) -> Optional[ImageMetadata]:
        """Search Pixabay for images."""
        if not self.pixabay_key:
            logger.warning("Pixabay API key not configured")
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://pixabay.com/api/",
                    params={"key": self.pixabay_key, "q": query, "per_page": 3, "image_type": "photo"},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                
                if not data.get("hits"):
                    logger.warning(f"No Pixabay results for: {query}")
                    return None
                
                photo = data["hits"][0]
                image_url = photo["largeImageURL"]
                attribution = f"Image by {photo['user']} from Pixabay"
                
                # Download and cache
                cached_path = await self._download_and_cache(
                    image_url=image_url,
                    query=query,
                    provider="pixabay",
                    attribution=attribution,
                )
                
                if not cached_path:
                    return None
                
                return ImageMetadata(
                    url=image_url,
                    source="pixabay",
                    license="Pixabay License",
                    attribution_text=attribution,
                    cached_path=cached_path,
                    cache_expiry=datetime.utcnow() + timedelta(days=self.cache_expiry_days),
                )
                
        except Exception as e:
            logger.error(f"Error searching Pixabay: {str(e)}")
            return None

    async def _download_and_cache(
        self,
        image_url: str,
        query: str,
        provider: str,
        attribution: str,
    ) -> Optional[str]:
        """Download image and save to cache."""
        try:
            # Generate cache filename
            cache_key = self._generate_cache_key(query, provider)
            filename = hashlib.md5(cache_key.encode()).hexdigest() + ".jpg"
            cached_path = self.cache_dir / filename
            
            # Download image
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url, timeout=30.0)
                response.raise_for_status()
                
                # Save to cache
                cached_path.write_bytes(response.content)
                file_size = cached_path.stat().st_size
                
                # Store in database
                cache_entry = ImageCache(
                    url=cache_key,  # Use cache_key as unique identifier
                    cached_path=str(cached_path),
                    source=provider,
                    attribution=attribution,
                    file_size=file_size,
                    expires_at=datetime.utcnow() + timedelta(days=self.cache_expiry_days),
                )
                await cache_entry.save()
                
                # Check cache size and cleanup if needed
                await ImageCache.cleanup_lru(self.max_cache_size)
                
                logger.info(f"Cached image: {cached_path} ({file_size} bytes)")
                return str(cached_path)
                
        except Exception as e:
            logger.error(f"Error downloading and caching image: {str(e)}")
            return None

    def save_uploaded_image(self, file_content: bytes, filename: str) -> Optional[str]:
        """
        Save uploaded image to uploads directory.
        
        Args:
            file_content: Image file bytes
            filename: Original filename
        
        Returns:
            Path to saved file, or None on error
        """
        try:
            # Generate safe filename
            safe_filename = self._sanitize_filename(filename)
            upload_path = self.uploads_dir / safe_filename
            
            # Save file
            upload_path.write_bytes(file_content)
            
            logger.info(f"Saved uploaded image: {upload_path}")
            return str(upload_path)
            
        except Exception as e:
            logger.error(f"Error saving uploaded image: {str(e)}")
            return None

    async def cleanup_expired_cache(self):
        """Remove expired cache entries."""
        try:
            expired = await ImageCache.get_expired_entries()
            
            for entry in expired:
                # Delete file
                try:
                    path = Path(entry.cached_path)
                    if path.exists():
                        path.unlink()
                except Exception as e:
                    logger.warning(f"Error deleting cached file {entry.cached_path}: {str(e)}")
                
                # Delete database entry
                await entry.delete()
            
            if expired:
                logger.info(f"Cleaned up {len(expired)} expired cache entries")
                
        except Exception as e:
            logger.error(f"Error cleaning up expired cache: {str(e)}")

    def _generate_cache_key(self, query: str, provider: str) -> str:
        """Generate unique cache key for query and provider."""
        return f"{provider}:{query.lower().strip()}"

    def _is_expired(self, cache_entry: ImageCache) -> bool:
        """Check if cache entry is expired."""
        return datetime.utcnow() > cache_entry.expires_at

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe filesystem storage."""
        # Remove path components
        filename = os.path.basename(filename)
        
        # Generate timestamp prefix for uniqueness
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        return f"{timestamp}_{filename}"


# Global service instance
image_service = ImageService()
