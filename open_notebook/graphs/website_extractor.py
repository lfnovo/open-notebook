"""
Website Extractor Module

This module is responsible for extracting clean text content from websites using
BeautifulSoup for local HTML parsing instead of the Jina AI API.
"""

import html
import logging
import re
from typing import List
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from podcastfy.utils.config import load_config

logger = logging.getLogger(__name__)


class WebsiteExtractor:
    def __init__(self):
        """
        Initialize the WebsiteExtractor.
        """
        self.config = load_config()
        self.website_extractor_config = self.config.get("website_extractor", {})
        self.unwanted_tags = self.website_extractor_config.get("unwanted_tags", [])
        self.user_agent = self.website_extractor_config.get("user_agent", "Mozilla/5.0")
        self.timeout = self.website_extractor_config.get("timeout", 10)
        self.remove_patterns = self.website_extractor_config.get(
            "markdown_cleaning", {}
        ).get("remove_patterns", [])

    def extract_content(self, url: str) -> str:
        """
        Extract clean text content from a website using BeautifulSoup.

        Args:
                url (str): Website URL.

        Returns:
                str: Extracted clean text content.

        Raises:
                Exception: If there's an error in extracting the content.
        """
        try:
            # Normalize the URL
            normalized_url = self.normalize_url(url)

            # Request the webpage
            headers = {"User-Agent": self.user_agent}
            response = requests.get(
                normalized_url, headers=headers, timeout=self.timeout
            )
            response.raise_for_status()  # Raise an exception for bad status codes

            # Parse the page content with BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove unwanted elements
            self.remove_unwanted_elements(soup)

            # Extract and clean the text content
            raw_text = soup.get_text(separator="\n")  # Get all text content
            cleaned_content = self.clean_content(raw_text)

            return cleaned_content
        except requests.RequestException as e:
            logger.error(f"Failed to extract content from {url}: {str(e)}")
            raise Exception(f"Failed to extract content from {url}: {str(e)}")
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while extracting content from {url}: {str(e)}"
            )
            raise Exception(
                f"An unexpected error occurred while extracting content from {url}: {str(e)}"
            )

    def normalize_url(self, url: str) -> str:
        """
        Normalize the given URL by adding scheme if missing and ensuring it's a valid URL.

        Args:
                url (str): The URL to normalize.

        Returns:
                str: The normalized URL.

        Raises:
                ValueError: If the URL is invalid after normalization attempts.
        """
        # If the URL doesn't start with a scheme, add 'https://'
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        # Parse the URL
        parsed = urlparse(url)

        # Ensure the URL has a valid scheme and netloc
        if not all([parsed.scheme, parsed.netloc]):
            raise ValueError(f"Invalid URL: {url}")

        return parsed.geturl()

    def remove_unwanted_elements(self, soup: BeautifulSoup) -> None:
        """
        Remove unwanted elements from the BeautifulSoup object.

        Args:
                soup (BeautifulSoup): The BeautifulSoup object to clean.
        """
        for tag in self.unwanted_tags:
            for element in soup.find_all(tag):
                element.decompose()

    def clean_content(self, content: str) -> str:
        """
        Clean the extracted content by removing unnecessary whitespace and applying
        custom cleaning patterns.

        Args:
                content (str): The content to clean.

        Returns:
                str: Cleaned text content.
        """
        # Decode HTML entities
        cleaned_content = html.unescape(content)

        # Remove extra whitespace
        cleaned_content = re.sub(r"\s+", " ", cleaned_content)

        # Remove extra newlines
        cleaned_content = re.sub(r"\n{3,}", "\n\n", cleaned_content)

        # Apply custom cleaning patterns from config
        for pattern in self.remove_patterns:
            cleaned_content = re.sub(pattern, "", cleaned_content)

        return cleaned_content.strip()


def main(seed: int = 42) -> None:
    """
    Main function to test the WebsiteExtractor class.
    """
    logging.basicConfig(level=logging.INFO)

    # Create an instance of WebsiteExtractor
    extractor = WebsiteExtractor()

    # Test URLs
    test_urls: List[str] = [
        "www.souzatharsis.com",
        "https://en.wikipedia.org/wiki/Web_scraping",
    ]

    for url in test_urls:
        try:
            logger.info(f"Extracting content from: {url}")
            content = extractor.extract_content(url)

            # Print the first 500 characters of the extracted content
            logger.info(
                f"Extracted content (first 500 characters):\n{content[:500]}..."
            )

            # Print the total length of the extracted content
            logger.info(f"Total length of extracted content: {len(content)} characters")
            logger.info("-" * 50)

        except Exception as e:
            logger.error(f"An error occurred while processing {url}: {str(e)}")


if __name__ == "__main__":
    main()
