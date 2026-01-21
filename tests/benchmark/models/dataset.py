"""GroundTruthDataset data model

Collection of BenchmarkQuestions loaded from YAML file with metadata.
"""

from dataclasses import dataclass
from typing import List
import yaml

from .question import BenchmarkQuestion


@dataclass
class GroundTruthDataset:
    """Collection of benchmark questions with metadata
    
    Attributes:
        version: Dataset version (e.g., "1.0", "1.1")
        created: Creation date (ISO 8601)
        description: Dataset purpose/scope description
        questions: List of benchmark questions
    """
    
    version: str
    created: str
    description: str
    questions: List[BenchmarkQuestion]
    
    def __post_init__(self):
        """Validate dataset integrity"""
        if not self.questions:
            raise ValueError("Dataset must contain at least one question")
        
        # Check for duplicate IDs
        ids = [q.id for q in self.questions]
        if len(ids) != len(set(ids)):
            duplicates = [id for id in ids if ids.count(id) > 1]
            raise ValueError(f"Duplicate question IDs found: {set(duplicates)}")
        
        # Validate semantic versioning format (basic check)
        if not self.version or '.' not in self.version:
            raise ValueError(f"Invalid version format: {self.version}. Expected semantic versioning (e.g., '1.0.0')")
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> "GroundTruthDataset":
        """Load dataset from YAML file
        
        Args:
            yaml_path: Path to YAML file containing ground truth questions
        
        Returns:
            GroundTruthDataset instance
        
        Raises:
            FileNotFoundError: If YAML file doesn't exist
            ValueError: If YAML structure is invalid
            yaml.YAMLError: If YAML syntax is malformed
        """
        try:
            with open(yaml_path, "r") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Ground truth file not found: {yaml_path}\n"
                f"Expected YAML file with benchmark questions."
            )
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax in {yaml_path}: {e}")
        
        # Validate required top-level fields
        required_fields = ["version", "created", "description", "questions"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise ValueError(
                f"Missing required fields in {yaml_path}: {missing}\n"
                f"Required: {required_fields}"
            )
        
        # Parse questions
        if not isinstance(data["questions"], list):
            raise ValueError(f"'questions' must be a list, got {type(data['questions'])}")
        
        try:
            questions = [BenchmarkQuestion(**q) for q in data["questions"]]
        except TypeError as e:
            raise ValueError(f"Invalid question structure in {yaml_path}: {e}")
        
        return cls(
            version=data["version"],
            created=data["created"],
            description=data["description"],
            questions=questions
        )
    
    def get_question_by_id(self, question_id: str) -> BenchmarkQuestion:
        """Retrieve question by ID
        
        Args:
            question_id: Question identifier
        
        Returns:
            BenchmarkQuestion with matching ID
        
        Raises:
            KeyError: If question ID not found
        """
        for q in self.questions:
            if q.id == question_id:
                return q
        raise KeyError(f"Question not found: {question_id}")
    
    def get_questions_by_category(self, category: str) -> List[BenchmarkQuestion]:
        """Get all questions in a category
        
        Args:
            category: Category name (e.g., "vacation_policy")
        
        Returns:
            List of questions in the specified category
        """
        return [q for q in self.questions if q.category == category]
    
    def __len__(self) -> int:
        """Number of questions in dataset"""
        return len(self.questions)
