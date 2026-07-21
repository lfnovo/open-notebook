"""Tests for the opt-in runtime availability probes.

The engine choice lives in the database; the runtime that serves it comes from
environment flags evaluated at boot. engine_runtime_missing() is what keeps the
two from drifting into a state where extraction is routed to a runtime that
isn't installed.
"""

from unittest.mock import patch

from open_notebook.utils.runtime_capabilities import engine_runtime_missing


class TestEngineRuntimeMissing:
    def test_runtime_free_engines_need_nothing(self):
        """auto/simple/firecrawl/jina carry no opt-in runtime."""
        for engine in ("auto", "simple", "firecrawl", "jina"):
            assert engine_runtime_missing(engine) is None

    def test_none_and_empty_are_not_missing(self):
        assert engine_runtime_missing(None) is None
        assert engine_runtime_missing("") is None

    def test_unknown_engine_is_passed_through(self):
        """An engine we don't know about is content-core's problem, not ours."""
        assert engine_runtime_missing("some-future-engine") is None

    def test_crawl4ai_reports_its_env_var_when_absent(self):
        with patch(
            "open_notebook.utils.runtime_capabilities.crawl4ai_available",
            return_value=False,
        ):
            assert (
                engine_runtime_missing("crawl4ai") == "OPEN_NOTEBOOK_ENABLE_CRAWL4AI"
            )

    def test_crawl4ai_is_usable_when_available(self):
        with patch(
            "open_notebook.utils.runtime_capabilities.crawl4ai_available",
            return_value=True,
        ):
            assert engine_runtime_missing("crawl4ai") is None

    def test_docling_reports_its_env_var_when_absent(self):
        with patch(
            "open_notebook.utils.runtime_capabilities.docling_available",
            return_value=False,
        ):
            assert engine_runtime_missing("docling") == "OPEN_NOTEBOOK_ENABLE_DOCLING"

    def test_docling_is_usable_when_available(self):
        with patch(
            "open_notebook.utils.runtime_capabilities.docling_available",
            return_value=True,
        ):
            assert engine_runtime_missing("docling") is None

    def test_engine_name_is_normalized(self):
        """Stored values shouldn't have to be exactly lowercased to be gated."""
        with patch(
            "open_notebook.utils.runtime_capabilities.crawl4ai_available",
            return_value=False,
        ):
            assert (
                engine_runtime_missing("  Crawl4AI  ")
                == "OPEN_NOTEBOOK_ENABLE_CRAWL4AI"
            )

    def test_remote_crawl4ai_counts_as_available(self):
        """CRAWL4AI_API_URL offloads rendering — no local install needed."""
        with patch(
            "open_notebook.utils.runtime_capabilities.crawl4ai_local_ready",
            return_value=False,
        ), patch(
            "open_notebook.utils.runtime_capabilities.crawl4ai_remote_configured",
            return_value=True,
        ):
            assert engine_runtime_missing("crawl4ai") is None
