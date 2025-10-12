"""
Version utilities for Open Notebook.
Handles version comparison, GitHub version fetching, and package version management.
"""

from importlib.metadata import PackageNotFoundError, version
from urllib.parse import urlparse

import requests  # type: ignore
import tomli
from packaging.version import parse as parse_version


def get_version_from_github(repo_url: str, branch: str = "main") -> str:
    """
    Fetch and parse the version from pyproject.toml in a public GitHub repository.

    Args:
        repo_url (str): URL of the GitHub repository
        branch (str): Branch name to fetch from (defaults to "main")

    Returns:
        str: Version string from pyproject.toml

    Raises:
        ValueError: If the URL is not a valid GitHub repository URL
        requests.RequestException: If there's an error fetching the file
        KeyError: If version information is not found in pyproject.toml
    """
    # Parse the GitHub URL
    parsed_url = urlparse(repo_url)
    if "github.com" not in parsed_url.netloc:
        raise ValueError("Not a GitHub URL")

    # Extract owner and repo name from path
    path_parts = parsed_url.path.strip("/").split("/")
    if len(path_parts) < 2:
        raise ValueError("Invalid GitHub repository URL")

    owner, repo = path_parts[0], path_parts[1]

    # Construct raw content URL for pyproject.toml
    raw_url = (
        f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/pyproject.toml"
    )

    # Fetch the file with timeout
    response = requests.get(raw_url, timeout=10)
    response.raise_for_status()

    # Parse TOML content
    pyproject_data = tomli.loads(response.text)

    # Try to find version in different possible locations
    try:
        # Check project.version first (poetry style)
        version = pyproject_data["tool"]["poetry"]["version"]
    except KeyError:
        try:
            # Check project.version (standard style)
            version = pyproject_data["project"]["version"]
        except KeyError:
            raise KeyError("Version not found in pyproject.toml")

    return version


def get_installed_version(package_name: str) -> str:
    """
    Get the version of an installed package.

    Args:
        package_name (str): Name of the installed package

    Returns:
        str: Version string of the installed package

    Raises:
        PackageNotFoundError: If the package is not installed
    """
    try:
        return version(package_name)
    except PackageNotFoundError:
        raise PackageNotFoundError(f"Package '{package_name}' not found")


def compare_versions(version1: str, version2: str) -> int:
    """
    Compare two semantic versions.

    Args:
        version1 (str): First version string
        version2 (str): Second version string

    Returns:
        int: -1 if version1 < version2
              0 if version1 == version2
              1 if version1 > version2
    """
    v1 = parse_version(version1)
    v2 = parse_version(version2)

    if v1 < v2:
        return -1
    elif v1 > v2:
        return 1
    else:
        return 0
