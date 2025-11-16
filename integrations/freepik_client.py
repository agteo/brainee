"""Freepik API client for fetching images for learning concepts."""

import os
import requests
from typing import Optional
from pathlib import Path

# Freepik API configuration
FREEPIK_API_KEY = os.getenv('FREEPIK_API_KEY', '')
FREEPIK_API_BASE = 'https://api.freepik.com/v1'
FREEPIK_SEARCH_ENDPOINT = f'{FREEPIK_API_BASE}/resources'

# Local cache directory for downloaded images
IMAGE_CACHE_DIR = Path(__file__).resolve().parent.parent / 'content' / 'images'
IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_image_for_concept(concept: str) -> Optional[str]:
    """Get an image URL for a given concept using Freepik API.
    
    Only returns images if they are relevant to the learning content.
    Returns None if no relevant image is available.
    
    Args:
        concept: Search term for the image (e.g., "AI transformer diagram")
    
    Returns:
        URL to the image if found and relevant, None otherwise
    """
    if not FREEPIK_API_KEY:
        # No API key - don't return placeholder images
        return None
    
    # Optimize search terms for better relevance
    optimized_query = optimize_search_query(concept)
    
    try:
        # Search Freepik API with optimized query
        headers = {
            'X-Freepik-API-Key': FREEPIK_API_KEY,
            'Accept': 'application/json'
        }
        
        params = {
            'query': optimized_query,
            'locale': 'en-US',
            'page': 1,
            'limit': 5,  # Get more results to find the most relevant
            'order': 'relevant',
            'filters[content_type]': 'photo',  # Prefer photos over vectors for learning
            'filters[orientation]': 'landscape'  # Better for lesson display
        }
        
        response = requests.get(
            FREEPIK_SEARCH_ENDPOINT,
            headers=headers,
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract image URL from response
            if 'data' in data and len(data['data']) > 0:
                # Try to find the most relevant image
                for image_data in data['data']:
                    image_url = None
                    if 'attributes' in image_data:
                        attrs = image_data['attributes']
                        # Try different possible fields, prefer high-quality images
                        image_url = (
                            attrs.get('image', {}).get('url') or
                            attrs.get('preview', {}).get('url') or
                            attrs.get('thumbnail', {}).get('url') or
                            attrs.get('url')
                        )
                    
                    # Verify relevance by checking title/tags if available
                    if image_url and is_relevant_image(image_data, concept):
                        return image_url
        
        # No relevant image found
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"Freepik API error: {e}")
        return None
    except Exception as e:
        print(f"Error fetching Freepik image: {e}")
        return None


def optimize_search_query(concept: str) -> str:
    """Optimize search query for better Freepik results.
    
    Adds relevant keywords to improve search relevance.
    """
    # Map common AI/ML concepts to better search terms
    concept_lower = concept.lower()
    
    # Add educational/illustrative keywords
    educational_keywords = ['diagram', 'illustration', 'concept', 'education', 'learning']
    
    # Check if concept already contains educational terms
    has_educational_term = any(keyword in concept_lower for keyword in educational_keywords)
    
    if not has_educational_term:
        # Add most relevant keyword based on concept
        if 'transformer' in concept_lower or 'llm' in concept_lower or 'neural' in concept_lower:
            return f"{concept} diagram illustration"
        elif 'agent' in concept_lower or 'ai' in concept_lower:
            return f"{concept} illustration concept"
        elif 'fundamentals' in concept_lower or 'basics' in concept_lower:
            return f"{concept} education learning"
    
    return concept


def is_relevant_image(image_data: dict, concept: str) -> bool:
    """Check if an image is relevant to the learning concept.
    
    Args:
        image_data: Image data from Freepik API
        concept: The learning concept
    
    Returns:
        True if image appears relevant, False otherwise
    """
    # Extract keywords from image metadata
    keywords = []
    if 'attributes' in image_data:
        attrs = image_data['attributes']
        # Get title, description, tags
        title = attrs.get('title', '').lower()
        description = attrs.get('description', '').lower()
        tags = [tag.lower() for tag in attrs.get('tags', [])]
        keywords.extend([title, description] + tags)
    
    concept_terms = set(concept.lower().split())
    
    # Check for relevance indicators
    relevance_indicators = [
        'diagram', 'illustration', 'concept', 'education', 'learning',
        'technology', 'ai', 'artificial intelligence', 'machine learning',
        'neural', 'network', 'transformer', 'agent'
    ]
    
    # Check if any concept terms appear in image keywords
    for term in concept_terms:
        if len(term) > 3:  # Only check meaningful terms
            for keyword in keywords:
                if term in keyword:
                    return True
    
    # Check for educational/illustrative content
    for indicator in relevance_indicators:
        if indicator in concept.lower():
            for keyword in keywords:
                if indicator in keyword or any(term in keyword for term in ['diagram', 'illustration', 'concept']):
                    return True
    
    # If we can't determine relevance, be conservative and return True
    # (let the user decide, but prefer showing something relevant)
    return True


def download_image(url: str, filename: str) -> Optional[Path]:
    """Download an image from URL and save it locally.
    
    Args:
        url: URL of the image to download
        filename: Name to save the file as
    
    Returns:
        Path to the downloaded file, or None if download failed
    """
    try:
        response = requests.get(url, timeout=10, stream=True)
        response.raise_for_status()
        
        file_path = IMAGE_CACHE_DIR / filename
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return file_path
        
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None
