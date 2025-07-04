"""
Exceptions for the answer generator module.
"""

class AnswerGeneratorError(Exception):
    """Base exception for answer generator operations."""
    pass

class AlbertAPIError(Exception):
    """Raised when Albert API requests fail."""
    pass
