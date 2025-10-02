"""
Google Trends Client for Search Volume Estimation
"""
import os
from typing import Dict, List, Optional
from pytrends.request import TrendReq
import time


class TrendsClient:
    """Client for Google Trends data"""
    
    def __init__(self):
        """Initialize Google Trends client"""
        self.enabled = os.getenv('GOOGLE_TRENDS_ENABLED', 'true').lower() == 'true'
        
        if self.enabled:
            try:
                self.pytrends = TrendReq(hl='en-US', tz=360)
            except Exception as e:
                print(f"Warning: Could not initialize Google Trends: {str(e)}")
                self.enabled = False
        
        self.retry_delay = 2
        self.max_retries = 3
    
    def get_interest_over_time(self, keyword: str) -> Dict:
        """
        Get interest over time for keyword
        
        Args:
            keyword: Keyword to analyze
            
        Returns:
            Dictionary with trend data
        """
        if not self.enabled:
            return {'average_interest': 50, 'trend': 'stable'}
        
        for attempt in range(self.max_retries):
            try:
                # Build payload
                self.pytrends.build_payload([keyword], timeframe='today 12-m')
                
                # Get interest over time
                interest_df = self.pytrends.interest_over_time()
                
                if interest_df.empty:
                    return {'average_interest': 0, 'trend': 'no_data'}
                
                # Calculate average interest
                avg_interest = int(interest_df[keyword].mean())
                
                # Determine trend
                recent = interest_df[keyword].tail(3).mean()
                older = interest_df[keyword].head(3).mean()
                
                if recent > older * 1.2:
                    trend = 'rising'
                elif recent < older * 0.8:
                    trend = 'declining'
                else:
                    trend = 'stable'
                
                return {
                    'average_interest': avg_interest,
                    'trend': trend,
                    'max_interest': int(interest_df[keyword].max()),
                    'min_interest': int(interest_df[keyword].min())
                }
                
            except Exception as e:
                print(f"Trends attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    # Return default values on failure
                    return {'average_interest': 50, 'trend': 'stable'}
        
        return {'average_interest': 50, 'trend': 'stable'}
    
    def get_related_queries(self, keyword: str) -> List[str]:
        """
        Get related queries from Google Trends
        
        Args:
            keyword: Seed keyword
            
        Returns:
            List of related queries
        """
        if not self.enabled:
            return []
        
        try:
            self.pytrends.build_payload([keyword], timeframe='today 12-m')
            related_queries = self.pytrends.related_queries()
            
            queries = []
            
            if keyword in related_queries:
                # Top related
                top = related_queries[keyword].get('top')
                if top is not None and not top.empty:
                    queries.extend(top['query'].tolist())
                
                # Rising related
                rising = related_queries[keyword].get('rising')
                if rising is not None and not rising.empty:
                    queries.extend(rising['query'].tolist())
            
            # Remove duplicates
            return list(set(queries))
            
        except Exception as e:
            print(f"Error getting related queries: {str(e)}")
            return []
    
    def estimate_search_volume(self, keyword: str, base_volume: int = 1000) -> int:
        """
        Estimate monthly search volume based on Google Trends interest
        
        Args:
            keyword: Keyword to estimate
            base_volume: Base volume for scaling
            
        Returns:
            Estimated monthly search volume
        """
        if not self.enabled:
            # Fallback: estimate based on keyword length
            return self._estimate_by_length(keyword)
        
        try:
            interest_data = self.get_interest_over_time(keyword)
            avg_interest = interest_data['average_interest']
            
            # Scale volume based on interest (0-100)
            # Interest of 100 = 10x base volume
            # Interest of 50 = 1x base volume
            # Interest of 0 = 0.1x base volume
            
            if avg_interest == 0:
                estimated_volume = base_volume // 10
            else:
                scaling_factor = (avg_interest / 50.0)
                estimated_volume = int(base_volume * scaling_factor)
            
            return max(estimated_volume, 10)  # Minimum 10 searches
            
        except Exception as e:
            print(f"Error estimating volume: {str(e)}")
            return self._estimate_by_length(keyword)
    
    def _estimate_by_length(self, keyword: str) -> int:
        """
        Fallback: Estimate volume by keyword length
        Longer = more specific = lower volume
        
        Args:
            keyword: Keyword to estimate
            
        Returns:
            Estimated volume
        """
        word_count = len(keyword.split())
        
        # Simple heuristic
        if word_count <= 2:
            return 5000  # Short-tail
        elif word_count == 3:
            return 2000  # Medium-tail
        elif word_count == 4:
            return 1000  # Long-tail
        else:
            return 500   # Very long-tail
    
    def batch_estimate_volumes(self, keywords: List[str], delay: float = 2.0) -> Dict[str, int]:
        """
        Estimate volumes for multiple keywords
        
        Args:
            keywords: List of keywords
            delay: Delay between requests
            
        Returns:
            Dictionary mapping keywords to estimated volumes
        """
        volumes = {}
        
        for i, keyword in enumerate(keywords):
            volumes[keyword] = self.estimate_search_volume(keyword)
            
            # Rate limiting for Google Trends
            if i < len(keywords) - 1 and self.enabled:
                time.sleep(delay)
        
        return volumes


# Example usage
if __name__ == "__main__":
    client = TrendsClient()
    
    if client.enabled:
        keyword = "global internship"
        print(f"Analyzing trends for: {keyword}\n")
        
        # Get interest over time
        interest = client.get_interest_over_time(keyword)
        print(f"Interest Data:")
        print(f"  Average Interest: {interest['average_interest']}/100")
        print(f"  Trend: {interest['trend']}")
        
        # Estimate volume
        volume = client.estimate_search_volume(keyword)
        print(f"\nEstimated Monthly Volume: {volume:,}")
        
        # Get related queries
        related = client.get_related_queries(keyword)
        print(f"\nRelated Queries: {len(related)}")
        for r in related[:5]:
            print(f"  - {r}")
    else:
        print("Google Trends is disabled")