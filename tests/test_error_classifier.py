"""classify_error() tells a slow provider apart from an unreachable one."""

import httpx

from open_notebook.exceptions import (
    AuthenticationError,
    ConfigurationError,
    NetworkError,
)
from open_notebook.utils.error_classifier import classify_error


def test_read_timeout_says_the_provider_was_slow():
    exc_class, message = classify_error(
        httpx.ReadTimeout("The read operation timed out")
    )
    assert exc_class is NetworkError
    assert "took too long" in message
    assert "ESPERANTO_LLM_TIMEOUT" in message


def test_openai_style_timeout_says_the_provider_was_slow():
    class APITimeoutError(Exception):
        pass

    _, message = classify_error(APITimeoutError("Request timed out."))
    assert "took too long" in message


def test_connect_timeout_is_a_connection_problem():
    exc_class, message = classify_error(httpx.ConnectTimeout("timed out"))
    assert exc_class is NetworkError
    assert "Could not connect" in message


def test_connection_refused_is_a_connection_problem():
    _, message = classify_error(httpx.ConnectError("[Errno 111] Connection refused"))
    assert "Could not connect" in message


def test_auth_error_points_to_the_models_page():
    exc_class, message = classify_error(Exception("401 invalid api key"))
    assert exc_class is AuthenticationError
    assert "Manage -> Models" in message


def test_missing_default_model_passes_through():
    raw = "No model configured for default for type=chat. Please go to Manage → Models and configure a default model for 'chat'."
    exc_class, message = classify_error(ValueError(raw))
    assert exc_class is ConfigurationError
    assert message.startswith("No model configured")
