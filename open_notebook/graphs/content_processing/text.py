import asyncio

from loguru import logger

from open_notebook.graphs.content_processing.state import ContentState


async def extract_txt(state: ContentState):
    """
    Parse the text file and extract its content asynchronously.
    """
    return_dict = {}
    if (
        state.get("file_path") is not None
        and state.get("identified_type") == "text/plain"
    ):
        logger.debug(f"Extracting text from {state.get('file_path')}")
        file_path = state.get("file_path")

        if file_path is not None:
            try:

                def _read_file():
                    with open(file_path, "r", encoding="utf-8") as file:
                        return file.read()

                # Run file I/O in thread pool
                content = await asyncio.get_event_loop().run_in_executor(
                    None, _read_file
                )

                logger.debug(f"Extracted: {content[:100]}")
                return_dict["content"] = content

            except FileNotFoundError:
                raise FileNotFoundError(f"File not found at {file_path}")
            except Exception as e:
                raise Exception(f"An error occurred: {e}")

    return return_dict
