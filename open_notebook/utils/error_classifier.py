"""
Error classification utility for LLM provider errors.

Maps raw exceptions from AI providers/Esperanto/LangChain to user-friendly
error messages and appropriate exception types.
"""

from loguru import logger

from open_notebook.exceptions import (
    AuthenticationError,
    ConfigurationError,
    ExternalServiceError,
    NetworkError,
    OpenNotebookError,
    RateLimitError,
)

# Classification rules: (keywords, exception_class, user_message or None to pass through)
_CLASSIFICATION_RULES: list[tuple[list[str], type[OpenNotebookError], str | None]] = [
    # Authentication errors
    (
        ["authentication", "unauthorized", "invalid api key", "invalid_api_key", "401"],
        AuthenticationError,
        "Authentication failed. Please check your API key in Settings -> Credentials.",
    ),
    # Rate limit errors
    (
        ["rate limit", "rate_limit", "429", "too many requests", "quota exceeded"],
        RateLimitError,
        "Rate limit exceeded. Please wait a moment and try again.",
    ),
    # Model not found (pass through original message)
    (
        ["model not found", "does not exist", "model_not_found"],
        ConfigurationError,
        None,
    ),
    # Configuration errors from provision.py (pass through)
    (
        ["no model configured", "please go to settings"],
        ConfigurationError,
        None,
    ),
    # Network errors
    (
        ["connecterror", "timeoutexception", "connection refused", "connection error", "timed out", "timeout"],
        NetworkError,
        "Could not connect to the AI provider. Please check your network connection and provider URL.",
    ),
    # Context length errors
    (
        ["context length", "token limit", "maximum context", "context_length_exceeded", "max_tokens"],
        ExternalServiceError,
        "Content too large for the selected model. Try using a smaller selection or a model with a larger context window.",
    ),
    # Provider availability errors
    (
        ["500", "502", "503", "service unavailable", "overloaded", "internal server error"],
        ExternalServiceError,
        "The AI provider is temporarily unavailable. Please try again in a few minutes.",
    ),
]


def classify_error(exception: BaseException) -> tuple[type[OpenNotebookError], str]:
    """
    Classify a raw exception into a user-friendly error type and message.

    Args:
        exception: Any exception from LLM providers/Esperanto/LangChain

    Returns:
        Tuple of (exception_class, user_friendly_message)
    """
    error_str = str(exception).lower()
    error_type_name = type(exception).__name__.lower()
    combined = f"{error_type_name}: {error_str}"

    for keywords, exc_class, message in _CLASSIFICATION_RULES:
        for keyword in keywords:
            if keyword in combined:
                user_message = message if message is not None else _truncate(str(exception))
                return exc_class, user_message

    # Unclassified error - log for future improvement
    logger.warning(
        f"Unclassified LLM error ({type(exception).__name__}): {exception}"
    )
    return ExternalServiceError, f"AI service error: {_truncate(str(exception))}"


def _truncate(text: str, max_length: int = 200) -> str:
    """Truncate text to max_length to avoid leaking verbose internal details."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."
