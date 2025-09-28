"""
Pytest configuration for open_deep_research tests.
"""

import pytest

def pytest_addoption(parser):
    """Add command-line options to pytest."""
    parser.addoption("--research-agent", action="store", help="Agent type: multi_agent or graph")
    parser.addoption("--search-api", action="store", help="Search API to use")
    parser.addoption("--eval-model", action="store", help="Model for evaluation")
    parser.addoption("--supervisor-model", action="store", help="Model for supervisor agent")
    parser.addoption("--researcher-model", action="store", help="Model for researcher agent")
    parser.addoption("--planner-provider", action="store", help="Provider for planner model")
    parser.addoption("--planner-model", action="store", help="Model for planning")
    parser.addoption("--writer-provider", action="store", help="Provider for writer model")
    parser.addoption("--writer-model", action="store", help="Model for writing")
    parser.addoption("--max-search-depth", action="store", help="Maximum search depth")