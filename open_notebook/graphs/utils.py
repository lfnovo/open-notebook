import os

from langchain.output_parsers import OutputFixingParser
from loguru import logger

from open_notebook.llm_router import get_langchain_model
from open_notebook.prompter import Prompter


def run_pattern(
    pattern_name: str,
    model_name=None,
    messages=[],
    state: dict = {},
    parser=None,
    output_fixing_model_name=None,
) -> dict:
    if not model_name:
        model_name = os.environ["DEFAULT_MODEL"]

    chain = get_langchain_model(model_name)
    if parser:
        chain = chain | parser

    if output_fixing_model_name and parser:
        output_fix_model = get_langchain_model(output_fixing_model_name)
        chain = chain | OutputFixingParser.from_llm(
            parser=parser,
            llm=output_fix_model,
        )

    system_prompt = Prompter(prompt_template=pattern_name, parser=parser).render(
        data=state
    )
    # logger.debug(f"System prompt: {system_prompt}")

    if len(messages) > 0:
        logger.warning(messages)
        response = chain.invoke([system_prompt] + messages)
    else:
        response = chain.invoke(system_prompt)

    return response
