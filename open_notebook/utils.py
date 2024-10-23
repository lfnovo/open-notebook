import re
import string

from langchain_text_splitters import CharacterTextSplitter
from openai import OpenAI

client = OpenAI()


def split_text(txt: str, chunk=1000, overlap=0, separator=" "):
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
    text_splitter = CharacterTextSplitter(
        chunk_size=chunk, chunk_overlap=overlap, separator=separator
    )
    return text_splitter.split_text(txt)


def token_count(input_string):
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


def token_cost(token_count, cost_per_million=0.150):
    """
    Calculate the cost of tokens based on the token count and cost per million tokens.

    Args:
        token_count (int): The number of tokens.
        cost_per_million (float): The cost per million tokens. Default is 0.150.

    Returns:
        float: The calculated cost for the given token count.
    """
    return cost_per_million * (token_count / 1_000_000)


def get_embedding(text, model="text-embedding-3-small"):
    """
    Get the embedding for the input text using the specified model.

    Args:
        text (str): The input text to get the embedding for.
        model (str): The name of the embedding model to use. Default is "text-embedding-3-small".

    Returns:
        list: The embedding vector for the input text.
    """
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model=model).data[0].embedding


def remove_non_ascii(text):
    return re.sub(r"[^\x00-\x7F]+", "", text)


def remove_non_printable(text):
    return "".join(filter(lambda x: x in string.printable, text))


def surreal_clean(text):
    """
    Clean the input text by removing non-ASCII and non-printable characters,
    and adjusting colon placement for SurrealDB compatibility.

    Args:
        text (str): The input text to clean.
    Returns:
        str: The cleaned text with adjusted formatting.
    """
    text = remove_non_printable(remove_non_ascii(text))

    # Add space after colon if it's before the first space
    first_space_index = text.find(" ")
    colon_index = text.find(":")
    if colon_index != -1 and (
        first_space_index == -1 or colon_index < first_space_index
    ):
        text = text.replace(":", "\:", 1)

    return text
