"""BenchmarkQuestion data model

Represents a single test case with expected answer and variations.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class BenchmarkQuestion:
    """A single benchmark test case
    
    Attributes:
        id: Unique identifier (e.g., "Q001", "Q002")
        category: Question domain (e.g., "vacation_policy", "expense_policy")
        question: The question text to send to the LLM API
        expected_answer: Primary expected answer for accuracy validation
        variations: Alternative acceptable answer formulations
        citation_required: Whether citation is mandatory for this question
        tags: Metadata tags for filtering/grouping
    """
    
    id: str
    category: str
    question: str
    expected_answer: str
    variations: List[str] = field(default_factory=list)
    citation_required: bool = True
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate required fields"""
        if not self.id:
            raise ValueError("Question ID is required")
        if not self.question:
            raise ValueError("Question text is required")
        if not self.expected_answer:
            raise ValueError("Expected answer is required")
        if not self.category:
            raise ValueError("Category is required")
    
    def get_all_acceptable_answers(self) -> List[str]:
        """Get list of all acceptable answers (expected + variations)
        
        Returns:
            List containing expected_answer followed by all variations
        """
        return [self.expected_answer] + self.variations
