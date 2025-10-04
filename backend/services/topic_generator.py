"""
Topic generation service using AI
"""
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from utils.llm_provider import get_gemini_model

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TopicGenerator:
    """Service to generate topics from paper titles using AI"""
    
    def __init__(self):
        """Initialize the topic generator with AI model"""
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the AI model"""
        try:
            self.model = get_gemini_model()
            if self.model:
                logger.info("✅ Topic generator initialized with Gemini model")
            else:
                logger.error("❌ Failed to initialize Gemini model")
        except Exception as e:
            logger.error(f"Error initializing AI model: {e}")
            self.model = None
    
    def generate_topic_from_titles(
        self, 
        titles: List[str], 
        cluster_id: str = None
    ) -> Tuple[str, float]:
        """
        Generate a topic name from a list of paper titles
        
        Args:
            titles: List of paper titles
            cluster_id: Optional cluster identifier for context
            
        Returns:
            Tuple of (topic_name, confidence_score)
        """
        if not self.model:
            logger.warning("AI model not available, using fallback topic generation")
            return self._fallback_topic_generation(titles, cluster_id)
        
        if not titles:
            return "Empty Cluster", 0.0
        
        try:
            # Prepare prompt for AI
            prompt = self._create_topic_prompt(titles, cluster_id)
            
            # Generate response
            response = self.model.generate_content(prompt)
            
            # Parse response
            topic_name, confidence = self._parse_ai_response(response.text, titles)
            
            logger.info(f"Generated topic '{topic_name}' with confidence {confidence:.2f} for {len(titles)} papers")
            return topic_name, confidence
            
        except Exception as e:
            logger.error(f"Error generating topic with AI: {e}")
            return self._fallback_topic_generation(titles, cluster_id)
    
    def _create_topic_prompt(self, titles: List[str], cluster_id: str = None) -> str:
        """Create a prompt for AI topic generation"""
        
        # Limit titles to avoid token limit
        sample_titles = titles[:20] if len(titles) > 20 else titles
        
        prompt = f"""
Analyze the following research paper titles and generate a concise, descriptive topic name that captures the main theme.

Paper Titles ({len(sample_titles)} of {len(titles)} total):
{chr(10).join([f"- {title}" for title in sample_titles])}

Requirements:
1. Generate a short, descriptive topic name (2-5 words)
2. Focus on the main research domain/theme
3. Use academic/scientific terminology
4. Be specific but not too narrow
5. Return response in JSON format

Expected JSON response format:
{{
    "topic": "Topic Name Here",
    "confidence": 0.85,
    "reasoning": "Brief explanation of why this topic was chosen"
}}

Generate the topic now:
"""
        return prompt.strip()
    
    def _parse_ai_response(self, response_text: str, titles: List[str]) -> Tuple[str, float]:
        """Parse AI response to extract topic and confidence"""
        try:
            # Try to parse JSON response
            if '{' in response_text and '}' in response_text:
                # Extract JSON part
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                json_str = response_text[json_start:json_end]
                
                data = json.loads(json_str)
                topic = data.get('topic', 'Unknown Topic')
                confidence = float(data.get('confidence', 0.5))
                
                # Validate confidence range
                confidence = max(0.0, min(1.0, confidence))
                
                return topic, confidence
            else:
                # Fallback: use the text as topic name
                topic = response_text.strip()
                # Simple confidence based on title consistency
                confidence = self._calculate_simple_confidence(titles)
                return topic, confidence
                
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return self._fallback_topic_generation(titles)
    
    def _fallback_topic_generation(self, titles: List[str], cluster_id: str = None) -> Tuple[str, float]:
        """Fallback topic generation when AI is not available"""
        if not titles:
            return "Empty Cluster", 0.0
        
        # Simple keyword extraction approach
        common_words = self._extract_common_keywords(titles)
        
        if common_words:
            topic = " ".join(common_words[:3]).title()  # Take top 3 keywords
            confidence = 0.3  # Low confidence for fallback method
        else:
            topic = f"Research Cluster {cluster_id}" if cluster_id else "Research Papers"
            confidence = 0.1
        
        return topic, confidence
    
    def _extract_common_keywords(self, titles: List[str]) -> List[str]:
        """Extract common keywords from titles"""
        import re
        from collections import Counter
        
        # Common stop words to filter out
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'this', 'that',
            'these', 'those', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'study', 'analysis', 'research'
        }
        
        # Extract words from all titles
        all_words = []
        for title in titles:
            # Clean and split title
            words = re.findall(r'\b[a-zA-Z]{3,}\b', title.lower())
            all_words.extend([word for word in words if word not in stop_words])
        
        # Count frequency and return most common
        word_counts = Counter(all_words)
        return [word for word, count in word_counts.most_common(10) if count > 1]
    
    def _calculate_simple_confidence(self, titles: List[str]) -> float:
        """Calculate simple confidence based on title similarity"""
        if len(titles) < 2:
            return 0.5
        
        # Simple metric: more papers = higher confidence, up to a point
        confidence = min(0.8, 0.3 + (len(titles) * 0.02))
        return confidence


# Global instance
_topic_generator = None

def get_topic_generator() -> TopicGenerator:
    """Get or create the global topic generator instance"""
    global _topic_generator
    if _topic_generator is None:
        _topic_generator = TopicGenerator()
    return _topic_generator
