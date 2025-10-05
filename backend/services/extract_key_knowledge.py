"""
Step 3: LLM-based Key Knowledge Extraction

Uses Gemini 2.5 to extract structured summaries from project raw text.
Generates structured fields: Objective, Methodology, Key Findings, Innovation Type, Potential Benefit.
"""

import logging
import time
import json
from typing import Dict, Any, List, Optional
import sys
import os

# Add parent directories to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.llm_provider import get_gemini_model
from database.project_database import ProjectDatabase

logger = logging.getLogger(__name__)


class KeyKnowledgeExtractor:
    """Class to extract structured summaries from project descriptions using LLM"""
    
    def __init__(self):
        self.llm_model = get_gemini_model("gemini-2.5-flash")
        self.db = ProjectDatabase()
        
        # Cost estimation (approximate for Gemini 2.5 Flash)
        self.input_cost_per_1k_tokens = 0.00015  # $0.15 per 1M tokens
        self.output_cost_per_1k_tokens = 0.0006   # $0.60 per 1M tokens
    
    def extract_project_summaries(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Extract summaries for all projects without summaries
        
        Args:
            limit: Maximum number of projects to process
            
        Returns:
            Dictionary with processing statistics
        """
        try:
            # Get projects that need summaries
            projects = self.db.get_projects_without_summaries(limit)
            
            if not projects:
                logger.info("No projects found that need summaries")
                return {
                    'processed': 0,
                    'successful': 0,
                    'failed': 0,
                    'total_cost_usd': 0.0
                }
            
            logger.info(f"Processing {len(projects)} projects for key knowledge extraction")
            
            stats = {
                'processed': 0,
                'successful': 0,
                'failed': 0,
                'total_cost_usd': 0.0,
                'total_tokens_input': 0,
                'total_tokens_output': 0
            }
            
            for project in projects:
                try:
                    start_time = time.time()
                    
                    # Extract summary
                    summary, cost_info = self.extract_single_project_summary(project)
                    
                    if summary:
                        # Save to database
                        success = self.db.update_project_summary(project['project_id'], summary)
                        
                        if success:
                            stats['successful'] += 1
                            
                            # Log cost information
                            response_time_ms = int((time.time() - start_time) * 1000)
                            self.db.log_cost(
                                operation_type='llm_analysis',
                                tokens_input=cost_info['tokens_input'],
                                tokens_output=cost_info['tokens_output'],
                                cost_usd=cost_info['cost_usd'],
                                response_time_ms=response_time_ms,
                                paper_id=project['project_id']
                            )
                            
                            stats['total_cost_usd'] += cost_info['cost_usd']
                            stats['total_tokens_input'] += cost_info['tokens_input']
                            stats['total_tokens_output'] += cost_info['tokens_output']
                        else:
                            stats['failed'] += 1
                    else:
                        stats['failed'] += 1
                    
                    stats['processed'] += 1
                    
                    # Progress logging
                    if stats['processed'] % 10 == 0:
                        logger.info(f"Processed {stats['processed']}/{len(projects)} projects")
                    
                    # Small delay to avoid rate limiting
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error processing project {project['project_id']}: {e}")
                    stats['failed'] += 1
                    stats['processed'] += 1
                    continue
            
            logger.info(f"Summary extraction completed: {stats['successful']} successful, {stats['failed']} failed")
            logger.info(f"Total cost: ${stats['total_cost_usd']:.4f}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in extract_project_summaries: {e}")
            return stats
        finally:
            self.db.close_connection()
    
    def extract_single_project_summary(self, project: Dict[str, Any]) -> tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        """
        Extract structured summary for a single project
        
        Args:
            project: Project dictionary with raw_text
            
        Returns:
            Tuple of (summary_dict, cost_info)
        """
        try:
            raw_text = project.get('raw_text', '')
            
            if not raw_text:
                logger.warning(f"No raw text for project {project['project_id']}")
                return None, {'tokens_input': 0, 'tokens_output': 0, 'cost_usd': 0.0}
            
            # Create the prompt for structured extraction
            prompt = self._build_extraction_prompt(raw_text)
            
            # Estimate input tokens (rough approximation: 1 token ≈ 4 characters)
            estimated_input_tokens = len(prompt) // 4
            
            # Call LLM
            response = self.llm_model.generate_content(prompt)
            
            if not response or not response.text:
                logger.error(f"Empty response from LLM for project {project['project_id']}")
                return None, {'tokens_input': estimated_input_tokens, 'tokens_output': 0, 'cost_usd': 0.0}
            
            # Parse the structured response
            summary = self._parse_llm_response(response.text)
            
            # Estimate output tokens
            estimated_output_tokens = len(response.text) // 4
            
            # Calculate cost
            cost_usd = (
                (estimated_input_tokens / 1000) * self.input_cost_per_1k_tokens +
                (estimated_output_tokens / 1000) * self.output_cost_per_1k_tokens
            )
            
            cost_info = {
                'tokens_input': estimated_input_tokens,
                'tokens_output': estimated_output_tokens,
                'cost_usd': cost_usd
            }
            
            if summary:
                logger.info(f"Successfully extracted summary for project {project['project_id']}")
                return summary, cost_info
            else:
                logger.error(f"Failed to parse LLM response for project {project['project_id']}")
                return None, cost_info
            
        except Exception as e:
            logger.error(f"Error extracting summary for project {project['project_id']}: {e}")
            return None, {'tokens_input': 0, 'tokens_output': 0, 'cost_usd': 0.0}
    
    def _build_extraction_prompt(self, raw_text: str) -> str:
        """Build the prompt for LLM to extract structured information"""
        
        prompt = f"""You are an expert research analyst tasked with extracting structured information from project descriptions.

Please analyze the following project description and extract key information into a structured JSON format with these fields:

1. **Objective**: What is the main goal or purpose of this project? (1-2 sentences)
2. **Methodology**: What approach, methods, or techniques are being used? (1-2 sentences)  
3. **Key Findings**: What are the main results, discoveries, or outcomes? (1-2 sentences, or "Ongoing research" if not completed)
4. **Innovation Type**: What type of innovation does this represent? Choose from: ["Basic Research", "Applied Research", "Technology Development", "Process Innovation", "Product Development", "Other"]
5. **Potential Benefit**: What are the potential real-world applications or benefits? (1-2 sentences)
6. **Technical Domain**: What is the primary technical/scientific domain? (e.g., "Earth Sciences", "Materials Science", "Biotechnology", etc.)
7. **Readiness Level**: Estimate the technology readiness level from 1-9 (1=Basic research, 9=Operational system)

Project Description:
{raw_text}

Please respond with a valid JSON object containing these fields. Ensure your response is properly formatted JSON that can be parsed.

Example format:
{{
    "objective": "Develop new satellite imaging technology for...",
    "methodology": "Using machine learning algorithms and spectral analysis...",
    "key_findings": "Preliminary results show 15% improvement in...",
    "innovation_type": "Technology Development",
    "potential_benefit": "Could enable better climate monitoring and...",
    "technical_domain": "Earth Sciences",
    "readiness_level": 4
}}

JSON Response:"""

        return prompt
    
    def _parse_llm_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse the LLM response and extract the JSON structure
        
        Args:
            response_text: Raw LLM response
            
        Returns:
            Parsed summary dictionary or None
        """
        try:
            # Try to find JSON in the response
            response_text = response_text.strip()
            
            # Look for JSON block
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_text = response_text[start_idx:end_idx + 1]
                
                # Parse JSON
                summary = json.loads(json_text)
                
                # Validate required fields
                required_fields = ['objective', 'methodology', 'key_findings', 'innovation_type', 'potential_benefit']
                
                if all(field in summary for field in required_fields):
                    # Clean and validate the summary
                    return self._validate_and_clean_summary(summary)
                else:
                    logger.error(f"Missing required fields in summary. Got: {list(summary.keys())}")
                    return None
            else:
                logger.error("No valid JSON structure found in LLM response")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Response text: {response_text[:500]}...")
            return None
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return None
    
    def _validate_and_clean_summary(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean the extracted summary
        
        Args:
            summary: Raw summary dictionary
            
        Returns:
            Cleaned and validated summary
        """
        cleaned = {}
        
        # String fields - clean and truncate
        string_fields = ['objective', 'methodology', 'key_findings', 'potential_benefit', 'technical_domain']
        for field in string_fields:
            value = summary.get(field, '').strip()
            if value:
                # Truncate if too long
                cleaned[field] = value[:500] if len(value) > 500 else value
            else:
                cleaned[field] = 'Not specified'
        
        # Innovation type - validate against allowed values
        allowed_innovation_types = [
            'Basic Research', 'Applied Research', 'Technology Development', 
            'Process Innovation', 'Product Development', 'Other'
        ]
        
        innovation_type = summary.get('innovation_type', 'Other')
        if innovation_type in allowed_innovation_types:
            cleaned['innovation_type'] = innovation_type
        else:
            cleaned['innovation_type'] = 'Other'
        
        # Readiness level - validate as integer 1-9
        try:
            readiness_level = int(summary.get('readiness_level', 1))
            if 1 <= readiness_level <= 9:
                cleaned['readiness_level'] = readiness_level
            else:
                cleaned['readiness_level'] = 1
        except (ValueError, TypeError):
            cleaned['readiness_level'] = 1
        
        # Add extraction metadata
        cleaned['extraction_timestamp'] = time.time()
        cleaned['extraction_version'] = '1.0'
        
        return cleaned


def extract_all_project_summaries(limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Convenience function to extract summaries for all projects
    
    Args:
        limit: Maximum number of projects to process
        
    Returns:
        Processing statistics
    """
    extractor = KeyKnowledgeExtractor()
    return extractor.extract_project_summaries(limit)


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Extract key knowledge from projects')
    parser.add_argument('--limit', type=int, help='Maximum number of projects to process')
    args = parser.parse_args()
    
    # Run extraction
    print("🔍 Starting key knowledge extraction...")
    stats = extract_all_project_summaries(args.limit)
    
    print(f"\n📊 EXTRACTION RESULTS")
    print(f"   - Processed: {stats['processed']}")
    print(f"   - Successful: {stats['successful']}")
    print(f"   - Failed: {stats['failed']}")
    print(f"   - Total cost: ${stats['total_cost_usd']:.4f}")
    print(f"   - Input tokens: {stats['total_tokens_input']:,}")
    print(f"   - Output tokens: {stats['total_tokens_output']:,}")
