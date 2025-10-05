#!/usr/bin/env python3
"""
Step 4: Analyze Paper Against Projects

Analyze a research paper against the project database for investment insights.
Usage: python step4_analyze_paper.py [--paper-text "text"] [--paper-file path] [--paper-id id] [--top-k N]
"""

import sys
import os
import logging
import argparse
import json

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.paper_analysis_service import analyze_paper_against_projects
from database.project_database import ProjectDatabase

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to analyze paper against projects"""
    parser = argparse.ArgumentParser(description='Analyze research paper against project database')
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--paper-text', type=str, help='Paper text directly as argument')
    input_group.add_argument('--paper-file', type=str, help='Path to file containing paper text')
    input_group.add_argument('--interactive', action='store_true', help='Interactive mode - enter text manually')
    
    # Analysis options
    parser.add_argument('--paper-id', type=str, help='Optional paper identifier')
    parser.add_argument('--top-k', type=int, default=4, help='Number of similar projects to find (default: 4)')
    parser.add_argument('--no-cache', action='store_true', help='Disable caching')
    parser.add_argument('--output-file', type=str, help='Save results to JSON file')
    parser.add_argument('--check-status', action='store_true', help='Check system status before analysis')
    
    args = parser.parse_args()
    
    logger.info("🔍 Starting paper analysis...")
    
    try:
        # Check system status if requested
        if args.check_status:
            db = ProjectDatabase()
            try:
                stats = db.get_project_statistics()
                logger.info(f"📊 System status:")
                logger.info(f"   - Total projects: {stats.get('total_projects', 0)}")
                logger.info(f"   - With embeddings: {stats.get('projects_with_embeddings', 0)}")
                
                if stats.get('projects_with_embeddings', 0) == 0:
                    logger.error("❌ No projects have embeddings! Run steps 1-3 first.")
                    print("❌ No projects have embeddings! Run steps 1-3 first.")
                    return
                    
                logger.info("✅ System ready for analysis")
            finally:
                db.close_connection()
        
        # Get paper text
        paper_text = None
        
        if args.paper_text:
            paper_text = args.paper_text
        elif args.paper_file:
            if not os.path.exists(args.paper_file):
                logger.error(f"File not found: {args.paper_file}")
                sys.exit(1)
            
            with open(args.paper_file, 'r', encoding='utf-8') as f:
                paper_text = f.read().strip()
        elif args.interactive:
            print("Enter paper text (end with Ctrl+D on Unix/Linux or Ctrl+Z on Windows):")
            paper_text = sys.stdin.read().strip()
        
        if not paper_text:
            logger.error("No paper text provided")
            sys.exit(1)
        
        logger.info(f"📄 Paper text length: {len(paper_text)} characters")
        logger.info(f"🔍 Finding top {args.top_k} similar projects...")
        
        # Perform analysis
        result = analyze_paper_against_projects(
            paper_text=paper_text,
            paper_id=args.paper_id,
            top_k=args.top_k,
            use_cache=not args.no_cache
        )
        
        if not result['success']:
            logger.error(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
            print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
        
        # Extract results
        analysis = result['analysis']
        similar_projects = result['similar_projects']
        cached = result.get('cached', False)
        processing_time = result.get('processing_time_ms', 0)
        
        logger.info("✅ Analysis completed successfully!")
        
        # Print summary
        print(f"\n🎉 ANALYSIS COMPLETE")
        print(f"{'='*50}")
        
        print(f"\n📊 INVESTMENT RECOMMENDATION")
        investment = analysis.get('investment_recommendation', {})
        print(f"   Overall Score: {investment.get('overall_score', 'N/A')}/10")
        print(f"   Risk Level: {investment.get('risk_level', 'N/A')}")
        print(f"   Investment Stage: {investment.get('investment_stage', 'N/A')}")
        print(f"   Funding Priority: {investment.get('funding_priority', 'N/A')}")
        
        print(f"\n📈 DETAILED SCORES")
        innovation = analysis.get('innovation_assessment', {})
        feasibility = analysis.get('technical_feasibility', {})
        market = analysis.get('market_potential', {})
        impact = analysis.get('societal_impact', {})
        
        print(f"   Innovation: {innovation.get('novelty_score', 'N/A')}/10")
        print(f"   Feasibility: {feasibility.get('feasibility_score', 'N/A')}/10")
        print(f"   Market Potential: {market.get('market_score', 'N/A')}/10")
        print(f"   Societal Impact: {impact.get('impact_score', 'N/A')}/10")
        
        print(f"\n📝 EXECUTIVE SUMMARY")
        print(f"   {analysis.get('executive_summary', 'N/A')}")
        
        print(f"\n🔗 SIMILAR PROJECTS ({len(similar_projects)})")
        for i, project in enumerate(similar_projects, 1):
            similarity = project.get('similarity_score', 0)
            title = project.get('title', 'Unknown')[:60]
            institution = project.get('pi_institution', 'Unknown')[:30]
            print(f"   {i}. {title}... ({similarity:.3f}) - {institution}")
        
        print(f"\n⚡ PERFORMANCE")
        print(f"   Processing Time: {processing_time}ms")
        print(f"   Cached Result: {'Yes' if cached else 'No'}")
        print(f"   Request ID: {result.get('request_id', 'N/A')}")
        
        # Save to file if requested
        if args.output_file:
            with open(args.output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, default=str)
            logger.info(f"💾 Results saved to: {args.output_file}")
            print(f"\n💾 Results saved to: {args.output_file}")
        
        logger.info("🎉 Step 4 completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("❌ Analysis cancelled by user")
        print("\n❌ Analysis cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error during paper analysis: {e}")
        print(f"\n❌ FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
