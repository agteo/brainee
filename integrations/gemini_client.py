"""Gemini API client for generating images and videos for learning content.

Uses Google's Gemini API to generate visual content (images/videos) 
to make learning more engaging and less text-heavy.
"""

import os
import requests
from typing import Dict, Optional, List
from pathlib import Path


class GeminiClient:
    """Client for Google Gemini API to generate visual learning content."""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.available = self.api_key is not None

    def is_available(self) -> bool:
        """Check if Gemini API is configured."""
        return self.available

    def generate_image(self, concept: str, module: str = None, style: str = "educational") -> Optional[str]:
        """Generate an image URL or description for a learning concept.
        
        Args:
            concept: The concept to visualize (e.g., "neural network", "transformer architecture")
            module: Optional module name for context
            style: Image style (educational, diagram, illustration, etc.)
            
        Returns:
            URL to generated image or None if unavailable
        """
        if not self.available:
            return None

        try:
            # For now, we'll use Gemini's image generation capabilities
            # Note: Gemini API may have different endpoints for image generation
            # This is a placeholder structure - adjust based on actual Gemini API
            
            prompt = f"Create an educational {style} image showing: {concept}"
            if module:
                prompt += f" for the {module} module"
            
            # Using Gemini's text-to-image or image search capabilities
            # Adjust this based on actual Gemini API documentation
            response = requests.post(
                f"{self.base_url}/models/gemini-pro-vision:generateContent",
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key
                },
                json={
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }]
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                # Extract image URL from response
                # Adjust based on actual API response structure
                if "candidates" in result and len(result["candidates"]) > 0:
                    # Return a placeholder or actual image URL
                    # For now, return a search-friendly description
                    return f"gemini://{concept.replace(' ', '_')}"
            
        except Exception as e:
            print(f"Gemini image generation error: {e}")
        
        return None

    def generate_video_description(self, concept: str, module: str = None) -> Optional[str]:
        """Generate a video description or URL for a learning concept.
        
        Args:
            concept: The concept to create video content for
            module: Optional module name for context
            
        Returns:
            Video URL or description, or None if unavailable
        """
        if not self.available:
            return None

        try:
            # Gemini can suggest video content or generate video descriptions
            prompt = f"Suggest an educational video about: {concept}"
            if module:
                prompt += f" for learning {module}"
            
            response = requests.post(
                f"{self.base_url}/models/gemini-pro:generateContent",
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key
                },
                json={
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }]
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if "candidates" in result and len(result["candidates"]) > 0:
                    content = result["candidates"][0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    return content
            
        except Exception as e:
            print(f"Gemini video generation error: {e}")
        
        return None

    def generate_mcq_question(self, topic: str, difficulty: int = 1, context: str = None) -> Optional[Dict]:
        """Generate a multiple-choice question using Gemini.
        
        Args:
            topic: The topic for the question
            difficulty: Difficulty level (0-3)
            context: Optional context from lesson content
            
        Returns:
            Dict with question, options, and correct_answer, or None
        """
        if not self.available:
            return None

        try:
            difficulty_labels = ["beginner", "intermediate", "advanced", "expert"]
            difficulty_label = difficulty_labels[min(difficulty, 3)]
            
            prompt = f"""Generate a {difficulty_label} level multiple-choice question about: {topic}

Format your response as:
QUESTION: [the question]
OPTIONS:
A) [option 1]
B) [option 2]
C) [option 3]
D) [option 4]
CORRECT: [A, B, C, or D]

Make the question clear and educational."""
            
            if context:
                prompt += f"\n\nContext: {context[:500]}"
            
            response = requests.post(
                f"{self.base_url}/models/gemini-pro:generateContent",
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key
                },
                json={
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }]
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if "candidates" in result and len(result["candidates"]) > 0:
                    content = result["candidates"][0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    
                    # Parse the response
                    question = ""
                    options = []
                    correct = None
                    
                    lines = content.split("\n")
                    current_section = None
                    
                    for line in lines:
                        line = line.strip()
                        if line.startswith("QUESTION:"):
                            question = line.replace("QUESTION:", "").strip()
                        elif line.startswith("OPTIONS:") or line.startswith("A)") or line.startswith("B)") or line.startswith("C)") or line.startswith("D)"):
                            if line.startswith("OPTIONS:"):
                                current_section = "options"
                            elif line and (line[0] in "ABCD" and ")" in line):
                                options.append(line.split(")", 1)[1].strip())
                        elif line.startswith("CORRECT:"):
                            correct_str = line.replace("CORRECT:", "").strip().upper()
                            if correct_str in "ABCD":
                                correct = "ABCD".index(correct_str)
                    
                    if question and len(options) >= 2 and correct is not None:
                        return {
                            "question": question,
                            "options": options,
                            "correct_answer": correct
                        }
            
        except Exception as e:
            print(f"Gemini MCQ generation error: {e}")
        
        return None

    def generate_open_ended_question(self, topic: str, difficulty: int = 1, context: str = None) -> Optional[Dict]:
        """Generate an open-ended question using Gemini.
        
        Args:
            topic: The topic for the question
            difficulty: Difficulty level (0-3)
            context: Optional context from lesson content
            
        Returns:
            Dict with question text, or None
        """
        if not self.available:
            return None

        try:
            difficulty_labels = ["beginner", "intermediate", "advanced", "expert"]
            difficulty_label = difficulty_labels[min(difficulty, 3)]
            
            prompt = f"""Generate a {difficulty_label} level open-ended question about: {topic}

The question should:
- Test the learner's understanding of key concepts
- Require a thoughtful explanation, not just a one-word answer
- Be clear and specific
- Encourage the learner to demonstrate their understanding

Format your response as:
QUESTION: [the question text]

Make the question educational and appropriate for assessing understanding."""
            
            if context:
                prompt += f"\n\nContext: {context[:500]}"
            
            response = requests.post(
                f"{self.base_url}/models/gemini-pro:generateContent",
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key
                },
                json={
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }]
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if "candidates" in result and len(result["candidates"]) > 0:
                    content = result["candidates"][0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    
                    # Parse the response
                    question = ""
                    lines = content.split("\n")
                    
                    for line in lines:
                        line = line.strip()
                        if line.startswith("QUESTION:"):
                            question = line.replace("QUESTION:", "").strip()
                            break
                        elif line and not question:
                            # If no QUESTION: prefix, use the first non-empty line
                            question = line
                            break
                    
                    if question:
                        return {
                            "question": question
                            # Note: No options or correct_answer - this is open-ended
                        }
            
        except Exception as e:
            print(f"Gemini open-ended question generation error: {e}")
        
        return None

    @classmethod
    def get_usage_stats(cls) -> Dict:
        """Get usage statistics (placeholder for future tracking)."""
        return {
            "available": True,
            "images_generated": 0,
            "videos_generated": 0,
            "mcqs_generated": 0
        }

