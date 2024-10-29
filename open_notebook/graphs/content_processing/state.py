from typing_extensions import TypedDict


class SourceState(TypedDict):
    content: str
    file_path: str
    url: str
    title: str
    source_type: str
    identified_type: str
    identified_provider: str
    metadata: dict
    delete_source: bool = False
