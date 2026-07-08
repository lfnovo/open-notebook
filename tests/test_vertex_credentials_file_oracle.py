"""
Tests for the Vertex credentials_path file-existence oracle fix.

credentials_path (Vertex service-account file path) is free text with no
path validation (open_notebook/ai/key_provider.py sets it directly as
GOOGLE_APPLICATION_CREDENTIALS). Google's auth library raises
distinguishable exceptions - confirmed by direct reproduction against the
real library - for "file missing" (FileNotFoundError), "not valid JSON"
(json.JSONDecodeError), and "valid JSON but wrong shape"
(google.auth.exceptions.GoogleAuthError). Both api/credentials_service.py's
test_credential() (POST /credentials/{id}/test) and
connection_tester.py's test_individual_model() (POST /models/{id}/test)
used to echo the raw exception text (up to 100 chars, or the entire message
for test_individual_model) back to the API caller, including the
attacker-supplied path - turning credential/model testing into a
filesystem oracle for an attacker who can create/test a Vertex credential.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_notebook.ai.connection_tester import _is_vertex_credentials_file_error
from open_notebook.ai.connection_tester import (
    test_individual_model as run_individual_model_test,
)


def real_google_auth_exception(credentials_path: str) -> Exception:
    """Drives the real google.oauth2.service_account library to get a
    genuine exception object, rather than guessing at its shape."""
    from google.oauth2 import service_account

    try:
        service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        raise AssertionError("expected from_service_account_file to raise")
    except Exception as e:
        return e


class TestIsVertexCredentialsFileError:
    def test_classifies_missing_file(self, tmp_path):
        exc = real_google_auth_exception(str(tmp_path / "does-not-exist.json"))
        assert isinstance(exc, FileNotFoundError)
        assert _is_vertex_credentials_file_error(exc) is True

    def test_classifies_invalid_json(self, tmp_path):
        bad_json = tmp_path / "bad.json"
        bad_json.write_text("not valid json {{{")
        exc = real_google_auth_exception(str(bad_json))
        assert _is_vertex_credentials_file_error(exc) is True

    def test_classifies_wrong_shape_json(self, tmp_path):
        wrong_shape = tmp_path / "wrong_shape.json"
        wrong_shape.write_text('{"foo": "bar"}')
        exc = real_google_auth_exception(str(wrong_shape))
        assert _is_vertex_credentials_file_error(exc) is True

    def test_does_not_misclassify_unrelated_errors(self):
        assert _is_vertex_credentials_file_error(ValueError("some other error")) is False
        assert _is_vertex_credentials_file_error(RuntimeError("rate limited")) is False


class TestTestCredentialClosesOracle:
    @pytest.mark.asyncio
    async def test_missing_and_invalid_json_produce_identical_generic_message(
        self, tmp_path
    ):
        """The core of the fix: two scenarios that used to be
        distinguishable via the response message must now be identical."""
        from open_notebook.domain.credential import Credential

        missing_exc = real_google_auth_exception(str(tmp_path / "missing.json"))
        bad_json = tmp_path / "bad.json"
        bad_json.write_text("not json {{{")
        invalid_exc = real_google_auth_exception(str(bad_json))

        cred = MagicMock(spec=Credential)
        cred.provider = "vertex"
        cred.to_esperanto_config.return_value = {"project": "p", "location": "us-central1"}

        from api.credentials_service import test_credential

        with patch(
            "open_notebook.domain.credential.Credential.get",
            new=AsyncMock(return_value=cred),
        ):
            with patch(
                "esperanto.factory.AIFactory.create_language", side_effect=missing_exc
            ):
                result_missing = await test_credential("credential:test")
            with patch(
                "esperanto.factory.AIFactory.create_language", side_effect=invalid_exc
            ):
                result_invalid = await test_credential("credential:test")

        assert result_missing["message"] == "Invalid or inaccessible credentials file"
        assert result_invalid["message"] == "Invalid or inaccessible credentials file"
        assert result_missing["message"] == result_invalid["message"]
        assert str(tmp_path) not in result_missing["message"]

    @pytest.mark.asyncio
    async def test_non_vertex_provider_still_gets_detailed_message(self):
        """Only vertex has this specific file-existence oracle risk - other
        providers should be unaffected by the generic-message guard."""
        from open_notebook.domain.credential import Credential

        cred = MagicMock(spec=Credential)
        cred.provider = "openai"
        cred.to_esperanto_config.return_value = {"api_key": "sk-fake"}

        from api.credentials_service import test_credential

        with (
            patch(
                "open_notebook.domain.credential.Credential.get",
                new=AsyncMock(return_value=cred),
            ),
            patch(
                "esperanto.factory.AIFactory.create_language",
                side_effect=FileNotFoundError("unrelated file issue"),
            ),
        ):
            result = await test_credential("credential:test")

        assert result["message"] != "Invalid or inaccessible credentials file"


class TestIndividualModelClosesOracle:
    @pytest.mark.asyncio
    async def test_missing_credentials_file_returns_generic_message(self, tmp_path):
        exc = real_google_auth_exception(str(tmp_path / "missing.json"))
        model = MagicMock(id="model:vertex1", provider="vertex", type="language")

        manager_instance = MagicMock()
        manager_instance.get_model = AsyncMock(side_effect=exc)

        with patch(
            "open_notebook.ai.models.ModelManager", return_value=manager_instance
        ):
            success, message = await run_individual_model_test(model)

        assert success is False
        assert message == "Invalid or inaccessible credentials file"
        assert str(tmp_path) not in message

    @pytest.mark.asyncio
    async def test_non_vertex_provider_still_gets_detailed_message(self):
        model = MagicMock(id="model:openai1", provider="openai", type="language")

        manager_instance = MagicMock()
        manager_instance.get_model = AsyncMock(
            side_effect=FileNotFoundError("unrelated file issue")
        )

        with patch(
            "open_notebook.ai.models.ModelManager", return_value=manager_instance
        ):
            success, message = await run_individual_model_test(model)

        assert message != "Invalid or inaccessible credentials file"
