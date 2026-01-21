"""Fuzzy matching validation for answer accuracy

Implements threshold-based fuzzy matching using Levenshtein distance
and keyword overlap as specified in research.md.
"""

from Levenshtein import ratio as levenshtein_ratio
from typing import List


def fuzzy_match(
    expected: str,
    actual: str,
    lev_threshold: float = 0.8,
    keyword_threshold: float = 0.70
) -> tuple[bool, float]:
    """Compare expected and actual answers using fuzzy matching
    
    Uses two methods:
    1. Levenshtein ratio (character-based similarity)
    2. Keyword overlap (word-based similarity)
    
    Passes if EITHER method exceeds its threshold.
    
    Args:
        expected: Expected answer text
        actual: Actual LLM response text
        lev_threshold: Minimum Levenshtein ratio for pass (default: 0.8)
        keyword_threshold: Minimum keyword overlap for pass (default: 0.70)
    
    Returns:
        Tuple of (passes, score) where:
        - passes: True if either method passes threshold
        - score: Maximum score from both methods (0.0-1.0)
    
    Examples:
        >>> fuzzy_match("Submit via portal", "Submit through portal")
        (True, 0.89)
        
        >>> fuzzy_match("20 days vacation", "twenty days of vacation time")
        (True, 0.75)  # keyword overlap passes
    """
    # Normalize whitespace and case
    exp_norm = " ".join(expected.lower().split())
    act_norm = " ".join(actual.lower().split())
    
    # Method 1: Levenshtein ratio (character-based)
    lev_score = levenshtein_ratio(exp_norm, act_norm)
    
    # Method 2: Keyword overlap (word-based)
    exp_words = set(exp_norm.split())
    act_words = set(act_norm.split())
    
    if len(exp_words) == 0:
        keyword_score = 0.0
    else:
        overlap = len(exp_words & act_words)
        keyword_score = overlap / len(exp_words)
    
    # Pass if EITHER method exceeds threshold
    passes = lev_score >= lev_threshold or keyword_score >= keyword_threshold
    
    # Return max score for reporting
    max_score = max(lev_score, keyword_score)
    
    return passes, max_score


def match_against_variations(
    expected_answers: List[str],
    actual: str,
    lev_threshold: float = 0.8,
    keyword_threshold: float = 0.70
) -> tuple[bool, float, str]:
    """Match actual answer against multiple acceptable variations
    
    Tries fuzzy matching against each expected answer variation
    and returns the best match.
    
    Args:
        expected_answers: List of acceptable answer variations
        actual: Actual LLM response text
        lev_threshold: Minimum Levenshtein ratio for pass
        keyword_threshold: Minimum keyword overlap for pass
    
    Returns:
        Tuple of (passes, best_score, matched_variation) where:
        - passes: True if any variation passes
        - best_score: Highest score across all variations
        - matched_variation: The variation that matched (or empty string)
    
    Examples:
        >>> variations = ["20 days per year", "20 vacation days annually"]
        >>> match_against_variations(variations, "20 days vacation each year")
        (True, 0.85, "20 days per year")
    """
    if not expected_answers:
        return False, 0.0, ""
    
    best_score = 0.0
    best_match = ""
    any_passed = False
    
    for expected in expected_answers:
        passes, score = fuzzy_match(expected, actual, lev_threshold, keyword_threshold)
        
        if score > best_score:
            best_score = score
            best_match = expected
        
        if passes:
            any_passed = True
    
    return any_passed, best_score, best_match
