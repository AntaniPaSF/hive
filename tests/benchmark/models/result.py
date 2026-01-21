"""TestResult data model

Captures the outcome of testing one question against the LLM API.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional

from .enums import AccuracyStatus, CitationStatus


@dataclass
class TestResult:
    """Outcome of testing one benchmark question
    
    Attributes:
        question_id: References BenchmarkQuestion.id
        question_text: The question that was asked (for report readability)
        llm_response: The answer text returned by the LLM
        citations_found: Citations extracted from response
        accuracy_status: Enum: PASS, FAIL, ERROR
        accuracy_score: Fuzzy match score (0.0-1.0)
        citation_status: Enum: PRESENT, MISSING, INVALID
        latency_ms: Response time in milliseconds
        error_message: Error details if status=ERROR
        timestamp: ISO 8601 timestamp of test execution
    """
    
    question_id: str
    question_text: str
    llm_response: str
    citations_found: List[Dict[str, str]]
    accuracy_status: AccuracyStatus
    accuracy_score: float
    citation_status: CitationStatus
    latency_ms: float
    error_message: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def __post_init__(self):
        """Validate field values"""
        if not (0.0 <= self.accuracy_score <= 1.0):
            raise ValueError(f"accuracy_score must be in [0.0, 1.0], got {self.accuracy_score}")
        if self.latency_ms < 0:
            raise ValueError(f"latency_ms must be non-negative, got {self.latency_ms}")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization
        
        Returns:
            Dictionary representation with enum values as strings
        """
        return {
            "question_id": self.question_id,
            "question_text": self.question_text,
            "llm_response": self.llm_response,
            "citations_found": self.citations_found,
            "accuracy_status": self.accuracy_status.value,
            "accuracy_score": self.accuracy_score,
            "citation_status": self.citation_status.value,
            "latency_ms": self.latency_ms,
            "error_message": self.error_message,
            "timestamp": self.timestamp
        }
    
    def is_passing(self) -> bool:
        """Check if test passed all validations
        
        Returns:
            True if accuracy passed and citations present
        """
        return (
            self.accuracy_status == AccuracyStatus.PASS and
            self.citation_status == CitationStatus.PRESENT
        )
