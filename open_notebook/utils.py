import re
import unicodedata
from importlib.metadata import PackageNotFoundError, version
from urllib.parse import urlparse

import requests
import tomli
from langchain_text_splitters import RecursiveCharacterTextSplitter
from packaging.version import parse as parse_version


def token_count(input_string) -> int:
    """
    Count the number of tokens in the input string using the 'o200k_base' encoding.

    Args:
        input_string (str): The input string to count tokens for.

    Returns:
        int: The number of tokens in the input string.
    """
    import tiktoken

    encoding = tiktoken.get_encoding("o200k_base")
    tokens = encoding.encode(input_string)
    token_count = len(tokens)
    return token_count


def token_cost(token_count, cost_per_million=0.150) -> float:
    """
    Calculate the cost of tokens based on the token count and cost per million tokens.

    Args:
        token_count (int): The number of tokens.
        cost_per_million (float): The cost per million tokens. Default is 0.150.

    Returns:
        float: The calculated cost for the given token count.
    """
    return cost_per_million * (token_count / 1_000_000)


def split_text(txt: str, chunk_size=500):
    """
    Split the input text into chunks.

    Args:
        txt (str): The input text to be split.
        chunk (int): The size of each chunk. Default is 1000.
        overlap (int): The number of characters to overlap between chunks. Default is 0.
        separator (str): The separator to use when splitting the text. Default is " ".

    Returns:
        list: A list of text chunks.
    """
    overlap = int(chunk_size * 0.15)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=token_count,
        separators=[
            "\n\n",
            "\n",
            ".",
            ",",
            " ",
            "\u200b",  # Zero-width space
            "\uff0c",  # Fullwidth comma
            "\u3001",  # Ideographic comma
            "\uff0e",  # Fullwidth full stop
            "\u3002",  # Ideographic full stop
            "",
        ],
    )
    return text_splitter.split_text(txt)


def remove_non_ascii(text) -> str:
    return re.sub(r"[^\x00-\x7F]+", "", text)


def remove_non_printable(text) -> str:
    # Replace any special Unicode whitespace characters with a regular space
    text = re.sub(r"[\u2000-\u200B\u202F\u205F\u3000]", " ", text)

    # Replace unusual line terminators with a single newline
    text = re.sub(r"[\u2028\u2029\r]", "\n", text)

    # Remove control characters, except newlines and tabs
    text = "".join(
        char for char in text if unicodedata.category(char)[0] != "C" or char in "\n\t"
    )

    # Replace non-breaking spaces with regular spaces
    text = text.replace("\xa0", " ").strip()

    # Keep letters (including accented ones), numbers, spaces, newlines, tabs, and basic punctuation
    return re.sub(r"[^\w\s.,!?\-\n\t]", "", text, flags=re.UNICODE)


def surreal_clean(text) -> str:
    """
    Clean the input text by removing non-ASCII and non-printable characters,
    and adjusting colon placement for SurrealDB compatibility.

    Args:
        text (str): The input text to clean.
    Returns:
        str: The cleaned text with adjusted formatting.
    """
    text = remove_non_printable(text)

    # Add space after colon if it's before the first space
    first_space_index = text.find(" ")
    colon_index = text.find(":")
    if colon_index != -1 and (
        first_space_index == -1 or colon_index < first_space_index
    ):
        text = text.replace(":", "\:", 1)

    return text


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

    # Fetch the file
    response = requests.get(raw_url)
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
