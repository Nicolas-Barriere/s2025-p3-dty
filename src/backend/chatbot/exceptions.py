"""
Custom exceptions for the chatbot system.
"""


class ChatbotError(Exception):
    """Base exception for chatbot operations."""
    pass


class AlbertAPIError(ChatbotError):
    """Raised when Albert API requests fail."""
    pass


class FunctionExecutionError(ChatbotError):
    """Raised when function execution fails."""
    pass


class InvalidFunctionArgumentsError(ChatbotError):
    """Raised when function arguments are invalid."""
    pass


class UserNotFoundError(ChatbotError):
    """Raised when user is not found."""
    pass


class MailboxAccessError(ChatbotError):
    """Raised when user doesn't have mailbox access."""
    pass
