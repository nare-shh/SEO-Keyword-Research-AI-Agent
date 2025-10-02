#!/usr/bin/env python3
"""
SEO Keyword Research AI Agent
Main execution script
"""
import os
import sys
import json
import time
from datetime import datetime
from typing import List, Dict
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.clients.groq_client import GroqClient
from src.clients.serp_client import SerpClient
from src.clients.trends_client import TrendsClient
from src.agents.keyword_scorer import KeywordScorer
from dotenv import load_dotenv


class SEOKeywordAgent:
    """Main SEO Keyword Research Agent"""
    
    def __init__(self):
        """Initialize the agent with all necessary clients"""
        # Load environment variables
        load_dotenv()
        
        # Initialize clients
        print("🚀 Initializing SEO Keyword Research Agent...")
        self.groq_client = GroqClient()
        self.serp_client = SerpClient()
        self.trends_client = TrendsClient()
        self.scorer = KeywordScorer()
        
        # Configuration
        self.max_keywords = int(os.getenv('MAX_KEYWORDS', '50'))
        self.expansion_count = int(os.getenv('EXPANSION_COUNT', '30'))
        self.min_relevance = float(os.getenv('MIN_RELEVANCE_SCORE', '0.5'))
        self.api_delay = float(os.getenv('API_DELAY', '0.5'))
        
        print("✅ Agent initialized successfully!\n")
    
    def research_keywords(self, seed_keyword: str) -> Dict:
        """
        Complete keyword research workflow
        
        Args:
            seed_keyword: The seed keyword to research
            
        Returns:
            Dictionary with top keywords and metadata
        """
        start_time = time.time()
        print(f"{'='*60}")
        print(f"🎯 Starting Keyword Research for: '{seed_keyword}'")
        print(f"{'='*60}\n")
        
        # Step 1: Keyword Expansion
        print("📝 Step 1: Expanding keywords with LLM...")
        llm_keywords = self._expand_keywords_llm(seed_keyword)
        print(f"   Generated {len(llm_keywords)} variations\n")
        
        # Step 2: Get Related Searches from SERP
        print("🔍 Step 2: Fetching related searches from SERP...")
        serp_keywords = self._get_serp_suggestions(seed_keyword)
        print(f"   Found {len(serp_keywords)} SERP suggestions\n")
        
        # Step 3: Get Google Trends suggestions
        print("📈 Step 3: Getting Google Trends data...")
        trends_keywords = self._get_trends_suggestions(seed_keyword)
        print(f"   Found {len(trends_keywords)} trending queries\n")
        
        # Step 4: Merge and deduplicate
        print("🔄 Step 4: Merging and deduplicating keywords...")
        all_keywords = self._merge_keywords(
            llm_keywords, 
            serp_keywords, 
            trends_keywords,
            seed_keyword
        )
        print(f"   Total unique keywords: {len(all_keywords)}\n")
        
        # Step 5: Calculate relevance scores
        print("🎯 Step 5: Calculating relevance scores...")
        keywords_with_relevance = self._add_relevance_scores(seed_keyword, all_keywords)
        
        # Filter by minimum relevance
        filtered_keywords = [
            kw for kw in keywords_with_relevance 
            if kw['relevance_score'] >= self.min_relevance
        ]
        print(f"   {len(filtered_keywords)} keywords passed relevance filter\n")
        
        # Step 6: Analyze competition (SERP analysis)
        print("🏆 Step 6: Analyzing competition (this may take a while)...")
        keywords_with_competition = self._analyze_competition(filtered_keywords)
        print(f"   Analyzed {len(keywords_with_competition)} keywords\n")
        
        # Step 7: Estimate search volumes
        print("📊 Step 7: Estimating search volumes...")
        keywords_with_volumes = self._estimate_volumes(keywords_with_competition)
        print(f"   Estimated volumes for {len(keywords_with_volumes)} keywords\n")
        
        # Step 8: Score and rank keywords
        print("🎖️  Step 8: Scoring and ranking keywords...")
        top_keywords = self.scorer.rank_keywords(keywords_with_volumes, self.max_keywords)
        print(f"   Top {len(top_keywords)} keywords selected\n")
        
        # Step 9: Generate reasoning
        print("💭 Step 9: Generating insights...")
        for kw_data in top_keywords:
            kw_data['reasoning'] = self.scorer.generate_reasoning(kw_data)
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Prepare results
        results = {
            'seed_keyword': seed_keyword,
            'generated_at': datetime.now().isoformat(),
            'execution_time_seconds': round(execution_time, 2),
            'total_keywords_analyzed': len(all_keywords),
            'keywords_after_relevance_filter': len(filtered_keywords),
            'top_keywords_count': len(top_keywords),
            'configuration': {
                'max_keywords': self.max_keywords,
                'min_relevance_score': self.min_relevance,
                'volume_weight': self.scorer.volume_weight,
                'competition_weight': self.scorer.competition_weight,
                'relevance_weight': self.scorer.relevance_weight
            },
            'top_keywords': top_keywords
        }
        
        print(f"\n{'='*60}")
        print(f"✅ Research Complete! Time: {execution_time:.1f}s")
        print(f"{'='*60}\n")
        
        return results
    
    def _expand_keywords_llm(self, seed_keyword: str) -> List[str]:
        """Expand keywords using LLM"""
        return self.groq_client.generate_keyword_variations(
            seed_keyword, 
            count=self.expansion_count
        )
    
    def _get_serp_suggestions(self, seed_keyword: str) -> List[str]:
        """Get keyword suggestions from SERP API"""
        related = self.serp_client.get_related_searches(seed_keyword)
        paa = self.serp_client.get_people_also_ask(seed_keyword)
        
        # Combine and clean
        all_suggestions = related + paa
        cleaned = [kw.lower().strip('?') for kw in all_suggestions]
        
        return cleaned
    
    def _get_trends_suggestions(self, seed_keyword: str) -> List[str]:
        """Get suggestions from Google Trends"""
        if not self.trends_client.enabled:
            return []
        
        return self.trends_client.get_related_queries(seed_keyword)
    
    def _merge_keywords(
        self, 
        llm_kw: List[str], 
        serp_kw: List[str], 
        trends_kw: List[str],
        seed_kw: str
    ) -> List[str]:
        """Merge and deduplicate keywords"""
        # Combine all sources
        all_keywords = llm_kw + serp_kw + trends_kw
        
        # Add seed keyword
        all_keywords.append(seed_kw.lower())
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        
        for kw in all_keywords:
            kw_clean = kw.lower().strip()
            if kw_clean and kw_clean not in seen and len(kw_clean) > 3:
                seen.add(kw_clean)
                unique_keywords.append(kw_clean)
        
        return unique_keywords
    
    def _add_relevance_scores(self, seed_keyword: str, keywords: List[str]) -> List[Dict]:
        """Add relevance scores to keywords"""
        keywords_data = []
        
        # Batch calculate relevance for efficiency
        batch_size = 10
        for i in range(0, len(keywords), batch_size):
            batch = keywords[i:i + batch_size]
            scores = self.groq_client.batch_calculate_relevance(seed_keyword, batch)
            
            for kw in batch:
                keywords_data.append({
                    'keyword': kw,
                    'relevance_score': scores.get(kw, 0.5)
                })
            
            # Rate limiting
            if i + batch_size < len(keywords):
                time.sleep(0.5)
        
        return keywords_data
    
    def _analyze_competition(self, keywords_data: List[Dict]) -> List[Dict]:
        """Analyze competition for keywords"""
        for i, kw_data in enumerate(keywords_data):
            keyword = kw_data['keyword']
            
            print(f"   Analyzing {i+1}/{len(keywords_data)}: {keyword[:50]}...")
            
            try:
                analysis = self.serp_client.analyze_competition(keyword)
                
                # Add competition data to keyword
                kw_data.update({
                    'competition_score': analysis.get('competition_score', 50),
                    'big_brands_count': analysis.get('big_brands_count', 0),
                    'has_featured_snippet': analysis.get('has_featured_snippet', False),
                    'has_knowledge_graph': analysis.get('has_knowledge_graph', False),
                    'has_ads': analysis.get('has_ads', False),
                    'first_page_probability': analysis.get('first_page_probability', 0.5),
                    'total_results': analysis.get('total_results', 0),
                    'serp_features_count': analysis.get('serp_features_count', 0),
                    'top_domains': analysis.get('domains', [])[:5]
                })
                
            except Exception as e:
                print(f"   ⚠️  Error analyzing {keyword}: {str(e)}")
                # Add default values
                kw_data.update({
                    'competition_score': 50,
                    'big_brands_count': 0,
                    'has_featured_snippet': False,
                    'has_knowledge_graph': False,
                    'has_ads': False,
                    'first_page_probability': 0.5,
                    'total_results': 0,
                    'serp_features_count': 0,
                    'top_domains': []
                })
            
            # Rate limiting
            if i < len(keywords_data) - 1:
                time.sleep(self.api_delay)
        
        return keywords_data
    
    def _estimate_volumes(self, keywords_data: List[Dict]) -> List[Dict]:
        """Estimate search volumes"""
        for kw_data in keywords_data:
            keyword = kw_data['keyword']
            
            try:
                volume = self.trends_client.estimate_search_volume(keyword)
                kw_data['estimated_volume'] = volume
                
                # Get trend data
                if self.trends_client.enabled:
                    interest_data = self.trends_client.get_interest_over_time(keyword)
                    kw_data['trend'] = interest_data.get('trend', 'stable')
                    kw_data['average_interest'] = interest_data.get('average_interest', 50)
                
            except Exception as e:
                print(f"   ⚠️  Error estimating volume for {keyword}: {str(e)}")
                kw_data['estimated_volume'] = 1000  # Default
                kw_data['trend'] = 'stable'
        
        return keywords_data
    
    def save_results(self, results: Dict, output_dir: str = "output"):
        """Save results to file"""
        # Create output directory
        Path(output_dir).mkdir(exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        seed = results['seed_keyword'].replace(' ', '_')
        filename = f"{output_dir}/keywords_{seed}_{timestamp}.json"
        
        # Save JSON
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {filename}")
        
        return filename
    
    def print_summary(self, results: Dict):
        """Print summary of results"""
        print(f"\n{'='*60}")
        print(f"📊 RESULTS SUMMARY")
        print(f"{'='*60}\n")
        
        print(f"Seed Keyword: {results['seed_keyword']}")
        print(f"Total Keywords Analyzed: {results['total_keywords_analyzed']}")
        print(f"After Relevance Filter: {results['keywords_after_relevance_filter']}")
        print(f"Top Keywords Returned: {results['top_keywords_count']}")
        print(f"Execution Time: {results['execution_time_seconds']}s")
        
        print(f"\n{'='*60}")
        print(f"🏆 TOP 10 KEYWORDS")
        print(f"{'='*60}\n")
        
        for kw_data in results['top_keywords'][:10]:
            print(f"\n{kw_data['rank']}. {kw_data['keyword'].upper()}")
            print(f"   Opportunity Score: {kw_data['opportunity_score']:.1f}/100")
            print(f"   Competition: {kw_data['competition_score']}/100 ({kw_data['ranking_potential']['difficulty_category']})")
            print(f"   Est. Volume: {kw_data['estimated_volume']:,}/month")
            print(f"   Relevance: {kw_data['relevance_score']:.0%}")
            print(f"   First Page Probability: {kw_data['first_page_probability']:.0%}")
            print(f"   💡 {kw_data['ranking_potential']['recommendation']}")


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='SEO Keyword Research AI Agent'
    )
    parser.add_argument(
        '--seed',
        '-s',
        type=str,
        required=True,
        help='Seed keyword to research'
    )
    parser.add_argument(
        '--output',
        '-o',
        type=str,
        default='output',
        help='Output directory for results'
    )
    parser.add_argument(
        '--limit',
        '-l',
        type=int,
        default=50,
        help='Maximum number of keywords to return'
    )
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Do not save results to file'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize agent
        agent = SEOKeywordAgent()
        
        # Override max keywords if specified
        if args.limit:
            agent.max_keywords = args.limit
        
        # Run research
        results = agent.research_keywords(args.seed)
        
        # Print summary
        agent.print_summary(results)
        
        # Save results
        if not args.no_save:
            agent.save_results(results, args.output)
        
        print(f"\n{'='*60}")
        print("✅ SUCCESS! Research completed successfully.")
        print(f"{'='*60}\n")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Research interrupted by user.")
        return 1
    
    except Exception as e:
        print(f"\n\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())