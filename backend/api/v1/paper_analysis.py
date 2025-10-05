"""
FastAPI Router for Paper Analysis Pipeline

Provides REST endpoints for paper analysis, project management, and cost tracking.
Main endpoint: /analyze_paper for paper investment analysis.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
import json
import sys
import os
from datetime import datetime

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.project_database import ProjectDatabase
from utils.project_loader import load_projects_from_excel
from utils.llm_provider import get_gemini_model
from psycopg2.extras import RealDictCursor

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize services
db = ProjectDatabase()

# Pydantic models
class AnalyzePaperRequest(BaseModel):
    paper_id: str
    paper_text: Optional[str] = ""
    title: Optional[str] = "Unknown Title"
    user_query: Optional[str] = ""  # User's specific question or analysis request

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str

class AnalysisResponse(BaseModel):
    analysis: Dict[str, Any]
    message: str

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[str] = None


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="Paper Analysis API",
        version="1.0.0"
    )


@router.post("/analyze_paper")
async def analyze_paper(request: AnalyzePaperRequest):
    """
    Main endpoint for paper analysis against project database
    
    Expected JSON payload:
    {
        "paper_id": "PMCID or project_id to analyze",
        "paper_text": "Optional - paper abstract/summary if not in DB",
        "title": "Optional - paper title if not in DB"
    }
    """
    try:
        paper_id = request.paper_id.strip()
        if not paper_id:
            raise HTTPException(
                status_code=400,
                detail="paper_id is required and cannot be empty"
            )
        
        # Analysis with embedding-based similarity search
        result = await analyze_paper_with_similarity(
            paper_id, 
            request.paper_text.strip(),
            request.title,
            request.user_query.strip()
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in analyze_paper endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


async def analyze_paper_with_similarity(paper_id: str, fallback_text: str = "", fallback_title: str = "Unknown Title", user_query: str = ""):
    """
    Investment analysis using paper embeddings and similar projects
    """
    try:
        # Step 1: Get paper from database with embedding
        paper_data = db.get_paper_by_id(paper_id)
        
        if not paper_data:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": f"Paper with ID {paper_id} not found in database",
                    "message": f"Failed to find paper {paper_id}",
                    "suggestion": "Make sure the paper_id exists and has been processed"
                }
            )
        
        # Extract paper info - prioritize summarize over abstract
        paper_title = paper_data.get('title', fallback_title)
        paper_summarize = paper_data.get('summarize') or paper_data.get('summary') or paper_data.get('abstract', fallback_text)
        paper_embedding = paper_data.get('embeddings')
        
        if not paper_embedding:
            # Fallback: Use text-based analysis instead of embedding similarity
            logger.info(f"Paper {paper_id} has no embedding, using fallback analysis")
            return await analyze_paper_text_fallback(paper_id, paper_title, paper_summarize, user_query)
        
        # Step 2: Find top 4 similar projects
        similar_projects = db.find_similar_projects(paper_embedding, limit=4)
        
        # Step 3: Prepare analysis prompt with or without similar projects
        if similar_projects:
            # WITH similar projects
            projects_context = []
            for i, project in enumerate(similar_projects, 1):
                project_summary = f"""
Project {i}: {project.get('title', 'Unknown Title')}
Project ID: {project.get('project_id', 'Unknown')}
Fiscal Year: {project.get('fiscal_year', 'Unknown')}
Institution: {project.get('pi_institution', 'Unknown')}
Institution Type: {project.get('pi_institution_type', 'Unknown')}
Project Start Date: {project.get('project_start_date', 'Unknown')}
Project End Date: {project.get('project_end_date', 'Unknown')}
Solicitation Funding Source: {project.get('solicitation_funding_source', 'Unknown')}
Research Impact Earth Benefit: {project.get('research_impact_earth_benefit', 'Unknown')}
Abstract: {project.get('abstract', 'No abstract available')}
Raw Text: {project.get('raw_text', 'No raw text available')[:500]}{'...' if project.get('raw_text', '') and len(project.get('raw_text', '')) > 500 else ''}
Summary: {project.get('summary', 'No summary available')}
Similarity Score: {project.get('similarity_score', 0):.3f}
Created At: {project.get('created_at', 'Unknown')}
Updated At: {project.get('updated_at', 'Unknown')}
"""
                projects_context.append(project_summary.strip())
            
            # Analysis with similar projects
            analysis_method = "embedding_similarity_ai_powered"
            context_section = f"""
**SIMILAR EXISTING PROJECTS FOR CONTEXT (Complete Information):**
{chr(10).join(projects_context)}

**ANALYSIS TASK:**
Based on the target paper and similar existing projects, provide a comprehensive analysis. Consider how this paper compares to existing work, what unique value it offers, and its potential.
"""
        else:
            # WITHOUT similar projects - continue analysis anyway
            logger.info(f"No similar projects found for {paper_id}, continuing with paper-only analysis")
            analysis_method = "paper_only_ai_powered"
            context_section = """
**NO SIMILAR PROJECTS FOUND - PAPER-ONLY ANALYSIS**

**ANALYSIS TASK:**
Since no similar projects are available for comparison, provide a comprehensive analysis based solely on the paper content and general knowledge. Focus on the intrinsic value and potential of this research.
"""
        
        # Step 4: LLM Analysis with paper summarize + optional projects + user query
        llm_model = get_gemini_model()
        
        # Add user query section if provided
        user_query_section = ""
        if user_query.strip():
            user_query_section = f"""
**USER SPECIFIC QUESTION/REQUEST:**
{user_query}

Please address this specific question/request in your analysis.
"""
        
        # Create enhanced analysis prompt
        prompt = f"""You are an expert analyst specializing in research paper evaluation for investment, academic, and strategic decision making.

**TARGET PAPER FOR ANALYSIS (Summarize Only):**
Title: {paper_title}
Summarize: {paper_summarize}
{context_section}
{user_query_section}

Please provide your analysis in the following JSON format:

{{
    "overall_score": <float between 0-5>,
    "text_signals": {{
        "novelty": <float 0-1>,
        "applicability": <float 0-1>, 
        "sustainability": <float 0-1>,
        "readiness": <float 0-1>,
        "risk": <float 0-1>
    }},
    "metadata_analysis": {{
        "institution_score": <float 0-1>,
        "funding_score": <float 0-1>,
        "paper_age_years": <int>,
        "existing_score": <float 10-20>,
        "cluster": "<research cluster>",
        "topic": "<research domain>"
    }},
    "analysis_details": {{
        "strengths": ["strength 1", "strength 2"],
        "weaknesses": ["weakness 1", "weakness 2"],
        "potential": "<assessment>",
        "recommendation": "<recommendation>",
        "competitive_analysis": "<comparison insights>",
        "user_response": "<response to user query if provided>"
    }}
}}

Focus on providing realistic scores and actionable insights.

JSON Response:"""
        # Call LLM
        response = llm_model.generate_content(prompt)
        
        if not response or not response.text:
            raise Exception("Empty response from LLM")
        
        # Parse LLM response
        analysis_data = parse_llm_investment_response(response.text)
        
        if not analysis_data:
            raise Exception("Failed to parse LLM response")
        
        # Format response
        formatted_response = {
            "analysis": {
                "overall_score": analysis_data.get("overall_score", 2.5),
                "methodology": {
                    "analysis_method": analysis_method,
                    "text_signals": analysis_data.get("text_signals", {}),
                    "metadata_features": {
                        "title": paper_title,
                        "abstract": paper_summarize[:500] + "..." if len(paper_summarize) > 500 else paper_summarize,
                        "institution_score": analysis_data.get("metadata_analysis", {}).get("institution_score", 0.5),
                        "funding_score": analysis_data.get("metadata_analysis", {}).get("funding_score", 0.4),
                        "paper_age_years": analysis_data.get("metadata_analysis", {}).get("paper_age_years", 5),
                        "citation_rate": 0.0,
                        "total_citations": 0,
                        "reference_count": 0,
                        "existing_score": analysis_data.get("metadata_analysis", {}).get("existing_score", 12.5),
                        "cluster": analysis_data.get("metadata_analysis", {}).get("cluster", "unknown-cluster"),
                        "topic": analysis_data.get("metadata_analysis", {}).get("topic", "General Research")
                    },
                    "similar_projects": [
                        {
                            "project_id": proj.get("project_id"),
                            "title": proj.get("title"),
                            "similarity_score": proj.get("similarity_score"),
                            "institution": proj.get("pi_institution")
                        } for proj in similar_projects
                    ] if similar_projects else [],
                    "timestamp": datetime.now().isoformat()
                },
                "analysis_details": analysis_data.get("analysis_details", {}),
                "user_query": user_query if user_query.strip() else None
            },
            "message": f"Analysis completed for paper {paper_id}" + (f" with {len(similar_projects)} similar projects" if similar_projects else " (no similar projects found)")
        }
        
        return formatted_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in similarity-based investment analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Analysis failed: {str(e)}",
                "message": f"Failed to analyze paper {paper_id}"
            }
        )


async def analyze_paper_text_fallback(paper_id: str, paper_title: str, paper_summarize: str, user_query: str = ""):
    """
    Fallback analysis when paper doesn't have embedding - use all projects for context
    """
    try:
        # Get all projects with embeddings for general context
        conn = db.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get random sample of projects for context (instead of similarity-based)
        cursor.execute("""
            SELECT project_id, title, fiscal_year, pi_institution, pi_institution_type,
                   project_start_date, project_end_date, solicitation_funding_source,
                   research_impact_earth_benefit, abstract, raw_text, summary,
                   created_at, updated_at
            FROM projects 
            WHERE summary IS NOT NULL 
            ORDER BY RANDOM() 
            LIMIT 4
        """)
        
        context_projects = cursor.fetchall()
        cursor.close()
        
        if not context_projects:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "No projects available for context",
                    "message": f"No projects found in database for comparison"
                }
            )
        
        # Prepare full context for projects (all fields)
        projects_context = []
        for i, project in enumerate(context_projects, 1):
            project_info = f"""
Project {i}: {project.get('title', 'Unknown Title')}
Project ID: {project.get('project_id', 'Unknown')}
Fiscal Year: {project.get('fiscal_year', 'Unknown')}
Institution: {project.get('pi_institution', 'Unknown')}
Institution Type: {project.get('pi_institution_type', 'Unknown')}
Project Start Date: {project.get('project_start_date', 'Unknown')}
Project End Date: {project.get('project_end_date', 'Unknown')}
Solicitation Funding Source: {project.get('solicitation_funding_source', 'Unknown')}
Research Impact Earth Benefit: {project.get('research_impact_earth_benefit', 'Unknown')}
Abstract: {project.get('abstract', 'No abstract available')}
Raw Text: {project.get('raw_text', 'No raw text available')[:500]}{'...' if project.get('raw_text', '') and len(project.get('raw_text', '')) > 500 else ''}
Summary: {project.get('summary', 'No summary available')}
Created At: {project.get('created_at', 'Unknown')}
Updated At: {project.get('updated_at', 'Unknown')}
"""
            projects_context.append(project_info.strip())
        
        # LLM Analysis with paper summarize + full projects context
        llm_model = get_gemini_model()
        
        # Create analysis prompt (text-based instead of similarity-based)
        prompt = f"""You are an expert investment analyst specializing in research paper evaluation for venture capital and research funding decisions.

**TARGET PAPER FOR ANALYSIS (Summarize Only):**
Title: {paper_title}
Summarize: {paper_summarize}

**SAMPLE EXISTING PROJECTS FOR CONTEXT (Complete Information):**
{chr(10).join(projects_context)}

**ANALYSIS TASK:**
Based on the target paper and sample existing projects, provide a comprehensive investment analysis. Since we don't have similarity matching, focus on the paper's intrinsic value and potential compared to the general research landscape shown in the sample projects.

Please provide your analysis in the following JSON format:

{{
    "overall_score": <float between 0-5>,
    "text_signals": {{
        "novelty": <float 0-1, how novel this research appears>,
        "applicability": <float 0-1, commercial/practical applicability>,
        "sustainability": <float 0-1, long-term sustainability potential>,
        "readiness": <float 0-1, technology/market readiness level>,
        "risk": <float 0-1, investment risk assessment>
    }},
    "metadata_analysis": {{
        "institution_score": <float 0-1, quality of research institution>,
        "funding_score": <float 0-1, likelihood of securing funding>,
        "paper_age_years": <int, estimated age of research>,
        "existing_score": <float 10-20, competitiveness vs existing solutions>,
        "cluster": "<research cluster classification>",
        "topic": "<primary research domain/topic>"
    }},
    "investment_reasoning": {{
        "strengths": ["<key strength 1>", "<key strength 2>"],
        "weaknesses": ["<weakness 1>", "<weakness 2>"],
        "market_potential": "<brief market assessment>",
        "recommendation": "<invest/monitor/pass with brief reasoning>",
        "competitive_advantage": "<how it stands out from general research>",
        "context_analysis": "<brief analysis against the {len(context_projects)} sample projects shown>"
    }}
}}

Focus on:
1. Market potential and commercial viability
2. Technical innovation and competitive advantage
3. Research quality and execution feasibility
4. Risk factors and mitigation strategies
5. Timeline to market and funding requirements
6. How this research might advance the field

Provide realistic scores based on the actual content and research landscape.

JSON Response:"""

        # Call LLM
        response = llm_model.generate_content(prompt)
        
        if not response or not response.text:
            raise Exception("Empty response from LLM")
        
        # Parse LLM response
        analysis_data = parse_llm_investment_response(response.text)
        
        if not analysis_data:
            raise Exception("Failed to parse LLM response")
        
        # Format response
        formatted_response = {
            "analysis": {
                "overall_score": analysis_data.get("overall_score", 2.5),
                "methodology": {
                    "analysis_method": "text_based_ai_powered",
                    "text_signals": analysis_data.get("text_signals", {}),
                    "metadata_features": {
                        "title": paper_title,
                        "abstract": paper_summarize[:500] + "..." if len(paper_summarize) > 500 else paper_summarize,
                        "institution_score": analysis_data.get("metadata_analysis", {}).get("institution_score", 0.5),
                        "funding_score": analysis_data.get("metadata_analysis", {}).get("funding_score", 0.4),
                        "paper_age_years": analysis_data.get("metadata_analysis", {}).get("paper_age_years", 5),
                        "citation_rate": 0.0,
                        "total_citations": 0,
                        "reference_count": 0,
                        "existing_score": analysis_data.get("metadata_analysis", {}).get("existing_score", 12.5),
                        "cluster": analysis_data.get("metadata_analysis", {}).get("cluster", "unknown-cluster"),
                        "topic": analysis_data.get("metadata_analysis", {}).get("topic", "General Research")
                    },
                    "context_projects": [
                        {
                            "project_id": proj.get("project_id"),
                            "title": proj.get("title"),
                            "institution": proj.get("pi_institution"),
                            "research_impact": proj.get("research_impact_earth_benefit")
                        } for proj in context_projects
                    ],
                    "timestamp": datetime.now().isoformat()
                },
                "investment_details": analysis_data.get("investment_reasoning", {})
            },
            "message": f"Text-based investment analysis completed for paper {paper_id} with {len(context_projects)} context projects"
        }
        
        return formatted_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in text-based investment analysis: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Analysis failed: {str(e)}",
                "message": f"Failed to analyze paper {paper_id}"
            }
        )


def parse_llm_investment_response(response_text: str):
    """Parse LLM response and extract investment analysis data"""
    try:
        # Find JSON in response
        response_text = response_text.strip()
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_text = response_text[start_idx:end_idx + 1]
            analysis_data = json.loads(json_text)
            
            # Validate and clean the data
            return validate_investment_analysis(analysis_data)
        else:
            logger.error("No valid JSON found in LLM response")
            return None
            
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error parsing LLM response: {e}")
        return None


def validate_investment_analysis(data):
    """Validate and clean investment analysis data"""
    try:
        # Ensure required fields exist with defaults
        validated = {
            "overall_score": max(0, min(5, float(data.get("overall_score", 2.5)))),
            "text_signals": {
                "novelty": max(0, min(1, float(data.get("text_signals", {}).get("novelty", 0.5)))),
                "applicability": max(0, min(1, float(data.get("text_signals", {}).get("applicability", 0.5)))),
                "sustainability": max(0, min(1, float(data.get("text_signals", {}).get("sustainability", 0.5)))),
                "readiness": max(0, min(1, float(data.get("text_signals", {}).get("readiness", 0.5)))),
                "risk": max(0, min(1, float(data.get("text_signals", {}).get("risk", 0.5))))
            },
            "metadata_analysis": {
                "institution_score": max(0, min(1, float(data.get("metadata_analysis", {}).get("institution_score", 0.5)))),
                "funding_score": max(0, min(1, float(data.get("metadata_analysis", {}).get("funding_score", 0.4)))),
                "paper_age_years": max(1, min(20, int(data.get("metadata_analysis", {}).get("paper_age_years", 5)))),
                "existing_score": max(10, min(20, float(data.get("metadata_analysis", {}).get("existing_score", 12.5)))),
                "cluster": str(data.get("metadata_analysis", {}).get("cluster", "unknown-cluster")),
                "topic": str(data.get("metadata_analysis", {}).get("topic", "General Research"))
            },
            "investment_reasoning": data.get("investment_reasoning", {}),
            "analysis_details": data.get("analysis_details", {})
        }
        
        return validated
        
    except Exception as e:
        logger.error(f"Error validating investment analysis: {e}")
        return None


@router.post("/projects/upload")
async def upload_projects(file: UploadFile = File(...)):
    """Upload projects from Excel file"""
    try:
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="File must be an Excel file (.xlsx or .xls)"
            )
        
        # Save uploaded file temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file.flush()
            
            # Load projects from file
            projects = load_projects_from_excel(tmp_file.name)
            
            # Clean up temp file
            os.unlink(tmp_file.name)
        
        if not projects:
            raise HTTPException(
                status_code=400,
                detail="No valid projects found in file"
            )
        
        # Insert projects into database
        inserted, updated = db.insert_projects(projects)
        
        return {
            "success": True,
            "message": f"Successfully processed {len(projects)} projects",
            "inserted": inserted,
            "updated": updated,
            "total_projects": len(projects)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upload_projects endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload projects: {str(e)}"
        )


@router.get("/projects/stats")
async def get_project_stats():
    """Get statistics about projects in the database"""
    try:
        stats = db.get_project_statistics()
        
        return {
            "success": True,
            "statistics": stats
        }
        
    except Exception as e:
        logger.error(f"Error in get_project_stats endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get project statistics: {str(e)}"
        )


@router.get("/cost/summary")
async def get_cost_summary(days: int = 7):
    """Get cost summary for API usage"""
    try:
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=400,
                detail="days parameter must be between 1 and 365"
            )
        
        cost_summary = db.get_cost_summary(days)
        
        # Calculate totals
        total_requests = sum(row['total_requests'] for row in cost_summary)
        total_cost = sum(row['total_cost_usd'] for row in cost_summary)
        total_cache_hits = sum(row['cache_hits'] for row in cost_summary)
        
        cache_hit_rate = (total_cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "success": True,
            "period_days": days,
            "summary": {
                "total_requests": total_requests,
                "total_cost_usd": total_cost,
                "cache_hit_rate_percent": cache_hit_rate,
                "cost_per_request": total_cost / total_requests if total_requests > 0 else 0
            },
            "by_operation": cost_summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_cost_summary endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cost summary: {str(e)}"
        )
