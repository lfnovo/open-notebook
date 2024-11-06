from datetime import datetime
from typing import List

from langchain.tools import tool

from open_notebook.domain.notebook import hybrid_search


# todo: turn this into a system prompt variable
@tool
def get_current_timestamp() -> str:
    """
    name: get_current_timestamp
    Returns the current timestamp in the format YYYYMMDDHHmmss.
    """
    return datetime.now().strftime("%Y%m%d%H%M%S")


@tool
def repository_search(keyword_searches: List[str], vector_searches: List[str]) -> str:
    """
    name: repository_search
    Makes a search in the content repository for the given query.
    keyword_searches: List[str] - A list of search terms to search for using keyword search.
    vector_searches: List[str] - A list of search terms to search for using vector search.
    """
    return hybrid_search(keyword_searches, vector_searches, 20)
