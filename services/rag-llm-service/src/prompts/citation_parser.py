"""
Citation extraction from LLM-generated answers.

This module parses citation markers from LLM output and validates
that citations reference actual source documents.
"""

import re
from typing import List, Dict, Any, Set, Tuple

from ..utils.logger import get_logger

logger = get_logger(__name__)


def extract_citations(
    answer_text: str,
    retrieved_chunks: List[Dict[str, Any]],
    request_id: str = "unknown",
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Extract citation markers from LLM answer and validate against sources.

    Expects citations in format: [document_name, section_title]

    Args:
        answer_text: LLM-generated answer text
        retrieved_chunks: List of chunks used as context (for validation)
        request_id: Request ID for logging

    Returns:
        Tuple of (list of citation dicts, all_citations_valid boolean)
        Citation dict format:
        {
            "document_name": str,
            "section": str,
            "excerpt": str,  # from retrieved chunk
            "page_number": int or None,
            "chunk_id": str or None
        }
    """
    # Regex pattern to match [document, section] citations
    # Handles various formats: [doc.pdf, Section], [doc, Section Title], etc.
    citation_pattern = r"\[([^\]]+?),\s*([^\]]+?)\]"

    matches = re.findall(citation_pattern, answer_text)

    if not matches:
        logger.warning(
            "No citations found in LLM answer",
            extra={
                "component": "citation_parser",
                "event": "no_citations",
                "request_id": request_id,
                "data": {"answer_length": len(answer_text)},
            },
        )
        return [], False

    # Build map of available sources for validation
    available_sources = {}
    for chunk in retrieved_chunks:
        metadata = chunk.get("metadata", {})
        doc_name = metadata.get("document_name", "").lower()
        section = metadata.get("section", "").lower()

        key = (doc_name, section)
        if key not in available_sources:
            available_sources[key] = chunk

    # Extract and validate citations
    citations = []
    seen_citations = set()  # Deduplicate
    all_valid = True

    for doc_match, section_match in matches:
        doc_name = doc_match.strip()
        section_name = section_match.strip()

        # Create citation key for deduplication
        citation_key = (doc_name.lower(), section_name.lower())
        if citation_key in seen_citations:
            continue
        seen_citations.add(citation_key)

        # Try to find matching chunk
        matching_chunk = available_sources.get(citation_key)

        if matching_chunk:
            metadata = matching_chunk.get("metadata", {})
            citation = {
                "document_name": doc_name,
                "section": section_name,
                "excerpt": matching_chunk.get("content", "")[:200],  # First 200 chars
                "page_number": metadata.get("page_number"),
                "chunk_id": matching_chunk.get("chunk_id"),
            }
            citations.append(citation)

            logger.debug(
                "Valid citation found",
                extra={
                    "component": "citation_parser",
                    "event": "citation_validated",
                    "request_id": request_id,
                    "data": {"document": doc_name, "section": section_name},
                },
            )
        else:
            # Citation doesn't match any retrieved source
            all_valid = False
            logger.warning(
                "Citation references unknown source",
                extra={
                    "component": "citation_parser",
                    "event": "invalid_citation",
                    "request_id": request_id,
                    "data": {
                        "document": doc_name,
                        "section": section_name,
                        "available_sources": len(available_sources),
                    },
                },
            )

            # Still include the citation but flag it
            citation = {
                "document_name": doc_name,
                "section": section_name,
                "excerpt": None,
                "page_number": None,
                "chunk_id": None,
                "validation_warning": "Source not found in retrieved context",
            }
            citations.append(citation)

    logger.info(
        "Citation extraction complete",
        extra={
            "component": "citation_parser",
            "event": "extraction_complete",
            "request_id": request_id,
            "data": {
                "total_citations": len(citations),
                "unique_citations": len(seen_citations),
                "all_valid": all_valid,
            },
        },
    )

    return citations, all_valid


def format_citations_for_display(citations: List[Dict[str, Any]]) -> List[str]:
    """
    Format citations for human-readable display.

    Args:
        citations: List of citation dictionaries

    Returns:
        List of formatted citation strings
    """
    formatted = []
    for citation in citations:
        doc = citation.get("document_name", "Unknown")
        section = citation.get("section", "")
        page = citation.get("page_number")

        if page is not None:
            formatted.append(f"[{doc}, {section}, p.{page}]")
        elif section:
            formatted.append(f"[{doc}, {section}]")
        else:
            formatted.append(f"[{doc}]")

    return formatted
