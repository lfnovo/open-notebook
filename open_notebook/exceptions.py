from typing import Optional


class OpenNotebookError(Exception):
    """Base exception class for Open Notebook errors."""

    pass


class DatabaseOperationError(OpenNotebookError):
    """Raised when a database operation fails."""

    pass


class UnsupportedTypeException(OpenNotebookError):
    """Raised when an unsupported type is provided."""

    pass


class InvalidInputError(OpenNotebookError):
    """Raised when invalid input is provided."""

    pass


class NotFoundError(OpenNotebookError):
    """Raised when a requested resource is not found."""

    pass


class ConflictError(OpenNotebookError):
    """Raised when a request collides with existing state.

    For example a unique index rejecting a second record under a name that is
    already taken. The client can resolve this by choosing another name, so it
    is a 4xx, not a server failure.
    """

    pass


class AuthenticationError(OpenNotebookError):
    """Raised when there's an authentication problem."""

    pass


class ConfigurationError(OpenNotebookError):
    """Raised when there's a configuration problem."""

    pass


class ExternalServiceError(OpenNotebookError):
    """Raised when an external service (e.g., AI model) fails."""

    pass


class IncompleteGenerationError(ExternalServiceError):
    """The model returned truncated or empty output; do not retry automatically."""

    pass


class ContextLengthExceededError(ExternalServiceError):
    """Content exceeds the model's context window. Retrying sends the same
    oversized payload, so background commands must not retry this."""

    pass


class RateLimitError(OpenNotebookError):
    """Raised when a rate limit is exceeded."""

    pass


class FileOperationError(OpenNotebookError):
    """Raised when a file operation fails."""

    pass


class NetworkError(OpenNotebookError):
    """Raised when a network operation fails."""

    pass


class NoTranscriptFound(OpenNotebookError):
    """Raised when no transcript is found for a video."""

    pass


# SurrealDB reports a rejected unique index in the message rather than through a
# dedicated driver exception (the driver only exposes SurrealDBMethodError), so
# the phrase is the only signal available. The repository layer already keys off
# the same wording to skip duplicates on bulk insert; keep the two in step.
_UNIQUE_INDEX_REJECTED = "already contains"


def as_name_conflict(exc: Exception, entity: str, name: str) -> Optional[ConflictError]:
    """Translate a rejected unique index into a typed :class:`ConflictError`.

    Returns ``None`` when ``exc`` is not a duplicate-name rejection, so callers
    can keep treating every other failure the way they did before.
    """
    if _UNIQUE_INDEX_REJECTED not in str(exc):
        return None
    return ConflictError(f"An {entity} named '{name}' already exists")
