import os
import json
import logging
import sys
from typing import List, Dict, Any, Optional
import vertexai
from utils.llm_provider import get_gemini_model



# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connect import connect, close_connection
from utils.embedding_provider import get_embedding_model


# Setup logging (same format as embed_ingestion)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KeyKnowledgeExtractor:
    def __init__(self):
        self.conn = None
        self.model = None
        self.embedding_model = None
        
    def initialize(self):
        """Initialize database connection, Gemini model, and embedding model"""
        try:
            # Connect to database
            self.conn = connect()
            logger.info("Database connection established")

            self.model = get_gemini_model()
            logger.info("Gemini model initialized")

            
            # Initialize embedding model using the same method as embed_ingestion
            self.embedding_model = get_embedding_model()
            logger.info("Embedding model initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            raise
        
        # Few-shot examples for prompt engineering
        self.few_shot_examples = """
Example 1:
Input: Title: "Deep Learning for Medical Image Analysis"
Abstract: "This paper presents a comprehensive study on applying deep learning techniques to medical image analysis. We propose a novel convolutional neural network architecture that achieves state-of-the-art performance on chest X-ray classification tasks."
Introduction: "Medical imaging plays a crucial role in modern healthcare diagnosis. Recent advances in deep learning have shown promising results in automating medical image interpretation..."

Output: [
    "deep learning medical image analysis",
    "convolutional neural network architecture", 
    "chest X-ray classification"
]

Example 2:
Input: Title: "Natural Language Processing for Social Media Sentiment Analysis"
Abstract: "We develop a transformer-based model for real-time sentiment analysis of social media posts. Our approach combines BERT embeddings with attention mechanisms to achieve 94% accuracy on Twitter data."
Introduction: "Social media platforms generate massive amounts of textual data daily. Understanding public sentiment from this data is crucial for businesses and researchers..."

Output: [
    "transformer-based sentiment analysis",
    "BERT embeddings attention mechanisms",
    "real-time social media analysis"
]

Example 3:
Input: Title: "Quantum Computing Applications in Cryptography"
Abstract: "This research explores the potential of quantum algorithms in breaking classical cryptographic systems. We implement Shor's algorithm and demonstrate its effectiveness against RSA encryption."
Introduction: "Quantum computing represents a paradigm shift in computational capabilities. The advent of quantum computers poses significant challenges to current cryptographic standards..."

Output: [
    "quantum algorithms cryptography",
    "Shor's algorithm RSA encryption",
    "quantum computing security threats"
]
"""

    def close(self):
        """Close database connection"""
        if self.conn:
            close_connection(self.conn)
            logger.info("Database connection closed")

    def create_extraction_prompt(self, title: str, abstract: str, introduction: str) -> str:
        """Create a well-engineered prompt for key knowledge extraction"""
        
        prompt = f"""
You are an expert AI research assistant specialized in extracting key knowledge concepts from academic papers.

TASK: Extract 3-5 key knowledge concepts from the given research paper content. These concepts should be:
- Specific technical terms, methods, or approaches
- Important domain concepts
- Novel contributions or findings
- Relevant applications or use cases
- Connected concepts that work together

GUIDELINES:
1. Focus on CONCRETE concepts, not generic terms
2. Combine related terms into meaningful phrases (2-4 words each)
3. Avoid overly broad terms like "machine learning" - be specific
4. Include both methodological and application concepts
5. Ensure concepts are searchable and meaningful for researchers

{self.few_shot_examples}

Now extract key knowledge from this paper:

Input: Title: "{title}"
Abstract: "{abstract}"
Introduction: "{introduction}"

Output: [
"""
        return prompt

    def extract_key_knowledge_with_gemini(self, title: str, abstract: str, introduction: str) -> List[str]:
        """Extract key knowledge using Gemini 2.5 Flash"""
        try:
            # Create the prompt
            prompt = self.create_extraction_prompt(title, abstract, introduction)

            
            
            # Generate response
            response = self.model.generate_content(
                prompt
            )
            
            # Check if response is valid and has text
            if not response or not response.text:
                logger.error("Gemini response is empty or invalid")
                return []

            # Parse the response
            response_text = response.text.strip()
            logger.info(f"Gemini response: {response_text}")
            
            # Extract the list part
            if "[" in response_text and "]" in response_text:
                start_idx = response_text.find("[")
                end_idx = response_text.find("]") + 1
                list_part = response_text[start_idx:end_idx]
                
                # Try to parse as JSON
                try:
                    key_knowledge_list = json.loads(list_part)
                    if isinstance(key_knowledge_list, list):
                        return [str(item).strip().lower() for item in key_knowledge_list if item.strip()]
                except json.JSONDecodeError:
                    pass
            
            # Fallback: extract lines that look like concepts
            lines = response_text.split('\n')
            concepts = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('[') and not line.startswith(']'):
                    # Remove quotes and clean up
                    line = line.strip('"').strip("'").strip(',').strip()
                    if line and len(line.split()) <= 6:  # Reasonable concept length
                        concepts.append(line.lower())
            
            return concepts[:8]  # Limit to 8 concepts
            
        except Exception as e:
            logger.error(f"Error extracting key knowledge with Gemini: {e}")
            return []
    
    def create_summarize_prompt(self, full_text: str) -> str:
        """Create a well-engineered prompt for summarizing full research paper text"""
        
        prompt = f"""
You are an expert AI research assistant specialized in creating comprehensive yet concise summaries of academic papers.

TASK: Analyze the ENTIRE research paper content below and create a structured summary that captures:

1. Main Research Problem: What problem or question is being addressed?
2. Key Methodology: What approach, methods, or techniques were used?
3. Primary Findings: What are the main results or discoveries?
4. Significant Contributions: What new knowledge or innovations does this work provide?
5. Practical Implications: How can this research be applied or what impact does it have?

SUMMARY REQUIREMENTS:
- Write in clear, academic language
- Be comprehensive but concise (aim for 200-300 words)
- Focus on the most important aspects that make this paper valuable
- Include specific technical details and quantitative results when mentioned
- Maintain objective, scientific tone
- Structure the summary in a coherent narrative flow

FORMATTING:
- Write as a single, well-structured paragraph
- Do not use bullet points or numbered lists
- Include the most important technical terms and concepts
- Ensure the summary would help researchers quickly understand the paper's value

FULL PAPER TEXT TO SUMMARIZE:
{full_text}

Based on your analysis of the complete paper above, provide a comprehensive summary:

SUMMARY:"""
        return prompt

    def summarize_paper_with_gemini(self, full_text: str) -> str:
        """Generate paper summary using Gemini 2.5 Flash"""
        try:
            # Create the summarization prompt
            prompt = self.create_summarize_prompt(full_text)
            
            # Generate response
            response = self.model.generate_content(prompt)
            
            # Check if response is valid and has text
            if not response or not response.text:
                logger.error("Gemini summary response is empty or invalid")
                return ""

            # Parse the response
            summary_text = response.text.strip()
            
            # Clean up the summary - remove any "SUMMARY:" prefix if present
            if summary_text.upper().startswith("SUMMARY:"):
                summary_text = summary_text[8:].strip()
            
            logger.info(f"Generated summary ({len(summary_text)} chars)")
            return summary_text
            
        except Exception as e:
            logger.error(f"Error generating summary with Gemini: {e}")
            return ""

    def extract_key_knowledge_from_full_text(self, full_text: str) -> List[str]:
        """Extract key knowledge using Gemini 2.5 Flash from complete paper text"""
        try:
            # Create the prompt for full text analysis
            prompt = f"""
You are an expert AI research assistant specialized in extracting key knowledge concepts from complete academic papers.

TASK: Analyze the ENTIRE research paper content below and extract 4-6 key knowledge concepts that represent the most important and unique contributions of this work. These concepts should be:

PRIORITY EXTRACTION TARGETS:
1. **Novel methodologies or algorithms** - New techniques, models, or approaches introduced
2. **Specific technical innovations** - Unique implementations, architectures, or processes
3. **Domain-specific applications** - Particular use cases, datasets, or problem domains addressed
4. **Measurable outcomes or findings** - Quantified results, performance metrics, or discoveries
5. **Interdisciplinary connections** - Cross-field applications or hybrid approaches
6. **Practical implementations** - Real-world systems, tools, or deployments

EXTRACTION GUIDELINES:
- Read through ALL sections: Abstract, Introduction, Methods, Results, Discussion, Conclusion
- Focus on CONCRETE and SPECIFIC concepts (avoid generic terms like "machine learning")
- Combine related technical terms into meaningful 2-5 word phrases
- Prioritize concepts that appear multiple times or are emphasized in different sections
- Include both the HOW (methodology) and the WHAT (application/domain)
- Ensure concepts are searchable and would help researchers find this paper
- Avoid overly broad terms - be as specific as possible

FORMATTING REQUIREMENTS:
- Each concept should be 2-5 words maximum
- Use lowercase letters
- Focus on noun phrases that capture essence
- Combine related terms with spaces (not hyphens or underscores)

{self.few_shot_examples}

FULL PAPER TEXT:
{full_text}

Based on your analysis of the entire paper above, extract the most important key knowledge concepts:

Output: ["""
            
            # Generate response
            response = self.model.generate_content(prompt)
            
            # Check if response is valid and has text
            if not response or not response.text:
                logger.error("Gemini response is empty or invalid")
                return []

            # Parse the response
            response_text = response.text.strip()
            logger.info(f"Gemini full-text response: {response_text[:200]}...")
            
            # Extract the list part
            if "[" in response_text and "]" in response_text:
                start_idx = response_text.find("[")
                end_idx = response_text.find("]") + 1
                list_part = response_text[start_idx:end_idx]
                
                # Try to parse as JSON
                try:
                    key_knowledge_list = json.loads(list_part)
                    if isinstance(key_knowledge_list, list):
                        return [str(item).strip().lower() for item in key_knowledge_list if item.strip()]
                except json.JSONDecodeError:
                    pass
            
            # Fallback: extract lines that look like concepts
            lines = response_text.split('\n')
            concepts = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('[') and not line.startswith(']'):
                    # Remove quotes and clean up
                    line = line.strip('"').strip("'").strip(',').strip()
                    if line and len(line.split()) <= 6:  # Reasonable concept length
                        concepts.append(line.lower())
            
            return concepts[:8]  # Limit to 8 concepts
            
        except Exception as e:
            logger.error(f"Error extracting key knowledge from full text with Gemini: {e}")
            return []

    def update_paper_summary(self, paper_db_id: int, paper_id: str, summary: str) -> bool:
        """Update paper table with generated summary"""
        try:
            cursor = self.conn.cursor()
            
            # Check if the paper table has a summarize column, if not add it
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'paper' AND column_name = 'summarize'
            """)
            
            if not cursor.fetchone():
                # Add summarize column if it doesn't exist
                cursor.execute("""
                    ALTER TABLE paper 
                    ADD COLUMN IF NOT EXISTS summarize TEXT
                """)
                logger.info("Added summarize column to paper table")
            
            # Update the paper with summary
            update_query = """
                UPDATE paper 
                SET summarize = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            
            cursor.execute(update_query, (summary, paper_db_id))
            
            if cursor.rowcount > 0:
                self.conn.commit()
                logger.info(f"Updated summary for paper {paper_id}")
                return True
            else:
                logger.warning(f"No paper found with id {paper_db_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating summary for paper {paper_id}: {e}")
            if self.conn:
                self.conn.rollback()
            return False
        finally:
            cursor.close()

    def generate_embeddings(self, key_knowledge_list: List[str]) -> List[List[float]]:
        """Generate embeddings for key knowledge concepts using Vertex AI (same as embed_ingestion)"""
        try:
            if not key_knowledge_list:
                return []
                
            # Generate embeddings using Vertex AI - same method as embed_ingestion
            embeddings = []
            for concept in key_knowledge_list:
                try:
                    # Get embedding from Vertex AI using same pattern as embed_ingestion
                    embedding_response = self.embedding_model.get_embeddings([concept])
                    embedding_vector = embedding_response[0].values
                    embeddings.append(embedding_vector)
                    
                except Exception as e:
                    logger.error(f"Error generating embedding for concept '{concept}': {e}")
                    continue
            
            logger.info(f"Generated {len(embeddings)} embeddings using Vertex AI")
            if embeddings:
                logger.info(f"Embedding dimension: {len(embeddings[0])}")
            
            return embeddings
                
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return []

    def insert_key_knowledge(self, paper_db_id: int, paper_id: str, key_knowledge_list: List[str]) -> List[str]:
        """Insert key knowledge with embeddings into database (same pattern as embed_ingestion)"""
        try:
            cursor = self.conn.cursor()
            inserted_ids = []
            
            # Generate embeddings for all concepts
            embeddings = self.generate_embeddings(key_knowledge_list)
            
            if len(embeddings) != len(key_knowledge_list):
                logger.warning(f"Embedding count mismatch: {len(embeddings)} vs {len(key_knowledge_list)}")
                return []
            
            # Insert each concept
            for i, concept in enumerate(key_knowledge_list):
                try:
                    embedding = embeddings[i]
                    
                    # Convert embedding to PostgreSQL vector format (same as embed_ingestion)
                    embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                    
                    # Store concept with paper_id reference
                    context_data = [concept]  # Simple array with just the concept
                    
                    insert_query = """
                    INSERT INTO key_knowledge (
                        paper_id,
                        context,
                        embedding,
                        created_at,
                        updated_at
                    ) VALUES (%s, %s, %s::vector, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING id
                    """
                    
                    cursor.execute(insert_query, (
                        paper_db_id,  # Use the integer ID for foreign key
                        context_data,  # Store as array with concept
                        embedding_str
                    ))
                    
                    concept_id = cursor.fetchone()[0]
                    inserted_ids.append(concept_id)
                    
                    logger.debug(f"Inserted key knowledge: '{concept}' for paper {paper_id} with ID: {concept_id}")
                    
                except Exception as e:
                    logger.error(f"Error inserting concept '{concept}': {e}")
                    continue
            
            self.conn.commit()
            cursor.close()
            
            logger.info(f"Successfully inserted {len(inserted_ids)} key knowledge concepts for paper {paper_id}")
            return inserted_ids
            
        except Exception as e:
            logger.error(f"Error inserting key knowledge for paper {paper_id}: {e}")
            if self.conn:
                self.conn.rollback()
            return []

    def get_papers_for_key_knowledge(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch papers from database that need key knowledge extraction
        
        Args:
            limit: Maximum number of papers to fetch (None for all)
            
        Returns:
            List of paper dictionaries with id, paper_id, title, abstract, full_text, and json_data
        """
        try:
            cursor = self.conn.cursor()
            
            query = """
                SELECT id, paper_id, title, abstract, full_text, json_data
                FROM paper
                WHERE title IS NOT NULL
                ORDER BY id
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            papers = cursor.fetchall()
            
            papers_list = [
                {
                    'id': paper[0],  # This is the integer ID for foreign key
                    'paper_id': str(paper[1]),  # This is the text paper_id
                    'title': paper[2],
                    'abstract': paper[3] or '',  # Use empty string if abstract is None
                    'full_text': paper[4] or '',  # Use empty string if full_text is None
                    'json_data': paper[5] or {}  # Use empty dict if json_data is None
                }
                for paper in papers
            ]
            
            cursor.close()
            logger.info(f"Found {len(papers_list)} papers in database")
            return papers_list
            
        except Exception as e:
            logger.error(f"Error fetching papers: {e}")
            raise

    def process_paper_for_key_knowledge(self, paper_data: Dict[str, Any]) -> List[str]:
        """Process a single paper to extract and store key knowledge and generate summary"""
        try:
            paper_db_id = paper_data['id']  # Integer ID for foreign key
            paper_id = paper_data['paper_id']  # Text paper ID for display
            title = paper_data.get('title', '')
            abstract = paper_data.get('abstract', '')
            full_text = paper_data.get('full_text', '')
            
            # Try to extract introduction from json_data if available
            introduction = ""
            json_data = paper_data.get('json_data', {})
            if isinstance(json_data, dict):
                sections = json_data.get("sections", {})
                if sections and isinstance(sections, dict):
                    if "introduction" in sections:
                        if isinstance(sections["introduction"], dict) and "_content" in sections["introduction"]:
                            introduction = sections["introduction"]["_content"]
                    elif "intro" in sections:
                        if isinstance(sections["intro"], dict) and "_content" in sections["intro"]:
                            introduction = sections["intro"]["_content"]
            
            logger.info(f"Processing paper {paper_id}")
            logger.info(f"  Title: {title[:50]}...")
            logger.info(f"  Abstract length: {len(abstract)} chars")
            logger.info(f"  Introduction length: {len(introduction)} chars")
            logger.info(f"  Full text length: {len(full_text)} chars")
            
            # Step 1: Generate and save summary if full_text is available
            logger.info(f"Generating summary from full text for paper {paper_id}")
            summary = self.summarize_paper_with_gemini(full_text)
            
            if summary:
                self.update_paper_summary(paper_db_id, paper_id, summary)
                logger.info(f"Summary generated and saved for paper {paper_id}")
            else:
                logger.warning(f"Failed to generate summary for paper {paper_id}")
            
            # Step 2: Extract key knowledge
            # Prefer full_text if available, otherwise use title + abstract + introduction
             
                
            # Truncate content if too long
            title = title[:200] if title else ""
            abstract = abstract[:1000] if abstract else ""
            introduction = introduction[:1500] if introduction else ""
            
            logger.info(f"Extracting key knowledge from title/abstract/intro for paper {paper_id}")
            key_knowledge = self.extract_key_knowledge_with_gemini(title, abstract, introduction)
            
            if not key_knowledge:
                logger.warning(f"No key knowledge extracted for paper {paper_id}")
                return []
            
            logger.info(f"Extracted {len(key_knowledge)} concepts: {key_knowledge}")
            
            # Insert into database
            inserted_ids = self.insert_key_knowledge(paper_db_id, paper_id, key_knowledge)
            
            return inserted_ids
            
        except Exception as e:
            logger.error(f"Error processing paper {paper_data.get('paper_id', 'unknown')} for key knowledge: {e}")
            return []

def process_papers_for_key_knowledge(limit: Optional[int] = None):
    """Process papers from database to extract key knowledge (same pattern as embed_ingestion)"""
    
    # Initialize extractor using same pattern as embed_ingestion
    extractor = KeyKnowledgeExtractor()
    
    try:
        # Initialize the extractor (same as embed_ingestion.initialize())
        extractor.initialize()
        
        # Fetch papers from database
        papers = extractor.get_papers_for_key_knowledge(limit=limit)
        
        if not papers:
            logger.info("No papers found in database that need key knowledge extraction")
            return
        
        total_papers = len(papers)
        total_concepts = 0
        successful_papers = 0
        
        print(f"\nProcessing {total_papers} papers for key knowledge extraction...")
        
        for i, paper_data in enumerate(papers, 1):
            try:
                logger.info(f"\nProcessing paper {i}/{total_papers}: {paper_data['paper_id']}")
                
                # Process paper
                inserted_ids = extractor.process_paper_for_key_knowledge(paper_data)
                
                if inserted_ids:
                    successful_papers += 1
                    total_concepts += len(inserted_ids)
                    logger.info(f"Successfully processed paper {paper_data['paper_id']}: {len(inserted_ids)} concepts")
                else:
                    logger.warning(f"Failed to process paper {paper_data['paper_id']}")
                    
                # Progress update every 10 papers
                if i % 10 == 0:
                    logger.info(f"Progress: {i}/{total_papers} papers processed")
                        
            except Exception as e:
                logger.error(f"Error processing paper {paper_data.get('paper_id', 'unknown')}: {e}")

        # Summary
        logger.info("=" * 60)
        logger.info(f"Key Knowledge Extraction Completed!")
        logger.info(f"Total papers: {total_papers}")
        logger.info(f"Successful extractions: {successful_papers}")
        logger.info(f"Total concepts extracted: {total_concepts}")
        logger.info(f"Average concepts per paper: {total_concepts/successful_papers if successful_papers > 0 else 0:.1f}")
        logger.info("=" * 60)
        
        print(f"Successfully extracted {total_concepts} key knowledge concepts from {successful_papers} papers!")
        
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user")
    except Exception as e:
        logger.error(f"Error in key knowledge processing: {e}")
        raise
    finally:
        extractor.close()

def main():
    """Main function - simple call to process papers"""
    process_papers_for_key_knowledge()

if __name__ == "__main__":
    main()
