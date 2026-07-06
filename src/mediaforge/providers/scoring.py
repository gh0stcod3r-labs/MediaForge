"""Confidence scoring system for provider matches."""

from typing import Optional
from difflib import SequenceMatcher


class ConfidenceScorer:
    """Calculate match confidence based on multiple factors."""
    
    def __init__(self):
        """Initialize scoring system."""
        self.title_exact = 40
        self.title_fuzzy = 30
        self.season_match = 20
        self.episode_match = 20
        self.year_match = 10
        self.episode_title_match = 10
        self.has_episode_info = 10
        
        self.max_score = 100
        self.review_threshold = 0.80
    
    def calculate(self, 
                  title_match: Optional[bool] = None,
                  title_fuzzy_ratio: Optional[float] = None,
                  season_match: bool = False,
                  episode_match: bool = False,
                  year_match: bool = False,
                  episode_title_match: bool = False,
                  has_episode_info: bool = False) -> float:
        """Calculate confidence score (0.0 to 1.0).
        
        Args:
            title_match: Title matched exactly
            title_fuzzy_ratio: Fuzzy match ratio (0-1) if not exact
            season_match: Season number matched
            episode_match: Episode number matched
            year_match: Year matched
            episode_title_match: Episode title matched
            has_episode_info: Source had season/episode info
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        score = 0
        
        # Title matching
        if title_match:
            score += self.title_exact
        elif title_fuzzy_ratio is not None and title_fuzzy_ratio > 0.8:
            score += self.title_fuzzy
        
        # Other metadata matches
        if season_match:
            score += self.season_match
        if episode_match:
            score += self.episode_match
        if year_match:
            score += self.year_match
        if episode_title_match:
            score += self.episode_title_match
        if has_episode_info:
            score += self.has_episode_info
        
        # Normalize to 0-1
        confidence = min(score / self.max_score, 1.0)
        return confidence
    
    def needs_review(self, confidence: float) -> bool:
        """Check if confidence is below review threshold.
        
        Args:
            confidence: Score (0.0 to 1.0)
            
        Returns:
            True if below review threshold
        """
        return confidence < self.review_threshold
    
    def confidence_to_status(self, confidence: float) -> str:
        """Convert confidence to status string.
        
        Args:
            confidence: Score (0.0 to 1.0)
            
        Returns:
            Status: "No Match", "Needs Review", or "Matched"
        """
        if confidence < 0.5:
            return "No Match"
        elif confidence < 0.8:
            return "Needs Review"
        else:
            return "Matched"


def fuzzy_match(str1: str, str2: str) -> float:
    """Calculate fuzzy match ratio between two strings.
    
    Args:
        str1: First string
        str2: Second string
        
    Returns:
        Match ratio (0.0 to 1.0)
    """
    str1_lower = str1.lower().strip()
    str2_lower = str2.lower().strip()
    
    if str1_lower == str2_lower:
        return 1.0
    
    return SequenceMatcher(None, str1_lower, str2_lower).ratio()
