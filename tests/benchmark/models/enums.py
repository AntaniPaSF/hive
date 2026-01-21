"""Enumeration types for benchmark suite

Defines status enums used throughout the benchmark suite for
consistent type checking and validation.
"""

from enum import Enum


class AccuracyStatus(str, Enum):
    """Status of accuracy validation for a test result"""
    
    PASS = "PASS"
    """Answer matches expected answer (fuzzy match score >= threshold)"""
    
    FAIL = "FAIL"
    """Answer does not match expected answer"""
    
    ERROR = "ERROR"
    """API error occurred (timeout, connection failure, 4xx/5xx response)"""


class CitationStatus(str, Enum):
    """Status of citation validation for a test result"""
    
    PRESENT = "PRESENT"
    """Citations array exists and contains valid citation structure"""
    
    MISSING = "MISSING"
    """Citations array is empty or missing from response"""
    
    INVALID = "INVALID"
    """Citations present but structure is invalid or hallucinated"""
