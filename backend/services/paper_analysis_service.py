"""
Paper Analysis Service

Core service that combines all pipeline steps to analyze papers against project database.
Handles caching, similarity search, context building, and LLM analysis.
"""

import logging
import time
import uuid
import hashlib
import json
from typing import Dict, Any, List, Optional, Tuple
import sys
import os

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.llm_provider import get_gemini_model
from database.project_database import ProjectDatabase
from services.embed_projects import ProjectEmbeddingGenerator

logger = logging.getLogger(__name__)


class PaperAnalysisService:
    """
    Main service for analyzing papers against the project database
    
    Combines semantic search, context building, and LLM analysis
    """
    
    def __init__(self):
        self.llm_model = get_gemini_model("gemini-2.5-flash")
        self.db = ProjectDatabase()
        self.embedding_generator = ProjectEmbeddingGenerator()
        
        # Cost estimation for Gemini 2.5 Flash
        self.input_cost_per_1k_tokens = 0.00015  # $0.15 per 1M tokens
        self.output_cost_per_1k_tokens = 0.0006   # $0.60 per 1M tokens
    
    async def analyze_paper(
        self, 
        paper_text: str, 
        paper_id: Optional[str] = None,
        top_k: int = 4,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze a paper against the project database
        
        Args:
            paper_text: Paper abstract/summary text
            paper_id: Optional paper identifier
            top_k: Number of similar projects to retrieve
            use_cache: Whether to use cached results
            
        Returns:
            Structured analysis result
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            # Check cache first
            if use_cache:
                cached_result = await self.db.get_cached_analysis(paper_text)
                if cached_result:
                    logger.info(f"Cache hit for paper analysis")
                    
                    # Log cache hit
                    await self.db.log_cost(
                        operation_type='similarity_search',
                        cache_hit=True,
                        response_time_ms=int((time.time() - start_time) * 1000),
                        paper_id=paper_id,
                        request_id=request_id
                    )
                    
                    return {
                        'success': True,
                        'analysis': cached_result['llm_output'],
                        'similar_projects': cached_result['top_projects'],
                        'cached': True,
                        'cache_date': cached_result['created_at'],
                        'request_id': request_id
                    }
            
            # Step 1: Generate embedding for the paper
            paper_embedding = await self._embed_paper_text(paper_text, request_id, paper_id)
            if not paper_embedding:
                return {
                    'success': False,
                    'error': 'Failed to generate paper embedding',
                    'request_id': request_id
                }
            
            # Step 2: Find similar projects
            similar_projects = await self._find_similar_projects(paper_embedding, top_k, request_id, paper_id)
            if not similar_projects:
                return {
                    'success': False,
                    'error': 'No similar projects found',
                    'request_id': request_id
                }
            
            # Step 3: Build context from similar projects
            context_summary = self._build_context_summary(similar_projects)
            
            # Step 4: Generate LLM analysis
            analysis_result = await self._generate_investment_analysis(
                paper_text, 
                context_summary, 
                similar_projects,
                request_id,
                paper_id
            )
            
            if not analysis_result:
                return {
                    'success': False,
                    'error': 'Failed to generate analysis',
                    'request_id': request_id
                }
            
            # Step 5: Cache the result
            if use_cache:
                await self.db.cache_analysis_result(paper_text, similar_projects, analysis_result)
            
            return {
                'success': True,
                'analysis': analysis_result,
                'similar_projects': similar_projects,
                'cached': False,
                'processing_time_ms': int((time.time() - start_time) * 1000),
                'request_id': request_id
            }
            
        except Exception as e:
            logger.error(f"Error analyzing paper: {e}")
            return {
                'success': False,
                'error': str(e),
                'request_id': request_id
            }
        finally:
            await self.db.close_connection()
    
    async def _embed_paper_text(self, paper_text: str, request_id: str, paper_id: Optional[str]) -> Optional[List[float]]:
        """Generate embedding for paper text"""
        try:
            start_time = time.time()
            embedding = self.embedding_generator.embed_single_text(paper_text)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            if embedding:
                # Estimate cost
                estimated_tokens = len(paper_text) // 4
                cost_usd = (estimated_tokens / 1000) * self.embedding_generator.cost_per_1k_tokens
                
                # Log cost
                await self.db.log_cost(
                    operation_type='embedding',
                    tokens_input=estimated_tokens,
                    cost_usd=cost_usd,
                    response_time_ms=response_time_ms,
                    paper_id=paper_id,
                    request_id=request_id
                )
                
                return embedding
            else:
                logger.error("Failed to generate paper embedding")
                return None
                
        except Exception as e:
            logger.error(f"Error embedding paper text: {e}")
            return None
    
    async def _find_similar_projects(
        self, 
        paper_embedding: List[float], 
        top_k: int,
        request_id: str,
        paper_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Find similar projects using vector similarity"""
        try:
            start_time = time.time()
            similar_projects = await self.db.find_similar_projects(paper_embedding, top_k)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Log the similarity search
            await self.db.log_cost(
                operation_type='similarity_search',
                top_k_used=len(similar_projects),
                response_time_ms=response_time_ms,
                paper_id=paper_id,
                request_id=request_id
            )
            
            return similar_projects
            
        except Exception as e:
            logger.error(f"Error finding similar projects: {e}")
            return []
    
    def _build_context_summary(self, similar_projects: List[Dict[str, Any]]) -> str:
        """
        Build a compact context summary from similar projects
        
        Args:
            similar_projects: List of similar project dictionaries
            
        Returns:
            Compact context string for LLM
        """
        try:
            context_parts = []
            
            for i, project in enumerate(similar_projects, 1):
                # Extract key information
                title = project.get('title', 'Unknown Project')[:80]
                similarity = project.get('similarity_score', 0)
                
                # Get summary information
                summary = project.get('summary', {})
                if isinstance(summary, dict):
                    objective = summary.get('objective', '')[:100]
                    innovation_type = summary.get('innovation_type', 'Unknown')
                    potential_benefit = summary.get('potential_benefit', '')[:100]
                    readiness_level = summary.get('readiness_level', 'Unknown')
                    technical_domain = summary.get('technical_domain', 'Unknown')
                else:
                    # Fallback to abstract
                    objective = project.get('abstract', '')[:100]
                    innovation_type = 'Unknown'
                    potential_benefit = 'Unknown'
                    readiness_level = 'Unknown'
                    technical_domain = 'Unknown'
                
                # Institution and year
                institution = project.get('pi_institution', 'Unknown')[:50]
                fiscal_year = project.get('fiscal_year', 'Unknown')
                
                # Build compact description
                project_summary = (
                    f"Project {i} (similarity: {similarity:.3f}): {title} | "
                    f"Domain: {technical_domain} | Type: {innovation_type} | "
                    f"TRL: {readiness_level} | Institution: {institution} ({fiscal_year}) | "
                    f"Objective: {objective}"
                )
                
                if potential_benefit and potential_benefit != 'Unknown':
                    project_summary += f" | Benefits: {potential_benefit}"
                
                context_parts.append(project_summary)
            
            return '\n'.join(context_parts)
            
        except Exception as e:
            logger.error(f"Error building context summary: {e}")
            return "Context unavailable due to processing error."
    
    async def _generate_investment_analysis(
        self,
        paper_text: str,
        context_summary: str,
        similar_projects: List[Dict[str, Any]],
        request_id: str,
        paper_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Generate investment/research impact analysis using LLM
        
        Args:
            paper_text: Original paper text
            context_summary: Context from similar projects
            similar_projects: List of similar projects
            request_id: Request identifier
            paper_id: Paper identifier
            
        Returns:
            Structured analysis result
        """
        try:
            # Build the analysis prompt
            prompt = self._build_analysis_prompt(paper_text, context_summary)
            
            # Estimate input tokens
            estimated_input_tokens = len(prompt) // 4
            
            start_time = time.time()
            
            # Call LLM
            response = self.llm_model.generate_content(prompt)
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            if not response or not response.text:
                logger.error("Empty response from LLM for investment analysis")
                return None
            
            # Parse the structured response
            analysis = self._parse_analysis_response(response.text)
            
            if analysis:
                # Estimate output tokens and cost
                estimated_output_tokens = len(response.text) // 4
                cost_usd = (
                    (estimated_input_tokens / 1000) * self.input_cost_per_1k_tokens +
                    (estimated_output_tokens / 1000) * self.output_cost_per_1k_tokens
                )
                
                # Log cost
                await self.db.log_cost(
                    operation_type='llm_analysis',
                    tokens_input=estimated_input_tokens,
                    tokens_output=estimated_output_tokens,
                    cost_usd=cost_usd,
                    top_k_used=len(similar_projects),
                    response_time_ms=response_time_ms,
                    paper_id=paper_id,
                    request_id=request_id
                )
                
                # Add metadata to analysis
                analysis['analysis_metadata'] = {
                    'request_id': request_id,
                    'similar_projects_count': len(similar_projects),
                    'analysis_timestamp': time.time(),
                    'model_used': 'gemini-2.5-flash',
                    'estimated_cost_usd': cost_usd
                }
                
                return analysis
            else:
                logger.error("Failed to parse LLM analysis response")
                return None
                
        except Exception as e:
            logger.error(f"Error generating investment analysis: {e}")
            return None
    
    def _build_analysis_prompt(self, paper_text: str, context_summary: str) -> str:
        """Build the prompt for investment/research impact analysis"""
        
        prompt = f"""You are an expert AI investment analyst specializing in research and technology evaluation. Your task is to analyze a research paper's potential for innovation, technical feasibility, market potential, and societal impact based on similar projects in our database.

**PAPER TO ANALYZE:**
{paper_text}

**SIMILAR PROJECTS CONTEXT:**
Based on semantic similarity, here are the most relevant projects from our database:

{context_summary}

**ANALYSIS TASK:**
Please provide a comprehensive analysis with the following structured components:

1. **Innovation Assessment** (1-10 scale):
   - Novelty score and justification
   - Technical advancement level
   - Differentiation from existing work

2. **Technical Feasibility** (1-10 scale):
   - Implementation complexity
   - Resource requirements
   - Technology readiness indicators

3. **Market Potential** (1-10 scale):
   - Commercial viability
   - Market size and opportunity
   - Time to market estimation

4. **Societal Impact** (1-10 scale):
   - Potential benefits to society
   - Environmental impact
   - Accessibility and scalability

5. **Investment Recommendation**:
   - Overall score (1-10)
   - Risk assessment (Low/Medium/High)
   - Recommended investment stage (Early/Growth/Late)
   - Key success factors

6. **Comparative Analysis**:
   - How this research compares to similar projects
   - Advantages and disadvantages
   - Lessons learned from similar efforts

7. **Strategic Recommendations**:
   - Next steps for development
   - Potential partnerships or collaborations
   - Risk mitigation strategies

Please format your response as a valid JSON object with these exact field names:
{{
    "innovation_assessment": {{
        "novelty_score": <1-10>,
        "technical_advancement": <1-10>,
        "differentiation_score": <1-10>,
        "justification": "<explanation>"
    }},
    "technical_feasibility": {{
        "feasibility_score": <1-10>,
        "implementation_complexity": "<Low/Medium/High>",
        "resource_requirements": "<description>",
        "technology_readiness": <1-9>
    }},
    "market_potential": {{
        "market_score": <1-10>,
        "commercial_viability": "<Low/Medium/High>",
        "market_size": "<Small/Medium/Large>",
        "time_to_market_years": <estimate>
    }},
    "societal_impact": {{
        "impact_score": <1-10>,
        "environmental_benefit": "<Positive/Neutral/Negative>",
        "accessibility": "<Low/Medium/High>",
        "scalability": "<Low/Medium/High>"
    }},
    "investment_recommendation": {{
        "overall_score": <1-10>,
        "risk_level": "<Low/Medium/High>",
        "investment_stage": "<Early/Growth/Late>",
        "funding_priority": "<Low/Medium/High>",
        "key_success_factors": ["<factor1>", "<factor2>", "<factor3>"]
    }},
    "comparative_analysis": {{
        "advantages": ["<advantage1>", "<advantage2>"],
        "disadvantages": ["<disadvantage1>", "<disadvantage2>"],
        "similarity_insights": "<insights from similar projects>"
    }},
    "strategic_recommendations": {{
        "next_steps": ["<step1>", "<step2>", "<step3>"],
        "potential_partners": ["<partner_type1>", "<partner_type2>"],
        "risk_mitigation": ["<strategy1>", "<strategy2>"]
    }},
    "executive_summary": "<2-3 sentence summary of key findings and recommendation>"
}}

Ensure all scores are integers between the specified ranges, and all text fields are concise but informative.

JSON Response:"""

        return prompt
    
    def _parse_analysis_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse the LLM analysis response"""
        try:
            # Find JSON in response
            response_text = response_text.strip()
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_text = response_text[start_idx:end_idx + 1]
                analysis = json.loads(json_text)
                
                # Validate required top-level fields
                required_fields = [
                    'innovation_assessment', 'technical_feasibility', 'market_potential',
                    'societal_impact', 'investment_recommendation', 'comparative_analysis',
                    'strategic_recommendations', 'executive_summary'
                ]
                
                if all(field in analysis for field in required_fields):
                    return self._validate_analysis_structure(analysis)
                else:
                    logger.error(f"Missing required fields in analysis. Got: {list(analysis.keys())}")
                    return None
            else:
                logger.error("No valid JSON structure found in analysis response")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in analysis: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing analysis response: {e}")
            return None
    
    def _validate_analysis_structure(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean the analysis structure"""
        try:
            # Ensure all scores are within valid ranges
            innovation = analysis.get('innovation_assessment', {})
            for score_field in ['novelty_score', 'technical_advancement', 'differentiation_score']:
                score = innovation.get(score_field, 5)
                innovation[score_field] = max(1, min(10, int(score)))
            
            feasibility = analysis.get('technical_feasibility', {})
            feasibility['feasibility_score'] = max(1, min(10, int(feasibility.get('feasibility_score', 5))))
            feasibility['technology_readiness'] = max(1, min(9, int(feasibility.get('technology_readiness', 1))))
            
            market = analysis.get('market_potential', {})
            market['market_score'] = max(1, min(10, int(market.get('market_score', 5))))
            
            impact = analysis.get('societal_impact', {})
            impact['impact_score'] = max(1, min(10, int(impact.get('impact_score', 5))))
            
            investment = analysis.get('investment_recommendation', {})
            investment['overall_score'] = max(1, min(10, int(investment.get('overall_score', 5))))
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error validating analysis structure: {e}")
            return analysis


async def analyze_paper_against_projects(
    paper_text: str,
    paper_id: Optional[str] = None,
    top_k: int = 4,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to analyze a paper against the project database
    
    Args:
        paper_text: Paper abstract/summary text
        paper_id: Optional paper identifier
        top_k: Number of similar projects to retrieve
        use_cache: Whether to use cached results
        
    Returns:
        Analysis result dictionary
    """
    service = PaperAnalysisService()
    return await service.analyze_paper(paper_text, paper_id, top_k, use_cache)


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Example usage
    sample_paper = """
    This paper presents a novel machine learning approach for predicting climate change impacts 
    on agricultural yields using satellite imagery and weather data. Our method combines 
    convolutional neural networks with time series analysis to forecast crop productivity 
    with 85% accuracy. The system can process real-time data and provide early warning 
    systems for farmers and policymakers.
    """
    
    print("🔍 Analyzing sample paper...")
    result = analyze_paper_against_projects(sample_paper, "sample_001")
    
    if result['success']:
        analysis = result['analysis']
        print(f"\n📊 ANALYSIS RESULTS")
        print(f"   - Overall Score: {analysis.get('investment_recommendation', {}).get('overall_score', 'N/A')}/10")
        print(f"   - Risk Level: {analysis.get('investment_recommendation', {}).get('risk_level', 'N/A')}")
        print(f"   - Executive Summary: {analysis.get('executive_summary', 'N/A')}")
        print(f"   - Processing Time: {result.get('processing_time_ms', 'N/A')}ms")
        print(f"   - Cached: {result.get('cached', False)}")
    else:
        print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
