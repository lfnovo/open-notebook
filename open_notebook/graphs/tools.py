from datetime import datetime

from langchain.tools import tool


@tool
def get_current_timestamp() -> str:
    """
    name: get_current_timestamp
    Returns the current timestamp in the format YYYYMMDDHHmmss.
    """
    return datetime.now().strftime("%Y%m%d%H%M%S")


# @tool
# def doc_query(doc_id: str, question: str):
#     """
#     name: doc_query
#     Use this tool if you need to investigate into a particular document.
#     Another LLM will read the document and answer the question that you might have.
#     Use this when the user question cannot be answered with the content you have in context.
#     """
#     from temp.doc_query import graph

#     result = graph.invoke({"doc_id": doc_id, "question": question})
#     return result["answer"]
