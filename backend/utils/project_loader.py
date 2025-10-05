"""
Project Data Loader

Reads Excel files with project data, normalizes columns,
and combines textual content into raw_text field for LLM processing.
"""

import pandas as pd
import uuid
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


class ProjectLoader:
    """Class to handle loading and normalizing project data from Excel files"""
    
    def __init__(self):
        self.required_columns = [
            'Research Impact/Earth Benefit',
            'PI Institution', 
            'PI Institution Type',
            'Project Title',
            'Fiscal Year',
            'Solicitation/Funding Source',
            'Project Start Date',
            'Project End Date',
            'Task Abstract/Description'
        ]
    
    def load_projects(self, excel_file_path: str) -> List[Dict[str, Any]]:
        """
        Load projects from Excel file and normalize data
        
        Args:
            excel_file_path: Path to the Excel file
            
        Returns:
            List of normalized project dictionaries
        """
        try:
            # Read Excel file
            logger.info(f"Loading projects from: {excel_file_path}")
            df = pd.read_excel(excel_file_path)
            
            # Log basic info about the file
            logger.info(f"Loaded {len(df)} rows with columns: {list(df.columns)}")
            
            # Validate required columns
            missing_columns = self._validate_columns(df.columns)
            if missing_columns:
                logger.warning(f"Missing expected columns: {missing_columns}")
            
            # Normalize and process each row
            projects = []
            for index, row in df.iterrows():
                try:
                    project = self._normalize_project_row(row, index)
                    if project:
                        projects.append(project)
                except Exception as e:
                    logger.error(f"Error processing row {index}: {e}")
                    continue
            
            logger.info(f"Successfully processed {len(projects)} projects")
            return projects
            
        except Exception as e:
            logger.error(f"Error loading Excel file: {e}")
            raise
    
    def _validate_columns(self, columns: List[str]) -> List[str]:
        """Check for missing required columns"""
        available_columns = set(columns)
        required_columns = set(self.required_columns)
        missing = list(required_columns - available_columns)
        return missing
    
    def _normalize_project_row(self, row: pd.Series, row_index: int) -> Optional[Dict[str, Any]]:
        """
        Normalize a single project row into standardized format
        
        Args:
            row: Pandas Series representing one project
            row_index: Row index for error tracking
            
        Returns:
            Normalized project dictionary or None if invalid
        """
        try:
            # Generate unique project ID
            project_id = self._generate_project_id(row, row_index)
            
            # Extract and clean basic fields
            title = self._clean_text(row.get('Project Title', ''))
            abstract = self._clean_text(row.get('Task Abstract/Description', ''))
            
            # Skip if no title or abstract
            if not title and not abstract:
                logger.warning(f"Row {row_index}: No title or abstract, skipping")
                return None
            
            # Parse dates
            start_date = self._parse_date(row.get('Project Start Date'))
            end_date = self._parse_date(row.get('Project End Date'))
            
            # Parse fiscal year
            fiscal_year = self._parse_fiscal_year(row.get('Fiscal Year'))
            
            # Build raw_text by combining all relevant textual columns
            raw_text = self._build_raw_text(row)
            
            # Create normalized project object
            project = {
                'project_id': project_id,
                'title': title,
                'abstract': abstract,
                'fiscal_year': fiscal_year,
                'pi_institution': self._clean_text(row.get('PI Institution', '')),
                'pi_institution_type': self._clean_text(row.get('PI Institution Type', '')),
                'project_start_date': start_date,
                'project_end_date': end_date,
                'solicitation_funding_source': self._clean_text(row.get('Solicitation/Funding Source', '')),
                'research_impact_earth_benefit': self._clean_text(row.get('Research Impact/Earth Benefit', '')),
                'raw_text': raw_text,
                'row_index': row_index  # For debugging purposes
            }
            
            return project
            
        except Exception as e:
            logger.error(f"Error normalizing row {row_index}: {e}")
            return None
    
    def _generate_project_id(self, row: pd.Series, row_index: int) -> str:
        """Generate a unique project ID"""
        # Try to use title + fiscal year for deterministic ID
        title = str(row.get('Project Title', ''))
        fiscal_year = str(row.get('Fiscal Year', ''))
        
        if title:
            # Create hash-based ID for consistency
            content = f"{title}_{fiscal_year}_{row_index}"
            hash_obj = hashlib.md5(content.encode())
            return f"proj_{hash_obj.hexdigest()[:8]}"
        else:
            # Fallback to UUID
            return f"proj_{str(uuid.uuid4())[:8]}"
    
    def _clean_text(self, text: Any) -> str:
        """Clean and normalize text fields"""
        if pd.isna(text) or text is None:
            return ""
        
        # Convert to string and strip whitespace
        text_str = str(text).strip()
        
        # Remove extra whitespace
        text_str = ' '.join(text_str.split())
        
        return text_str
    
    def _parse_date(self, date_value: Any) -> Optional[str]:
        """Parse date value into ISO format string"""
        if pd.isna(date_value) or date_value is None:
            return None
            
        try:
            # If it's already a datetime object
            if isinstance(date_value, datetime):
                return date_value.date().isoformat()
            
            # If it's a string, try to parse it
            if isinstance(date_value, str):
                parsed_date = pd.to_datetime(date_value, errors='coerce')
                if not pd.isna(parsed_date):
                    return parsed_date.date().isoformat()
            
            return None
            
        except Exception:
            return None
    
    def _parse_fiscal_year(self, year_value: Any) -> Optional[int]:
        """Parse fiscal year into integer"""
        if pd.isna(year_value) or year_value is None:
            return None
            
        try:
            # Convert to int
            year = int(float(year_value))
            
            # Sanity check (reasonable range for fiscal years)
            if 1990 <= year <= 2030:
                return year
            
        except (ValueError, TypeError):
            pass
            
        return None
    
    def _build_raw_text(self, row: pd.Series) -> str:
        """
        Combine all relevant textual columns into a single raw_text field
        for LLM processing
        """
        text_components = []
        
        # Define the order of fields to include
        text_fields = [
            ('Project Title', 'Title'),
            ('Task Abstract/Description', 'Abstract'),
            ('Research Impact/Earth Benefit', 'Research Impact'),
            ('Solicitation/Funding Source', 'Funding Source'),
            ('PI Institution', 'Institution'),
            ('PI Institution Type', 'Institution Type')
        ]
        
        for field_name, label in text_fields:
            value = self._clean_text(row.get(field_name, ''))
            if value:
                text_components.append(f"{label}: {value}")
        
        # Add dates if available
        start_date = self._parse_date(row.get('Project Start Date'))
        end_date = self._parse_date(row.get('Project End Date'))
        fiscal_year = self._parse_fiscal_year(row.get('Fiscal Year'))
        
        if start_date:
            text_components.append(f"Start Date: {start_date}")
        if end_date:
            text_components.append(f"End Date: {end_date}")
        if fiscal_year:
            text_components.append(f"Fiscal Year: {fiscal_year}")
        
        return '\n'.join(text_components)
    
    def validate_projects(self, projects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate loaded projects and return statistics
        
        Args:
            projects: List of project dictionaries
            
        Returns:
            Dictionary with validation statistics
        """
        stats = {
            'total_projects': len(projects),
            'projects_with_title': 0,
            'projects_with_abstract': 0,
            'projects_with_dates': 0,
            'unique_institutions': set(),
            'fiscal_year_range': [],
            'average_raw_text_length': 0
        }
        
        text_lengths = []
        
        for project in projects:
            if project.get('title'):
                stats['projects_with_title'] += 1
            
            if project.get('abstract'):
                stats['projects_with_abstract'] += 1
            
            if project.get('project_start_date') and project.get('project_end_date'):
                stats['projects_with_dates'] += 1
            
            if project.get('pi_institution'):
                stats['unique_institutions'].add(project['pi_institution'])
            
            if project.get('fiscal_year'):
                stats['fiscal_year_range'].append(project['fiscal_year'])
            
            if project.get('raw_text'):
                text_lengths.append(len(project['raw_text']))
        
        # Calculate derived statistics
        stats['unique_institutions'] = len(stats['unique_institutions'])
        
        if stats['fiscal_year_range']:
            stats['fiscal_year_range'] = [
                min(stats['fiscal_year_range']), 
                max(stats['fiscal_year_range'])
            ]
        
        if text_lengths:
            stats['average_raw_text_length'] = sum(text_lengths) / len(text_lengths)
        
        return stats


def load_projects_from_excel(excel_file_path: str) -> List[Dict[str, Any]]:
    """
    Convenience function to load projects from Excel file
    
    Args:
        excel_file_path: Path to the Excel file
        
    Returns:
        List of normalized project dictionaries
    """
    loader = ProjectLoader()
    return loader.load_projects(excel_file_path)


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python project_loader.py <excel_file_path>")
        sys.exit(1)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Load projects
    excel_path = sys.argv[1]
    projects = load_projects_from_excel(excel_path)
    
    # Validate and show statistics
    loader = ProjectLoader()
    stats = loader.validate_projects(projects)
    
    print(f"\n📊 PROJECT LOADING STATISTICS")
    print(f"   - Total projects loaded: {stats['total_projects']}")
    print(f"   - Projects with title: {stats['projects_with_title']}")
    print(f"   - Projects with abstract: {stats['projects_with_abstract']}")
    print(f"   - Projects with dates: {stats['projects_with_dates']}")
    print(f"   - Unique institutions: {stats['unique_institutions']}")
    print(f"   - Fiscal year range: {stats['fiscal_year_range']}")
    print(f"   - Average raw text length: {stats['average_raw_text_length']:.0f} chars")
