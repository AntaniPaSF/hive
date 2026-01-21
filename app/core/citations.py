from typing import List, Dict


class CitationError(Exception):
    pass


def enforce_citations(payload: Dict) -> List[Dict]:
    """
    Enforce that an answer request contains at least one citation.
    For MVP, we expect client to provide citations or we reject.
    This models the response layer guard (no hallucinations).
    """
    citations = payload.get("citations", [])
    if not isinstance(citations, list) or len(citations) == 0:
        raise CitationError(
            "This system requires source citations. Please provide or ingest documents and reference at least one source."
        )
    # Minimal validation: each citation has name and section
    for c in citations:
        if not isinstance(c, dict) or not c.get("doc") or not c.get("section"):
            raise CitationError(
                "Invalid citation format. Expected {doc, section}.")
    return citations
