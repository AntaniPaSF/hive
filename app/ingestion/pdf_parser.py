"""
PDF Parser Module

Extracts text from PDF documents while preserving structural information
like headings, sections, and page boundaries.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional
import logging

try:
    import PyPDF2
except ImportError:
    raise ImportError("PyPDF2 is required. Install with: pip install PyPDF2==3.0.1")

logger = logging.getLogger(__name__)


class PDFParser:
    """Extract and structure text from PDF documents."""
    
    def __init__(self):
        self.logger = logger
    
    def extract_text_with_structure(self, pdf_path: Path) -> List[Dict]:
        """
        Extract text from PDF while preserving structure.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of dicts with page_number, text, sections, and metadata
            
        Raises:
            ValueError: If PDF is encrypted or corrupted
            FileNotFoundError: If PDF doesn't exist
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        self.logger.info(f"Extracting text from {pdf_path}")
        
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                # Check encryption
                if reader.is_encrypted:
                    if not reader.decrypt(''):
                        raise ValueError(f"PDF {pdf_path} is password-protected")
                
                documents = []
                total_pages = len(reader.pages)
                
                for page_num, page in enumerate(reader.pages, start=1):
                    try:
                        text = page.extract_text()
                        
                        if not text or len(text.strip()) < 10:
                            self.logger.warning(f"Page {page_num}: Very little text extracted (possible image/scan)")
                            continue
                        
                        # Clean whitespace but preserve structure
                        text = self._clean_text(text)
                        
                        # Detect section headers
                        sections = self._extract_sections(text)
                        
                        documents.append({
                            'page_number': page_num,
                            'text': text,
                            'sections': sections,
                            'metadata': {
                                'char_count': len(text),
                                'has_tables': self._detect_tables(text),
                                'section_count': len(sections)
                            }
                        })
                        
                        if page_num % 10 == 0:
                            self.logger.info(f"Processed {page_num}/{total_pages} pages")
                    
                    except Exception as e:
                        self.logger.error(f"Error extracting page {page_num}: {e}")
                        continue
                
                self.logger.info(f"Extracted {len(documents)} pages from {pdf_path.name}")
                return documents
        
        except Exception as e:
            raise ValueError(f"Failed to parse PDF: {e}")
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text while preserving structure."""
        # Normalize line breaks
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove excessive spaces but keep indentation
        lines = []
        for line in text.split('\n'):
            # Keep leading spaces for indentation, clean the rest
            stripped = line.rstrip()
            if stripped:
                lines.append(stripped)
        return '\n'.join(lines)
    
    def _extract_sections(self, text: str) -> List[Dict[str, str]]:
        """Detect section headers in text."""
        sections = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            # Detect headers: all caps, short lines, or numbered sections
            if self._is_section_header(line):
                sections.append({
                    'title': line.strip(),
                    'line_number': i,
                    'level': self._get_header_level(line)
                })
        
        return sections
    
    def _is_section_header(self, line: str) -> bool:
        """Check if line is likely a section header."""
        line = line.strip()
        
        if not line or len(line) > 100:
            return False
        
        # All caps (likely header)
        if line.isupper() and len(line) > 5 and len(line) < 60:
            return True
        
        # Numbered sections (e.g., "1.2 Vacation Policy")
        if re.match(r'^[\d\.\)]+\s+[A-Z]', line):
            return True
        
        # Title case with few words
        words = line.split()
        if len(words) <= 8 and all(w[0].isupper() for w in words if w):
            return True
        
        return False
    
    def _get_header_level(self, line: str) -> int:
        """Determine header level (1-3) based on formatting."""
        # Level 1: Very short, all caps
        if line.isupper() and len(line) < 30:
            return 1
        
        # Level 2: Numbered sections
        if re.match(r'^[\d\.]+\s', line):
            depth = line.split()[0].count('.')
            return min(depth + 1, 3)
        
        # Level 3: Title case
        return 3
    
    def _detect_tables(self, text: str) -> bool:
        """Detect if text likely contains tables."""
        # Simple heuristic: multiple aligned spaces or pipe characters
        lines = text.split('\n')
        
        aligned_count = 0
        for line in lines:
            # Check for multiple spaces (table columns)
            if re.search(r'\s{3,}', line):
                aligned_count += 1
            # Check for pipe separators
            if '|' in line and line.count('|') >= 2:
                aligned_count += 1
        
        # If >20% of lines look like table content
        return aligned_count > len(lines) * 0.2
    
    def convert_to_markdown(self, documents: List[Dict], output_path: Path, pdf_filename: str):
        """
        Convert extracted PDF to markdown format.
        
        Args:
            documents: List of extracted page dicts
            output_path: Where to save markdown
            pdf_filename: Original PDF filename for header
        """
        md_lines = [f"# {pdf_filename}\n"]
        
        for doc in documents:
            md_lines.append(f"## Page {doc['page_number']}\n")
            
            text = doc['text']
            sections = doc['sections']
            
            if sections:
                # Split text by sections and add markdown headers
                lines = text.split('\n')
                current_line = 0
                
                for section in sections:
                    # Add text before this section
                    before_text = '\n'.join(lines[current_line:section['line_number']])
                    if before_text.strip():
                        md_lines.append(before_text + '\n')
                    
                    # Add section header with appropriate markdown level
                    header_prefix = '#' * (section['level'] + 2)  # +2 because page is ##
                    md_lines.append(f"{header_prefix} {section['title']}\n")
                    
                    current_line = section['line_number'] + 1
                
                # Add remaining text
                remaining_text = '\n'.join(lines[current_line:])
                if remaining_text.strip():
                    md_lines.append(remaining_text + '\n')
            else:
                # No sections detected, just add the text
                md_lines.append(text + '\n')
            
            md_lines.append('\n---\n\n')  # Page separator
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_lines))
        
        self.logger.info(f"Saved markdown to {output_path}")
