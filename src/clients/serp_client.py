"""
SERP API Client for Search Results and Competition Analysis
"""
import os
import time
from typing import Dict, List, Optional
from serpapi import GoogleSearch


class SerpClient:
    """Client for interacting with SERP API"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize SERP API client
        
        Args:
            api_key: SERP API key (optional, will use env var if not provided)
        """
        self.api_key = api_key or os.getenv('SERP_API_KEY')
        if not self.api_key:
            raise ValueError("SERP API key not found. Set SERP_API_KEY environment variable.")
        
        self.location = os.getenv('SERP_LOCATION', 'United States')
        self.language = os.getenv('SERP_LANGUAGE', 'en')
        self.country = os.getenv('SERP_COUNTRY', 'us')
        self.max_retries = 3
        self.retry_delay = 1
        
        # High authority domains for competition analysis
        self.high_authority_domains = [
            'wikipedia.org', 'amazon.com', 'linkedin.com',
            'indeed.com', 'glassdoor.com', 'forbes.com',
            'nytimes.com', 'medium.com', 'reddit.com',
            'youtube.com', 'stackoverflow.com', 'github.com',
            'quora.com', 'bbc.com', 'cnn.com'
        ]
    
    def search(self, keyword: str, num_results: int = 10) -> Dict:
        """
        Perform Google search for keyword
        
        Args:
            keyword: Search query
            num_results: Number of results to fetch
            
        Returns:
            Search results dictionary
        """
        params = {
            'q': keyword,
            'api_key': self.api_key,
            'engine': 'google',
            'location': self.location,
            'gl': self.country,
            'hl': self.language,
            'num': num_results
        }
        
        for attempt in range(self.max_retries):
            try:
                search = GoogleSearch(params)
                results = search.get_dict()
                return results
            except Exception as e:
                print(f"Search attempt {attempt + 1} failed for '{keyword}': {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise
        
        return {}
    
    def get_related_searches(self, keyword: str) -> List[str]:
        """
        Get related searches for keyword
        
        Args:
            keyword: Search query
            
        Returns:
            List of related search keywords
        """
        try:
            results = self.search(keyword)
            related = results.get('related_searches', [])
            return [item['query'] for item in related if 'query' in item]
        except Exception as e:
            print(f"Error getting related searches: {str(e)}")
            return []
    
    def get_people_also_ask(self, keyword: str) -> List[str]:
        """
        Get "People Also Ask" questions
        
        Args:
            keyword: Search query
            
        Returns:
            List of PAA questions
        """
        try:
            results = self.search(keyword)
            paa = results.get('related_questions', [])
            return [item['question'] for item in paa if 'question' in item]
        except Exception as e:
            print(f"Error getting PAA: {str(e)}")
            return []
    
    def analyze_competition(self, keyword: str) -> Dict:
        """
        Comprehensive competition analysis for keyword
        
        Args:
            keyword: Keyword to analyze
            
        Returns:
            Competition analysis dictionary
        """
        try:
            results = self.search(keyword, num_results=10)
            
            organic_results = results.get('organic_results', [])[:10]
            
            analysis = {
                'keyword': keyword,
                'total_results': results.get('search_information', {}).get('total_results', 0),
                'organic_results_count': len(organic_results),
                'big_brands_count': 0,
                'has_featured_snippet': 'featured_snippet' in results or 'answer_box' in results,
                'has_knowledge_graph': 'knowledge_graph' in results,
                'has_ads': 'ads' in results or 'top_ads' in results,
                'serp_features_count': 0,
                'domains': [],
                'competition_score': 0,
                'first_page_probability': 0.0
            }
            
            # Analyze top 10 organic results
            for result in organic_results:
                domain = result.get('domain', result.get('displayed_link', ''))
                analysis['domains'].append(domain)
                
                # Check for high authority domains
                if any(auth_domain in domain.lower() for auth_domain in self.high_authority_domains):
                    analysis['big_brands_count'] += 1
            
            # Count SERP features
            if analysis['has_featured_snippet']:
                analysis['serp_features_count'] += 1
            if analysis['has_knowledge_graph']:
                analysis['serp_features_count'] += 1
            if analysis['has_ads']:
                analysis['serp_features_count'] += 1
            
            # Calculate competition score (0-100)
            # Higher score = harder to rank
            competition_score = 0
            
            # Big brands factor (0-50 points)
            competition_score += min(analysis['big_brands_count'] * 10, 50)
            
            # SERP features factor (0-30 points)
            if analysis['has_featured_snippet']:
                competition_score += 10
            if analysis['has_knowledge_graph']:
                competition_score += 10
            if analysis['has_ads']:
                competition_score += 10
            
            # Total results factor (0-20 points)
            total_results = analysis['total_results']
            if total_results > 100000000:
                competition_score += 20
            elif total_results > 10000000:
                competition_score += 15
            elif total_results > 1000000:
                competition_score += 10
            elif total_results > 100000:
                competition_score += 5
            
            analysis['competition_score'] = min(competition_score, 100)
            
            # Estimate first page probability
            analysis['first_page_probability'] = self._estimate_first_page_probability(analysis)
            
            return analysis
            
        except Exception as e:
            print(f"Error analyzing competition for '{keyword}': {str(e)}")
            return {
                'keyword': keyword,
                'error': str(e),
                'competition_score': 50,  # Default medium competition
                'first_page_probability': 0.3
            }
    
    def _estimate_first_page_probability(self, analysis: Dict) -> float:
        """
        Estimate probability of ranking on first page
        
        Args:
            analysis: Competition analysis dictionary
            
        Returns:
            Probability score (0.0 to 1.0)
        """
        comp_score = analysis['competition_score']
        big_brands = analysis['big_brands_count']
        serp_features = analysis['serp_features_count']
        
        # Base probability by competition score
        if comp_score < 20:
            base_prob = 0.85
        elif comp_score < 40:
            base_prob = 0.65
        elif comp_score < 60:
            base_prob = 0.45
        elif comp_score < 80:
            base_prob = 0.25
        else:
            base_prob = 0.10
        
        # Adjust for big brands
        brand_penalty = min(big_brands * 0.08, 0.30)
        
        # Adjust for SERP features
        feature_penalty = min(serp_features * 0.05, 0.20)
        
        # Calculate final probability
        final_probability = max(base_prob - brand_penalty - feature_penalty, 0.05)
        
        return round(final_probability, 2)
    
    def batch_analyze_keywords(self, keywords: List[str], delay: float = 0.5) -> List[Dict]:
        """
        Analyze multiple keywords with rate limiting
        
        Args:
            keywords: List of keywords to analyze
            delay: Delay between requests (seconds)
            
        Returns:
            List of analysis dictionaries
        """
        results = []
        
        for i, keyword in enumerate(keywords):
            print(f"Analyzing {i+1}/{len(keywords)}: {keyword}")
            analysis = self.analyze_competition(keyword)
            results.append(analysis)
            
            # Rate limiting
            if i < len(keywords) - 1:
                time.sleep(delay)
        
        return results


# Example usage
if __name__ == "__main__":
    client = SerpClient()
    
    # Test single keyword
    keyword = "global internship"
    print(f"Analyzing: {keyword}\n")
    
    # Get related searches
    related = client.get_related_searches(keyword)
    print(f"Related searches: {len(related)}")
    for r in related[:5]:
        print(f"  - {r}")
    
    # Get PAA
    paa = client.get_people_also_ask(keyword)
    print(f"\nPeople Also Ask: {len(paa)}")
    for q in paa[:3]:
        print(f"  - {q}")
    
    # Competition analysis
    print("\nCompetition Analysis:")
    analysis = client.analyze_competition(keyword)
    print(f"  Competition Score: {analysis['competition_score']}/100")
    print(f"  Big Brands: {analysis['big_brands_count']}")
    print(f"  First Page Probability: {analysis['first_page_probability']:.0%}")
    print(f"  SERP Features: {analysis['serp_features_count']}")