"""
Tests for Source.add_insight() raising on submission failure instead of
silently swallowing it.

Previously, if submit_command() failed, add_insight() logged the error and
returned None. Both callers (transformation.py, source.py) discard the
return value, so a transformation could report success=True while the
insight was never persisted. add_insight() now matches the sibling
vectorize() method's contract: submission failures raise
DatabaseOperationError so they propagate to the job-level retry/failure
handling that already exists in commands/source_commands.py.
"""

from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_notebook.domain.notebook import Source
from open_notebook.exceptions import DatabaseOperationError, InvalidInputError


def make_source(**overrides):
    defaults = dict(id="source:test123", title="Test Source", asset=None)
    defaults.update(overrides)
    return Source(**defaults)


class TestAddInsightRaisesOnSubmissionFailure:
    @pytest.mark.asyncio
    async def test_returns_command_id_on_success(self):
        source = make_source()
        with patch(
            "open_notebook.domain.notebook.submit_command",
            return_value="command:abc123",
        ):
            result = await source.add_insight("Summary", "some content")
        assert result == "command:abc123"

    @pytest.mark.asyncio
    async def test_raises_database_operation_error_on_submission_failure(self):
        source = make_source()
        with patch(
            "open_notebook.domain.notebook.submit_command",
            side_effect=RuntimeError("queue unavailable"),
        ):
            with pytest.raises(DatabaseOperationError):
                await source.add_insight("Summary", "some content")

    @pytest.mark.asyncio
    async def test_still_raises_invalid_input_for_empty_content(self):
        source = make_source()
        with pytest.raises(InvalidInputError):
            await source.add_insight("Summary", "")

    @pytest.mark.asyncio
    async def test_still_raises_invalid_input_for_empty_type(self):
        source = make_source()
        with pytest.raises(InvalidInputError):
            await source.add_insight("", "some content")


class TestTransformationGraphPropagatesFailure:
    """open_notebook/graphs/transformation.py: run_transformation()."""

    @pytest.mark.asyncio
    async def test_add_insight_failure_propagates_out_of_run_transformation(self):
        from open_notebook.graphs.transformation import run_transformation

        source = make_source()
        transformation = MagicMock(title="Summary", prompt="Summarize this")

        fake_response = MagicMock()
        fake_response.content = "the transformation output"
        fake_chain = AsyncMock()
        fake_chain.ainvoke = AsyncMock(return_value=fake_response)

        state = {
            "source": source,
            "input_text": None,
            "transformation": transformation,
        }

        with (
            patch(
                "open_notebook.graphs.transformation.DefaultPrompts",
                return_value=MagicMock(transformation_instructions=None),
            ),
            patch(
                "open_notebook.graphs.transformation.Prompter"
            ) as mock_prompter_cls,
            patch(
                "open_notebook.graphs.transformation.provision_langchain_model",
                new=AsyncMock(return_value=fake_chain),
            ),
            patch.object(
                Source,
                "add_insight",
                new=AsyncMock(side_effect=DatabaseOperationError("submission failed")),
            ) as mock_add_insight,
        ):
            mock_prompter_cls.return_value.render.return_value = "rendered prompt"
            source.full_text = "full text of the source"

            with pytest.raises(DatabaseOperationError):
                await run_transformation(state, config={"configurable": {}})

        mock_add_insight.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_successful_add_insight_returns_output_normally(self):
        from open_notebook.graphs.transformation import run_transformation

        source = make_source()
        transformation = MagicMock(title="Summary", prompt="Summarize this")

        fake_response = MagicMock()
        fake_response.content = "the transformation output"
        fake_chain = AsyncMock()
        fake_chain.ainvoke = AsyncMock(return_value=fake_response)

        state = {
            "source": source,
            "input_text": None,
            "transformation": transformation,
        }

        with (
            patch(
                "open_notebook.graphs.transformation.DefaultPrompts",
                return_value=MagicMock(transformation_instructions=None),
            ),
            patch(
                "open_notebook.graphs.transformation.Prompter"
            ) as mock_prompter_cls,
            patch(
                "open_notebook.graphs.transformation.provision_langchain_model",
                new=AsyncMock(return_value=fake_chain),
            ),
            patch.object(
                Source, "add_insight", new=AsyncMock(return_value="command:ok")
            ) as mock_add_insight,
        ):
            mock_prompter_cls.return_value.render.return_value = "rendered prompt"
            source.full_text = "full text of the source"

            result = await run_transformation(state, config={"configurable": {}})

        mock_add_insight.assert_awaited_once()
        assert result == {"output": "the transformation output"}


class TestSourceGraphTransformContentPropagatesFailure:
    """open_notebook/graphs/source.py: transform_content() - the other
    add_insight() caller, invoked during initial source ingestion."""

    @pytest.mark.asyncio
    async def test_add_insight_failure_propagates_out_of_transform_content(self):
        from open_notebook.graphs.source import TransformationState, transform_content

        source = make_source()
        source.full_text = "the source's full text"
        transformation = MagicMock(title="Summary")

        state = {"source": source, "transformation": transformation}

        with (
            patch(
                "open_notebook.graphs.source.transform_graph.ainvoke",
                new=AsyncMock(return_value={"output": "transformed output"}),
            ),
            patch.object(
                Source,
                "add_insight",
                new=AsyncMock(side_effect=DatabaseOperationError("submission failed")),
            ) as mock_add_insight,
        ):
            with pytest.raises(DatabaseOperationError):
                # cast: mocks stand in for the real Source/Transformation
                await transform_content(cast(TransformationState, state))

        mock_add_insight.assert_awaited_once()


class TestRunTransformationCommandDoesNotReportFalseSuccess:
    """commands/source_commands.py: run_transformation_command()."""

    @pytest.mark.asyncio
    async def test_add_insight_submission_failure_does_not_return_success_true(self):
        from commands.source_commands import (
            RunTransformationInput,
            run_transformation_command,
        )

        source = make_source()
        transformation = MagicMock(id="transformation:1")

        input_data = RunTransformationInput(
            source_id="source:test123", transformation_id="transformation:1"
        )

        with (
            patch(
                "commands.source_commands.Source.get",
                new=AsyncMock(return_value=source),
            ),
            patch(
                "commands.source_commands.Transformation.get",
                new=AsyncMock(return_value=transformation),
            ),
            patch(
                "commands.source_commands.transform_graph.ainvoke",
                new=AsyncMock(
                    side_effect=DatabaseOperationError("insight submission failed")
                ),
            ),
        ):
            with pytest.raises(DatabaseOperationError):
                await run_transformation_command(input_data)
