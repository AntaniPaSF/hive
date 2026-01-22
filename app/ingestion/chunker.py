"""
Semantic Chunking Module for HR Data Pipeline

Implements hybrid chunking strategy:
- Respects section boundaries from PDF structure
- Maximum 512 tokens per chunk
- 50 token overlap between chunks for context continuity
- Preserves metadata for citation and retrieval

Related:
- FR-008: Semantic chunking with section boundaries
- Research: semantic_chunker algorithm from research.md
- Data Model: Document Chunk entity (100-512 tokens)
"""

import logging
import tiktoken
from typing import List, Dict, Optional
from dataclasses import dataclass
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a single text chunk with metadata."""
    chunk_id: str
    text: str
    token_count: int
    chunk_index: int
    metadata: Dict


class SemanticChunker:
    """
    Semantic chunker that respects document structure while enforcing token limits.
    
    Uses tiktoken for accurate token counting with cl100k_base encoding (GPT-4 tokenizer).
    Splits text on section boundaries when possible, falls back to sentence boundaries
    when sections exceed max_tokens.
    """
    
    def __init__(self, max_tokens: int = 512, overlap_tokens: int = 50, min_chunk_size: int = 100):
        """
        Initialize the semantic chunker.
        
        Args:
            max_tokens: Maximum tokens per chunk (default: 512)
            overlap_tokens: Token overlap between chunks (default: 50)
            min_chunk_size: Minimum characters per chunk to avoid tiny fragments (default: 100)
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.min_chunk_size = min_chunk_size
        
        # Use cl100k_base encoding (GPT-4 tokenizer) for accurate counting
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.error(f"Failed to load tiktoken encoding: {e}")
            raise
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self.tokenizer.encode(text))
    
    def chunk_document(
        self,
        pdf_pages: List[Dict],
        document_id: str,
        source_filename: str
    ) -> List[Chunk]:
        """
        Chunk a document extracted from PDF with structure preservation.
        
        Args:
            pdf_pages: List of page dicts from PDFParser.extract_text_with_structure()
                       Each dict has: {page_number, text, sections, metadata}
            document_id: UUID of the source document
            source_filename: Original PDF filename for metadata
            
        Returns:
            List of Chunk objects with text, metadata, and unique IDs
        """
        chunks = []
        chunk_index = 0
        
        for page in pdf_pages:
            page_number = page.get('page_number', 0)
            sections = page.get('sections', [])
            
            # If no sections detected OR sections don't have text content,
            # treat entire page as one section
            if not sections or not any(section.get('text') for section in sections):
                sections = [{'text': page['text'], 'title': None, 'level': 0}]
            
            for section in sections:
                section_text = section.get('text', '').strip()
                section_title = section.get('title')
                
                if len(section_text) < self.min_chunk_size:
                    logger.debug(f"Skipping small section (< {self.min_chunk_size} chars) on page {page_number}")
                    continue
                
                # Chunk this section respecting token limits
                section_chunks = self._chunk_section(
                    text=section_text,
                    section_title=section_title,
                    page_number=page_number,
                    document_id=document_id,
                    source_filename=source_filename,
                    chunk_index_offset=chunk_index
                )
                
                chunks.extend(section_chunks)
                chunk_index += len(section_chunks)
        
        logger.info(f"Created {len(chunks)} chunks from {len(pdf_pages)} pages")
        return chunks
    
    def _chunk_section(
        self,
        text: str,
        section_title: Optional[str],
        page_number: int,
        document_id: str,
        source_filename: str,
        chunk_index_offset: int
    ) -> List[Chunk]:
        """
        Chunk a single section of text, respecting token limits with overlap.
        
        Strategy:
        1. If section fits in max_tokens → return as single chunk
        2. Otherwise, split on sentence boundaries with overlap
        3. Ensure each chunk has context continuity via overlap_tokens
        """
        token_count = self.count_tokens(text)
        
        # Case 1: Section fits in one chunk
        if token_count <= self.max_tokens:
            return [self._create_chunk(
                text=text,
                token_count=token_count,
                chunk_index=chunk_index_offset,
                section_title=section_title,
                page_number=page_number,
                document_id=document_id,
                source_filename=source_filename
            )]
        
        # Case 2: Section needs splitting
        chunks = []
        sentences = self._split_sentences(text)
        
        current_chunk_sentences = []
        current_token_count = 0
        overlap_sentences = []
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            # If adding this sentence exceeds limit, finalize current chunk
            if current_token_count + sentence_tokens > self.max_tokens and current_chunk_sentences:
                chunk_text = ' '.join(current_chunk_sentences)
                chunks.append(self._create_chunk(
                    text=chunk_text,
                    token_count=current_token_count,
                    chunk_index=chunk_index_offset + len(chunks),
                    section_title=section_title,
                    page_number=page_number,
                    document_id=document_id,
                    source_filename=source_filename
                ))
                
                # Prepare overlap for next chunk
                overlap_sentences = self._get_overlap_sentences(current_chunk_sentences, self.overlap_tokens)
                current_chunk_sentences = overlap_sentences.copy()
                current_token_count = sum(self.count_tokens(s) for s in current_chunk_sentences)
            
            # Add sentence to current chunk
            current_chunk_sentences.append(sentence)
            current_token_count += sentence_tokens
        
        # Finalize last chunk
        if current_chunk_sentences:
            chunk_text = ' '.join(current_chunk_sentences)
            chunks.append(self._create_chunk(
                text=chunk_text,
                token_count=self.count_tokens(chunk_text),
                chunk_index=chunk_index_offset + len(chunks),
                section_title=section_title,
                page_number=page_number,
                document_id=document_id,
                source_filename=source_filename
            ))
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using simple heuristics.
        
        Handles common abbreviations (e.g., Dr., Mr., Inc.) to avoid false splits.
        """
        # Common abbreviations that shouldn't trigger sentence breaks
        abbreviations = ['Dr', 'Mr', 'Mrs', 'Ms', 'Inc', 'Ltd', 'Corp', 'Co', 'etc', 'e.g', 'i.e']
        
        # Replace abbreviations temporarily
        temp_text = text
        for i, abbr in enumerate(abbreviations):
            temp_text = temp_text.replace(f'{abbr}.', f'{abbr}<ABBR{i}>')
        
        # Split on sentence boundaries
        import re
        sentences = re.split(r'(?<=[.!?])\s+', temp_text)
        
        # Restore abbreviations
        restored_sentences = []
        for sentence in sentences:
            for i, abbr in enumerate(abbreviations):
                sentence = sentence.replace(f'{abbr}<ABBR{i}>', f'{abbr}.')
            restored_sentences.append(sentence.strip())
        
        return [s for s in restored_sentences if s]
    
    def _get_overlap_sentences(self, sentences: List[str], target_overlap_tokens: int) -> List[str]:
        """
        Get the last N sentences that fit within target_overlap_tokens.
        
        This ensures context continuity between chunks.
        """
        overlap = []
        token_count = 0
        
        # Work backwards from end of sentences list
        for sentence in reversed(sentences):
            sentence_tokens = self.count_tokens(sentence)
            if token_count + sentence_tokens > target_overlap_tokens:
                break
            overlap.insert(0, sentence)
            token_count += sentence_tokens
        
        return overlap
    
    def _create_chunk(
        self,
        text: str,
        token_count: int,
        chunk_index: int,
        section_title: Optional[str],
        page_number: int,
        document_id: str,
        source_filename: str
    ) -> Chunk:
        """Create a Chunk object with metadata."""
        metadata = {
            'document_id': document_id,
            'source_doc': source_filename,
            'source_type': 'pdf',
            'page_number': page_number,
            'section_title': section_title,
            'chunk_index': chunk_index
        }
        
        return Chunk(
            chunk_id=str(uuid4()),
            text=text,
            token_count=token_count,
            chunk_index=chunk_index,
            metadata=metadata
        )
