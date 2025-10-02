"""
Groq LLM Client for Keyword Generation and Analysis
"""
import os
import json
from typing import List, Dict
from groq import Groq
import time


class GroqClient:
    """Client for interacting with Groq LLM API"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize Groq client
        
        Args:
            api_key: Groq API key (optional, will use env var if not provided)
        """
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        if not self.api_key:
            raise ValueError("Groq API key not found. Set GROQ_API_KEY environment variable.")
        
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.1-70b-versatile"
        self.max_retries = 3
        self.retry_delay = 1
    
    def generate_keyword_variations(
        self, 
        seed_keyword: str, 
        count: int = 30
    ) -> List[str]:
        """
        Generate keyword variations using LLM
        
        Args:
            seed_keyword: The seed keyword to expand from
            count: Number of variations to generate
            
        Returns:
            List of keyword variations
        """
        prompt = f"""You are an SEO expert. Generate {count} keyword variations for the seed keyword: "{seed_keyword}"

Requirements:
1. Mix of short-tail (2-3 words) and long-tail (4+ words) keywords
2. Include question-based keywords (how, what, why, where, when)
3. Include commercial intent keywords (best, top, review, comparison)
4. Include informational keywords (guide, tutorial, tips, learn)
5. All keywords must be relevant to the seed keyword
6. No duplicates
7. Return ONLY a JSON array of strings

Example format:
["keyword 1", "keyword 2", "keyword 3"]

Generate the keywords now:"""

        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an SEO expert specializing in keyword research. Return only valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.7,
                    max_tokens=2000
                )
                
                # Extract content
                content = response.choices[0].message.content.strip()
                
                # Try to parse as JSON
                try:
                    # Remove markdown code blocks if present
                    if content.startswith('```'):
                        content = content.split('```')[1]
                        if content.startswith('json'):
                            content = content[4:]
                    
                    keywords = json.loads(content)
                    
                    # Validate it's a list
                    if isinstance(keywords, list):
                        # Clean and filter keywords
                        cleaned = []
                        for kw in keywords:
                            if isinstance(kw, str) and kw.strip():
                                cleaned.append(kw.strip().lower())
                        
                        # Remove duplicates while preserving order
                        seen = set()
                        unique_keywords = []
                        for kw in cleaned:
                            if kw not in seen:
                                seen.add(kw)
                                unique_keywords.append(kw)
                        
                        return unique_keywords[:count]
                    
                except json.JSONDecodeError:
                    # Fallback: extract keywords from text
                    keywords = self._extract_keywords_from_text(content)
                    return keywords[:count]
                
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise
        
        return []
    
    def _extract_keywords_from_text(self, text: str) -> List[str]:
        """
        Fallback method to extract keywords from text
        
        Args:
            text: Text containing keywords
            
        Returns:
            List of extracted keywords
        """
        keywords = []
        lines = text.split('\n')
        
        for line in lines:
            # Remove common list markers
            line = line.strip()
            for marker in ['- ', '* ', '• ', '1. ', '2. ', '3. ']:
                if line.startswith(marker):
                    line = line[len(marker):]
            
            # Remove quotes
            line = line.strip('"\'')
            
            # Skip empty lines or lines that are too short
            if line and len(line) > 3:
                keywords.append(line.lower())
        
        return keywords
    
    def calculate_relevance_score(
        self, 
        seed_keyword: str, 
        candidate_keyword: str
    ) -> float:
        """
        Calculate semantic relevance between seed and candidate keyword
        
        Args:
            seed_keyword: Original seed keyword
            candidate_keyword: Keyword to evaluate
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        prompt = f"""Rate the semantic relevance between these two keywords on a scale of 0.0 to 1.0:

Seed keyword: "{seed_keyword}"
Candidate keyword: "{candidate_keyword}"

Consider:
- Topic similarity
- Search intent alignment
- Semantic relationship

Return ONLY a decimal number between 0.0 and 1.0, nothing else.
Examples: 0.95, 0.72, 0.43

Your rating:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a semantic analysis expert. Return only a decimal number."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=10
            )
            
            # Extract score
            content = response.choices[0].message.content.strip()
            
            # Parse the score
            try:
                score = float(content)
                # Clamp between 0 and 1
                return max(0.0, min(1.0, score))
            except ValueError:
                # Default to moderate relevance if parsing fails
                return 0.6
                
        except Exception as e:
            print(f"Error calculating relevance: {str(e)}")
            return 0.5
    
    def batch_calculate_relevance(
        self, 
        seed_keyword: str, 
        candidate_keywords: List[str]
    ) -> Dict[str, float]:
        """
        Calculate relevance scores for multiple keywords at once
        
        Args:
            seed_keyword: Original seed keyword
            candidate_keywords: List of keywords to evaluate
            
        Returns:
            Dictionary mapping keywords to relevance scores
        """
        # Batch prompt for efficiency
        keywords_str = "\n".join([f"{i+1}. {kw}" for i, kw in enumerate(candidate_keywords)])
        
        prompt = f"""Rate the semantic relevance of each keyword to the seed keyword.
Return scores as a JSON object where each keyword maps to a score (0.0 to 1.0).

Seed keyword: "{seed_keyword}"

Candidate keywords:
{keywords_str}

Return format:
{{
  "keyword 1": 0.85,
  "keyword 2": 0.72,
  ...
}}

Your ratings:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a semantic analysis expert. Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
            
            scores = json.loads(content)
            
            # Normalize and validate scores
            normalized_scores = {}
            for kw in candidate_keywords:
                score = scores.get(kw, 0.5)
                normalized_scores[kw] = max(0.0, min(1.0, float(score)))
            
            return normalized_scores
            
        except Exception as e:
            print(f"Batch relevance calculation failed: {str(e)}")
            # Fallback to individual calculations
            return {
                kw: self.calculate_relevance_score(seed_keyword, kw)
                for kw in candidate_keywords
            }


# Example usage
if __name__ == "__main__":
    client = GroqClient()
    
    seed = "global internship"
    print(f"Generating keywords for: {seed}\n")
    
    keywords = client.generate_keyword_variations(seed, count=20)
    print(f"Generated {len(keywords)} keywords:")
    for i, kw in enumerate(keywords, 1):
        print(f"{i}. {kw}")
    
    print("\nCalculating relevance scores...")
    scores = client.batch_calculate_relevance(seed, keywords[:5])
    for kw, score in scores.items():
        print(f"{kw}: {score:.2f}")