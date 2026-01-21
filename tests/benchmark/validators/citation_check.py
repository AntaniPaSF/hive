"""Citation validation for LLM responses

Validates that citations are present and have correct structure
as specified in the API contract.
"""

from typing import List, Dict, Any, Tuple


def validate_citations(response_data: Dict[str, Any]) -> Tuple[bool, List[Dict[str, str]]]:
    """Validate citation presence and structure in LLM response
    
    Checks that:
    1. 'citations' field exists in response
    2. Citations is a non-empty list
    3. Each citation has required fields: 'document' and 'section'
    
    Args:
        response_data: Parsed JSON response from LLM API
    
    Returns:
        Tuple of (is_valid, citations_list) where:
        - is_valid: True if citations present and valid
        - citations_list: List of citation dicts (empty if invalid)
    
    Examples:
        >>> data = {"answer": "...", "citations": [{"document": "HR.md", "section": "§1"}]}
        >>> validate_citations(data)
        (True, [{"document": "HR.md", "section": "§1"}])
        
        >>> data = {"answer": "...", "citations": []}
        >>> validate_citations(data)
        (False, [])
    """
    # Check if citations field exists
    if "citations" not in response_data:
        return False, []
    
    citations = response_data["citations"]
    
    # Check if citations is a list
    if not isinstance(citations, list):
        return False, []
    
    # Check if citations list is non-empty
    if len(citations) == 0:
        return False, []
    
    # Validate structure of each citation
    valid_citations = []
    for citation in citations:
        if not isinstance(citation, dict):
            continue
        
        # Required fields: document and section
        if "document" not in citation or "section" not in citation:
            continue
        
        # Check that values are non-empty strings
        if not citation["document"] or not citation["section"]:
            continue
        
        valid_citations.append({
            "document": citation["document"],
            "section": citation["section"]
        })
    
    # At least one valid citation required
    is_valid = len(valid_citations) > 0
    
    return is_valid, valid_citations


def validate_citation_quality(
    citations: List[Dict[str, str]],
    manifest: Dict[str, List[str]]
) -> Tuple[bool, List[Dict[str, str]]]:
    """Validate citations against knowledge base manifest (US4)
    
    Checks that cited documents and sections exist in the
    knowledge base manifest.
    
    Args:
        citations: List of citation dicts with 'document' and 'section'
        manifest: Dict mapping document names to list of valid sections
    
    Returns:
        Tuple of (all_valid, hallucinated_citations) where:
        - all_valid: True if all citations reference real sources
        - hallucinated_citations: List of invalid citations
    
    Examples:
        >>> manifest = {"HR.md": ["§1", "§2"], "Policy.md": ["§A"]}
        >>> citations = [{"document": "HR.md", "section": "§1"}]
        >>> validate_citation_quality(citations, manifest)
        (True, [])
        
        >>> citations = [{"document": "Fake.md", "section": "§1"}]
        >>> validate_citation_quality(citations, manifest)
        (False, [{"document": "Fake.md", "section": "§1"}])
    """
    hallucinated = []
    
    for citation in citations:
        doc = citation["document"]
        section = citation["section"]
        
        # Check if document exists in manifest
        if doc not in manifest:
            hallucinated.append(citation)
            continue
        
        # Check if section exists in document
        valid_sections = manifest[doc]
        if section not in valid_sections:
            hallucinated.append(citation)
    
    all_valid = len(hallucinated) == 0
    
    return all_valid, hallucinated
