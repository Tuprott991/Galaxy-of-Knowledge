"""
PMC Text to Markdown Converter

This module converts PMC (PubMed Central) text files that contain HTML-formatted 
academic papers into clean, structured Markdown format following proper academic 
paper structure.

Features:
- Extracts title, abstract, sections, figures, tables
- Properly formats references and citations
- Maintains academic paper structure
- Handles special formatting and symbols
"""

import re
import os
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple
import json


class PMCToMarkdownConverter:
    """Converts PMC HTML text files to structured Markdown format."""
    
    def __init__(self):
        self.soup = None
        self.title = ""
        self.abstract = ""
        self.sections = []
        self.references = []
        self.figures = []
        self.tables = []
        self.keywords = []
    
    def load_pmc_file(self, file_path: str) -> bool:
        """Load and parse a PMC text file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Parse HTML content
            self.soup = BeautifulSoup(content, 'html.parser')
            return True
        except Exception as e:
            print(f"Error loading file {file_path}: {e}")
            return False
    
    def extract_title(self) -> str:
        """Extract paper title from HTML."""
        # Try multiple possible title locations
        title_selectors = [
            'title',
            'h1',
            '.title',
            '[class*="title"]'
        ]
        
        for selector in title_selectors:
            title_elem = self.soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text().strip()
                # Clean up title
                if 'PMC' in title and 'Paper' in title:
                    continue  # Skip generic PMC titles
                if title and len(title) > 10:
                    self.title = self.clean_text(title)
                    return self.title
        
        # If no proper title found, try to extract from first heading
        first_heading = self.soup.find(['h1', 'h2', 'h3'])
        if first_heading:
            self.title = self.clean_text(first_heading.get_text())
        
        return self.title
    
    def extract_abstract(self) -> str:
        """Extract abstract section."""
        abstract_section = self.soup.find('section', {'class': 'abstract'}) or \
                          self.soup.find('section', {'id': 'abstract1'}) or \
                          self.soup.find(lambda tag: tag.name == 'section' and 
                                       tag.find('h2', string=re.compile(r'Abstract', re.I)))
        
        if abstract_section:
            # Remove the "Abstract" heading
            abstract_heading = abstract_section.find(['h1', 'h2', 'h3'], string=re.compile(r'Abstract', re.I))
            if abstract_heading:
                abstract_heading.decompose()
            
            # Extract text, preserving paragraph structure
            paragraphs = abstract_section.find_all('p')
            if paragraphs:
                abstract_text = []
                for p in paragraphs:
                    # Skip keywords section in abstract
                    if 'Keywords:' in p.get_text() or 'kwd-group' in str(p.get('class', [])):
                        continue
                    text = self.clean_text(p.get_text())
                    if text:
                        abstract_text.append(text)
                self.abstract = '\n\n'.join(abstract_text)
            else:
                self.abstract = self.clean_text(abstract_section.get_text())
        
        return self.abstract
    
    def extract_keywords(self) -> List[str]:
        """Extract keywords from the paper."""
        # Look for keywords in abstract section or dedicated keywords section
        keyword_section = self.soup.find('section', {'class': 'kwd-group'}) or \
                         self.soup.find(lambda tag: 'Keywords:' in tag.get_text())
        
        if keyword_section:
            text = keyword_section.get_text()
            # Extract keywords after "Keywords:" label
            if 'Keywords:' in text:
                keywords_text = text.split('Keywords:')[1].strip()
                # Split by common delimiters
                keywords = re.split(r'[,;]\s*', keywords_text)
                self.keywords = [k.strip() for k in keywords if k.strip()]
        
        return self.keywords
    
    def extract_sections(self) -> List[Dict]:
        """Extract main content sections."""
        sections = []
        
        # Find all main sections (usually have IDs like S1, S2, etc.)
        section_elements = self.soup.find_all('section', {'id': re.compile(r'^S\d+')})
        
        for section in section_elements:
            section_data = self.process_section(section)
            if section_data:
                sections.append(section_data)
        
        self.sections = sections
        return sections
    
    def process_section(self, section_elem) -> Optional[Dict]:
        """Process a single section element."""
        # Extract section title
        title_elem = section_elem.find(['h1', 'h2', 'h3', 'h4'])
        if not title_elem:
            return None
        
        title = self.clean_text(title_elem.get_text())
        
        # Extract section content
        content_parts = []
        
        # Remove title from processing
        title_elem.decompose()
        
        # Process paragraphs
        paragraphs = section_elem.find_all('p', recursive=False)
        for p in paragraphs:
            text = self.clean_text(p.get_text())
            if text:
                content_parts.append(text)
        
        # Process subsections
        subsections = []
        subsection_elements = section_elem.find_all('section')
        for subsection in subsection_elements:
            subsection_data = self.process_section(subsection)
            if subsection_data:
                subsections.append(subsection_data)
        
        return {
            'title': title,
            'content': content_parts,
            'subsections': subsections
        }
    
    def extract_figures(self) -> List[Dict]:
        """Extract figure information."""
        figures = []
        figure_elements = self.soup.find_all('figure')
        
        for fig in figure_elements:
            figure_data = {
                'id': fig.get('id', ''),
                'title': '',
                'caption': '',
                'image_url': ''
            }
            
            # Extract figure title
            title_elem = fig.find(['h1', 'h2', 'h3', 'h4'])
            if title_elem:
                figure_data['title'] = self.clean_text(title_elem.get_text())
            
            # Extract caption
            caption_elem = fig.find('figcaption') or fig.find('p')
            if caption_elem:
                figure_data['caption'] = self.clean_text(caption_elem.get_text())
            
            # Extract image URL
            img_elem = fig.find('img')
            if img_elem:
                figure_data['image_url'] = img_elem.get('src', '')
            
            figures.append(figure_data)
        
        self.figures = figures
        return figures
    
    def extract_tables(self) -> List[Dict]:
        """Extract table information."""
        tables = []
        table_sections = self.soup.find_all('section', {'class': 'tw'}) or \
                        self.soup.find_all(lambda tag: tag.name == 'section' and tag.find('table'))
        
        for table_section in table_sections:
            table_data = {
                'id': table_section.get('id', ''),
                'title': '',
                'caption': '',
                'headers': [],
                'rows': []
            }
            
            # Extract table title
            title_elem = table_section.find(['h1', 'h2', 'h3', 'h4'])
            if title_elem:
                table_data['title'] = self.clean_text(title_elem.get_text())
            
            # Extract table
            table_elem = table_section.find('table')
            if table_elem:
                # Extract headers
                header_row = table_elem.find('thead')
                if header_row:
                    headers = [self.clean_text(th.get_text()) for th in header_row.find_all(['th', 'td'])]
                    table_data['headers'] = headers
                
                # Extract rows
                tbody = table_elem.find('tbody') or table_elem
                rows = tbody.find_all('tr')
                for row in rows:
                    if row.parent.name == 'thead':  # Skip header rows
                        continue
                    cells = [self.clean_text(td.get_text()) for td in row.find_all(['td', 'th'])]
                    if cells:
                        table_data['rows'].append(cells)
            
            tables.append(table_data)
        
        self.tables = tables
        return tables
    
    def extract_references(self) -> List[Dict]:
        """Extract reference list."""
        references = []
        
        # Find references section
        ref_section = self.soup.find('section', {'class': 'ref-list'}) or \
                     self.soup.find(lambda tag: tag.name == 'section' and 
                                  tag.find(['h1', 'h2'], string=re.compile(r'References?', re.I)))
        
        if ref_section:
            # Extract individual references
            ref_items = ref_section.find_all('li') or ref_section.find_all('div', {'class': 'ref'})
            
            for ref_item in ref_items:
                ref_id = ref_item.get('id', '')
                ref_text = self.clean_text(ref_item.get_text())
                
                if ref_text:
                    references.append({
                        'id': ref_id,
                        'text': ref_text
                    })
        
        self.references = references
        return references
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Fix common formatting issues
        text = re.sub(r'\s+([,.;:!?])', r'\1', text)  # Remove space before punctuation
        text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', text)  # Ensure space after sentence end
        
        # Handle special characters
        text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        
        return text
    
    def convert_to_markdown(self) -> str:
        """Convert the extracted content to formatted Markdown."""
        markdown_parts = []
        
        # Title
        if self.title:
            markdown_parts.append(f"# {self.title}\n")
        
        # Keywords
        if self.keywords:
            markdown_parts.append(f"**Keywords:** {', '.join(self.keywords)}\n")
        
        # Abstract
        if self.abstract:
            markdown_parts.append("## Abstract\n")
            markdown_parts.append(f"{self.abstract}\n")
        
        # Main sections
        for section in self.sections:
            markdown_parts.append(self.format_section_markdown(section, level=2))
        
        # Figures
        if self.figures:
            markdown_parts.append("## Figures\n")
            for fig in self.figures:
                if fig['title']:
                    markdown_parts.append(f"### {fig['title']}\n")
                if fig['image_url']:
                    markdown_parts.append(f"![{fig['title']}]({fig['image_url']})\n")
                if fig['caption']:
                    markdown_parts.append(f"*{fig['caption']}*\n")
                markdown_parts.append("")
        
        # Tables
        if self.tables:
            markdown_parts.append("## Tables\n")
            for table in self.tables:
                markdown_parts.append(self.format_table_markdown(table))
        
        # References
        if self.references:
            markdown_parts.append("## References\n")
            for i, ref in enumerate(self.references, 1):
                markdown_parts.append(f"{i}. {ref['text']}\n")
        
        return '\n'.join(markdown_parts)
    
    def format_section_markdown(self, section: Dict, level: int = 2) -> str:
        """Format a section as Markdown."""
        parts = []
        
        # Section heading
        heading_prefix = '#' * level
        parts.append(f"{heading_prefix} {section['title']}\n")
        
        # Section content
        for paragraph in section['content']:
            parts.append(f"{paragraph}\n")
        
        # Subsections
        for subsection in section['subsections']:
            parts.append(self.format_section_markdown(subsection, level + 1))
        
        return '\n'.join(parts)
    
    def format_table_markdown(self, table: Dict) -> str:
        """Format a table as Markdown."""
        parts = []
        
        if table['title']:
            parts.append(f"### {table['title']}\n")
        
        if table['headers'] and table['rows']:
            # Create table header
            headers = '| ' + ' | '.join(table['headers']) + ' |'
            separator = '| ' + ' | '.join(['---'] * len(table['headers'])) + ' |'
            parts.extend([headers, separator])
            
            # Add table rows
            for row in table['rows']:
                if len(row) == len(table['headers']):
                    row_text = '| ' + ' | '.join(row) + ' |'
                    parts.append(row_text)
        
        parts.append("")  # Add spacing after table
        return '\n'.join(parts)
    
    def convert_file(self, input_path: str, output_path: str = None) -> bool:
        """Convert a PMC file to Markdown and save it."""
        if not self.load_pmc_file(input_path):
            return False
        
        # Extract all components
        self.extract_title()
        self.extract_keywords()
        self.extract_abstract()
        self.extract_sections()
        self.extract_figures()
        self.extract_tables()
        self.extract_references()
        
        # Generate Markdown
        markdown_content = self.convert_to_markdown()
        
        # Determine output path
        if not output_path:
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            output_path = os.path.join(os.path.dirname(input_path), f"{base_name}.md")
        
        # Save Markdown file
        try:
            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(markdown_content)
            print(f"Successfully converted {input_path} to {output_path}")
            return True
        except Exception as e:
            print(f"Error saving Markdown file: {e}")
            return False


def main():
    """Main function to demonstrate converter usage."""
    converter = PMCToMarkdownConverter()
    
    folder_path = "database/PMC_txt"  # Folder containing PMC text files
    output_path = "database/PMC_md"  # Folder to save converted Markdown files  
    os.makedirs(output_path, exist_ok=True)
    

    for filename in os.listdir(folder_path):
        if filename.endswith(".txt"):
            input_file = os.path.join(folder_path, filename)
            base_name = os.path.splitext(filename)[0]
            output_file = os.path.join(output_path, f"{base_name}.md")
            
            print(f"Converting {input_file} to {output_file}...")
            if converter.convert_file(input_file, output_file):
                print("Conversion completed successfully!")
            else:
                print("Conversion failed!")

if __name__ == "__main__":
    main()