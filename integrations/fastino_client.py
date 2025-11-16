"""Fastino Labs integration for enhanced personalization.

Provides user memory, RAG retrieval, and personalized insights.
Works alongside existing UserStateManager for enhanced personalization.
"""

import os
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime


class FastinoClient:
    """Client for Fastino Labs Personalization API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Fastino client.
        
        Args:
            api_key: Fastino API key. If None, reads from FASTINO_API_KEY env var.
        """
        self.api_key = api_key or os.getenv('FASTINO_API_KEY', '')
        self.api_base = os.getenv('FASTINO_API_BASE', 'https://api.fastino.ai/v1')
        self.enabled = bool(self.api_key)
        
        # Usage tracking for admin dashboard
        self.usage_stats = {
            'events_ingested': 0,
            'queries_made': 0,
            'retrievals_made': 0,
            'users_registered': 0,
            'summaries_fetched': 0,
            'predictions_made': 0,
            'last_used': None
        }
        
        if self.enabled:
            self.headers = {
                "Authorization": f"x-api-key {self.api_key}",
                "Content-Type": "application/json"
            }
        else:
            self.headers = {}
    
    def get_usage_stats(self) -> Dict:
        """Get usage statistics for admin dashboard."""
        return self.usage_stats.copy()
    
    def is_available(self) -> bool:
        """Check if Fastino is available and configured."""
        return self.enabled
    
    def register_user(self, user_id: str, traits: Optional[Dict] = None) -> bool:
        """Register a user with Fastino to create their memory profile.
        
        Args:
            user_id: Unique user identifier
            traits: Optional user traits (name, timezone, etc.)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            payload = {
                "user_id": user_id,
                "traits": traits or {}
            }
            
            response = requests.put(
                f"{self.api_base}/register",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                self.usage_stats['users_registered'] += 1
                self.usage_stats['last_used'] = datetime.now().isoformat()
                return True
            return False
        except Exception as e:
            print(f"Fastino register_user error: {e}")
            return False
    
    def ingest_event(self, user_id: str, event_type: str, content: Dict, 
                    metadata: Optional[Dict] = None) -> bool:
        """Ingest a user event into Fastino memory.
        
        Args:
            user_id: User identifier
            event_type: Type of event (e.g., 'quiz_attempt', 'lesson_completed')
            content: Event content/details
            metadata: Optional metadata (timestamp, etc.)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            event_id = f"{user_id}_{event_type}_{datetime.now().timestamp()}"
            
            payload = {
                "user_id": user_id,
                "source": "learnai_platform",
                "events": [
                    {
                        "event_id": event_id,
                        "type": event_type,
                        "content": content,
                        "metadata": metadata or {}
                    }
                ]
            }
            
            response = requests.post(
                f"{self.api_base}/ingest",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.usage_stats['events_ingested'] += 1
                self.usage_stats['last_used'] = datetime.now().isoformat()
                return True
            return False
        except Exception as e:
            print(f"Fastino ingest_event error: {e}")
            return False
    
    def get_user_summary(self, user_id: str) -> Optional[Dict]:
        """Get a personalized summary for the user.
        
        Args:
            user_id: User identifier
        
        Returns:
            Summary dict with user insights, or None if unavailable
        """
        if not self.enabled:
            return None
        
        try:
            response = requests.get(
                f"{self.api_base}/summary",
                params={"user_id": user_id},
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.usage_stats['summaries_fetched'] += 1
                self.usage_stats['last_used'] = datetime.now().isoformat()
                return response.json()
            return None
        except Exception as e:
            print(f"Fastino get_user_summary error: {e}")
            return None
    
    def query_user_profile(self, user_id: str, query: str) -> Optional[Dict]:
        """Query user profile using natural language.
        
        Args:
            user_id: User identifier
            query: Natural language query (e.g., "What topics does the user struggle with?")
        
        Returns:
            Query results, or None if unavailable
        """
        if not self.enabled:
            return None
        
        try:
            payload = {
                "user_id": user_id,
                "query": query
            }
            
            response = requests.post(
                f"{self.api_base}/query",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.usage_stats['queries_made'] += 1
                self.usage_stats['last_used'] = datetime.now().isoformat()
                return response.json()
            return None
        except Exception as e:
            print(f"Fastino query_user_profile error: {e}")
            return None
    
    def retrieve_memories(self, user_id: str, query: str, top_k: int = 5) -> List[Dict]:
        """Retrieve relevant memories using RAG.
        
        Args:
            user_id: User identifier
            query: Query to find relevant memories
            top_k: Number of memories to retrieve
        
        Returns:
            List of relevant memory snippets
        """
        if not self.enabled:
            return []
        
        try:
            payload = {
                "user_id": user_id,
                "query": query,
                "top_k": top_k
            }
            
            response = requests.post(
                f"{self.api_base}/retrieve",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.usage_stats['retrievals_made'] += 1
                self.usage_stats['last_used'] = datetime.now().isoformat()
                data = response.json()
                return data.get("memories", [])
            return []
        except Exception as e:
            print(f"Fastino retrieve_memories error: {e}")
            return []
    
    def predict_decision(self, user_id: str, context: Dict) -> Optional[Dict]:
        """Predict user decision based on historical patterns.
        
        Args:
            user_id: User identifier
            context: Context for the decision (e.g., available learning paths)
        
        Returns:
            Prediction results, or None if unavailable
        """
        if not self.enabled:
            return None
        
        try:
            payload = {
                "user_id": user_id,
                "context": context
            }
            
            response = requests.post(
                f"{self.api_base}/predict",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.usage_stats['predictions_made'] += 1
                self.usage_stats['last_used'] = datetime.now().isoformat()
                return response.json()
            return None
        except Exception as e:
            print(f"Fastino predict_decision error: {e}")
            return None


# Global Fastino client instance
_fastino_client = None


def get_fastino_client() -> FastinoClient:
    """Get or create the global Fastino client instance."""
    global _fastino_client
    if _fastino_client is None:
        _fastino_client = FastinoClient()
    return _fastino_client

