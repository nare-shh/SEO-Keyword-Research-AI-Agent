"""
Keyword Scoring Algorithm
"""
import os
from typing import Dict, List
import math


class KeywordScorer:
    """Score and rank keywords based on multiple factors"""
    
    def __init__(self):
        """Initialize scorer with configurable weights"""
        self.volume_weight = float(os.getenv('VOLUME_WEIGHT', '0.4'))
        self.competition_weight = float(os.getenv('COMPETITION_WEIGHT', '0.4'))
        self.relevance_weight = float(os.getenv('RELEVANCE_WEIGHT', '0.2'))
        
        # Ensure weights sum to 1.0
        total = self.volume_weight + self.competition_weight + self.relevance_weight
        if abs(total - 1.0) > 0.01:
            # Normalize weights
            self.volume_weight /= total
            self.competition_weight /= total
            self.relevance_weight /= total
    
    def calculate_opportunity_score(self, keyword_data: Dict) -> float:
        """
        Calculate opportunity score for keyword
        
        Formula:
        Opportunity Score = (Volume_Score * W1) + (Competition_Score * W2) + (Relevance_Score * W3)
        
        Where:
        - Volume_Score: Normalized search volume (0-100)
        - Competition_Score: Inverse competition (100 - competition_score)
        - Relevance_Score: Semantic relevance (0-100)
        - W1, W2, W3: Configurable weights
        
        Args:
            keyword_data: Dictionary with keyword metrics
            
        Returns:
            Opportunity score (0-100)
        """
        # Extract metrics
        volume = keyword_data.get('estimated_volume', 1000)
        competition = keyword_data.get('competition_score', 50)
        relevance = keyword_data.get('relevance_score', 0.5)
        
        # Normalize volume (diminishing returns at scale)
        # Use square root to reduce impact of very high volumes
        volume_normalized = min(math.sqrt(volume) / 10, 100)
        
        # Inverse competition (lower competition = higher score)
        competition_score = 100 - competition
        
        # Relevance to 0-100 scale
        relevance_score = relevance * 100
        
        # Calculate weighted opportunity score
        opportunity_score = (
            (volume_normalized * self.volume_weight) +
            (competition_score * self.competition_weight) +
            (relevance_score * self.relevance_weight)
        )
        
        return round(opportunity_score, 2)
    
    def calculate_keyword_difficulty(self, serp_analysis: Dict) -> int:
        """
        Calculate keyword difficulty (0-100)
        
        Args:
            serp_analysis: SERP analysis data
            
        Returns:
            Difficulty score (0 = easiest, 100 = hardest)
        """
        difficulty = 0
        
        # Big brands factor (0-40 points)
        big_brands = serp_analysis.get('big_brands_count', 0)
        difficulty += min(big_brands * 8, 40)
        
        # SERP features factor (0-30 points)
        if serp_analysis.get('has_featured_snippet', False):
            difficulty += 10
        if serp_analysis.get('has_knowledge_graph', False):
            difficulty += 10
        if serp_analysis.get('has_ads', False):
            difficulty += 10
        
        # Total results factor (0-30 points)
        total_results = serp_analysis.get('total_results', 0)
        if total_results > 100000000:
            difficulty += 30
        elif total_results > 10000000:
            difficulty += 20
        elif total_results > 1000000:
            difficulty += 10
        
        return min(difficulty, 100)
    
    def estimate_ranking_potential(self, keyword_data: Dict) -> Dict:
        """
        Estimate ranking potential with detailed breakdown
        
        Args:
            keyword_data: Complete keyword data
            
        Returns:
            Dictionary with ranking assessment
        """
        competition = keyword_data.get('competition_score', 50)
        first_page_prob = keyword_data.get('first_page_probability', 0.5)
        opportunity = keyword_data.get('opportunity_score', 50)
        
        # Determine difficulty category
        if competition < 30:
            difficulty_category = "Low"
            difficulty_description = "Easy to rank with quality content"
        elif competition < 50:
            difficulty_category = "Medium-Low"
            difficulty_description = "Good opportunity with moderate effort"
        elif competition < 70:
            difficulty_category = "Medium"
            difficulty_description = "Requires strong content and backlinks"
        elif competition < 85:
            difficulty_category = "Medium-High"
            difficulty_description = "Challenging, needs authority and optimization"
        else:
            difficulty_category = "High"
            difficulty_description = "Very difficult, dominated by major brands"
        
        # Determine opportunity rating
        if opportunity >= 75:
            opportunity_rating = "Excellent"
        elif opportunity >= 60:
            opportunity_rating = "Good"
        elif opportunity >= 45:
            opportunity_rating = "Fair"
        else:
            opportunity_rating = "Poor"
        
        return {
            'difficulty_category': difficulty_category,
            'difficulty_description': difficulty_description,
            'opportunity_rating': opportunity_rating,
            'first_page_probability': first_page_prob,
            'recommendation': self._generate_recommendation(keyword_data)
        }
    
    def _generate_recommendation(self, keyword_data: Dict) -> str:
        """
        Generate actionable recommendation for keyword
        
        Args:
            keyword_data: Keyword metrics
            
        Returns:
            Recommendation string
        """
        competition = keyword_data.get('competition_score', 50)
        volume = keyword_data.get('estimated_volume', 1000)
        relevance = keyword_data.get('relevance_score', 0.5)
        opportunity = keyword_data.get('opportunity_score', 50)
        
        # High opportunity keywords
        if opportunity >= 70 and competition < 40:
            return "🎯 High Priority: Low competition, good volume - target immediately"
        
        # Good long-tail opportunities
        elif competition < 30 and relevance > 0.7:
            return "✅ Quick Win: Easy to rank, highly relevant - great for content strategy"
        
        # High volume but competitive
        elif volume > 5000 and competition > 70:
            return "⚠️ Long-term Target: High competition - requires authority building"
        
        # Low competition but low volume
        elif competition < 30 and volume < 500:
            return "💡 Niche Opportunity: Low volume but easy rank - good for specific audiences"
        
        # Balanced opportunity
        elif 40 <= opportunity < 70:
            return "📊 Moderate Opportunity: Balanced metrics - include in content mix"
        
        # Low priority
        else:
            return "⏸️ Low Priority: Better opportunities available - consider alternatives"
    
    def rank_keywords(self, keywords_data: List[Dict], top_n: int = 50) -> List[Dict]:
        """
        Rank keywords by opportunity score
        
        Args:
            keywords_data: List of keyword dictionaries
            top_n: Number of top keywords to return
            
        Returns:
            Sorted list of top keywords
        """
        # Calculate opportunity scores
        for kw_data in keywords_data:
            kw_data['opportunity_score'] = self.calculate_opportunity_score(kw_data)
            kw_data['ranking_potential'] = self.estimate_ranking_potential(kw_data)
        
        # Sort by opportunity score (descending)
        sorted_keywords = sorted(
            keywords_data,
            key=lambda x: x['opportunity_score'],
            reverse=True
        )
        
        # Add rank numbers
        for i, kw_data in enumerate(sorted_keywords[:top_n], 1):
            kw_data['rank'] = i
        
        return sorted_keywords[:top_n]
    
    def generate_reasoning(self, keyword_data: Dict) -> str:
        """
        Generate human-readable reasoning for keyword ranking
        
        Args:
            keyword_data: Keyword metrics
            
        Returns:
            Reasoning text
        """
        keyword = keyword_data.get('keyword', '')
        volume = keyword_data.get('estimated_volume', 0)
        competition = keyword_data.get('competition_score', 0)
        relevance = keyword_data.get('relevance_score', 0)
        opportunity = keyword_data.get('opportunity_score', 0)
        big_brands = keyword_data.get('big_brands_count', 0)
        
        reasons = []
        
        # Volume reasoning
        if volume > 5000:
            reasons.append(f"high search volume ({volume:,}/month)")
        elif volume > 1000:
            reasons.append(f"moderate search volume ({volume:,}/month)")
        else:
            reasons.append(f"low search volume ({volume:,}/month)")
        
        # Competition reasoning
        if competition < 30:
            reasons.append("low competition")
        elif competition < 50:
            reasons.append("moderate competition")
        else:
            reasons.append("high competition")
        
        # Brand dominance
        if big_brands == 0:
            reasons.append("no major brands in top 10")
        elif big_brands <= 2:
            reasons.append(f"only {big_brands} major brand(s) in top 10")
        else:
            reasons.append(f"{big_brands} major brands dominating results")
        
        # Relevance
        if relevance >= 0.8:
            reasons.append("highly relevant to seed keyword")
        elif relevance >= 0.6:
            reasons.append("moderately relevant")
        else:
            reasons.append("loosely related")
        
        # SERP features
        if keyword_data.get('has_featured_snippet'):
            reasons.append("featured snippet present")
        if keyword_data.get('has_knowledge_graph'):
            reasons.append("knowledge graph present")
        
        return f"{keyword}: " + ", ".join(reasons)


# Example usage
if __name__ == "__main__":
    scorer = KeywordScorer()
    
    # Sample keyword data
    keyword_data = {
        'keyword': 'remote international internship programs',
        'estimated_volume': 2400,
        'competition_score': 22,
        'relevance_score': 0.92,
        'big_brands_count': 1,
        'has_featured_snippet': False,
        'has_knowledge_graph': False,
        'first_page_probability': 0.78
    }
    
    # Calculate scores
    opportunity = scorer.calculate_opportunity_score(keyword_data)
    print(f"Opportunity Score: {opportunity}/100")
    
    keyword_data['opportunity_score'] = opportunity
    potential = scorer.estimate_ranking_potential(keyword_data)
    
    print(f"\nRanking Potential:")
    print(f"  Difficulty: {potential['difficulty_category']}")
    print(f"  Opportunity: {potential['opportunity_rating']}")
    print(f"  First Page Prob: {potential['first_page_probability']:.0%}")
    print(f"  Recommendation: {potential['recommendation']}")
    
    print(f"\nReasoning:")
    print(f"  {scorer.generate_reasoning(keyword_data)}")