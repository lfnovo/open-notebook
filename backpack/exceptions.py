class BackpackError(Exception):
    """Base exception class for Backpack errors."""

    pass


class DatabaseOperationError(BackpackError):
    """Raised when a database operation fails."""

    pass


class UnsupportedTypeException(BackpackError):
    """Raised when an unsupported type is provided."""

    pass


class InvalidInputError(BackpackError):
    """Raised when invalid input is provided."""

    pass


class NotFoundError(BackpackError):
    """Raised when a requested resource is not found."""

    pass


class AuthenticationError(BackpackError):
    """Raised when there's an authentication problem."""

    pass


class ConfigurationError(BackpackError):
    """Raised when there's a configuration problem."""

    pass


class ExternalServiceError(BackpackError):
    """Raised when an external service (e.g., AI model) fails."""

    pass


class RateLimitError(BackpackError):
    """Raised when a rate limit is exceeded."""

    pass


class FileOperationError(BackpackError):
    """Raised when a file operation fails."""

    pass


class NetworkError(BackpackError):
    """Raised when a network operation fails."""

    pass


class NoTranscriptFound(BackpackError):
    """Raised when no transcript is found for a video."""

    pass
