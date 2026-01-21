"""Citation rendering utilities for RAG LLM Service."""

from typing import Optional
from .query import Citation


def render_citation(citation: Citation) -> str:
    """Render a citation as formatted string.

    Format options:
    - With page number: "[document_name, page X]"
    - With section: "[document_name, section_name]"
    - Minimal: "[document_name]"

    Args:
        citation: Citation object to render

    Returns:
        Formatted citation string

    Examples:
        >>> citation = Citation(document_name="employee_handbook.pdf", page_number=12)
        >>> render_citation(citation)
        '[employee_handbook.pdf, page 12]'

        >>> citation = Citation(document_name="safety_manual.pdf", section="Chemical Handling")
        >>> render_citation(citation)
        '[safety_manual.pdf, Chemical Handling]'
    """
    # Priority: page_number > section > minimal
    if citation.page_number is not None:
        return f"[{citation.document_name}, page {citation.page_number}]"
    elif citation.section:
        return f"[{citation.document_name}, {citation.section}]"
    else:
        return f"[{citation.document_name}]"


def render_citations(citations: list[Citation]) -> str:
    """Render multiple citations as comma-separated list.

    Args:
        citations: List of Citation objects

    Returns:
        Comma-separated citation string

    Examples:
        >>> citations = [
        ...     Citation(document_name="doc1.pdf", page_number=5),
        ...     Citation(document_name="doc2.pdf", section="Section A")
        ... ]
        >>> render_citations(citations)
        '[doc1.pdf, page 5], [doc2.pdf, Section A]'
    """
    if not citations:
        return ""
    return ", ".join(render_citation(c) for c in citations)


def format_citation_with_excerpt(
    citation: Citation, max_excerpt_length: int = 80
) -> str:
    """Format citation with excerpt for display.

    Args:
        citation: Citation object
        max_excerpt_length: Maximum length for excerpt display

    Returns:
        Formatted string with citation and excerpt

    Examples:
        >>> citation = Citation(
        ...     document_name="handbook.pdf",
        ...     excerpt="All employees must wear protective gear...",
        ...     page_number=12
        ... )
        >>> format_citation_with_excerpt(citation)
        '[handbook.pdf, page 12]: "All employees must wear protective gear..."'
    """
    citation_str = render_citation(citation)

    # Truncate excerpt if too long
    excerpt = citation.excerpt
    if len(excerpt) > max_excerpt_length:
        excerpt = excerpt[: max_excerpt_length - 3] + "..."

    return f'{citation_str}: "{excerpt}"'


def extract_document_names(citations: list[Citation]) -> list[str]:
    """Extract unique document names from citations.

    Args:
        citations: List of Citation objects

    Returns:
        List of unique document names

    Examples:
        >>> citations = [
        ...     Citation(document_name="doc1.pdf", excerpt="..."),
        ...     Citation(document_name="doc2.pdf", excerpt="..."),
        ...     Citation(document_name="doc1.pdf", excerpt="...")
        ... ]
        >>> extract_document_names(citations)
        ['doc1.pdf', 'doc2.pdf']
    """
    seen = set()
    result = []
    for citation in citations:
        if citation.document_name not in seen:
            seen.add(citation.document_name)
            result.append(citation.document_name)
    return result
