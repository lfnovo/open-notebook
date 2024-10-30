from langchain.output_parsers import OutputFixingParser
from loguru import logger

from open_notebook.config import DEFAULT_MODELS
from open_notebook.models import get_model
from open_notebook.prompter import Prompter
from open_notebook.utils import token_count


def run_pattern(
    pattern_name: str,
    model_name=None,
    messages=[],
    state: dict = {},
    parser=None,
    output_fixing_model_name=None,
) -> dict:
    system_prompt = Prompter(prompt_template=pattern_name, parser=parser).render(
        data=state
    )

    tokens = token_count(str(system_prompt) + str(messages))
    if tokens > 105_000 and DEFAULT_MODELS.large_context_model:
        model_name = DEFAULT_MODELS.large_context_model
        logger.debug(
            f"Using large context model ({model_name}) because the content has {tokens} tokens"
        )
        logger.warning(system_prompt)
    elif tokens > 105_000 and not DEFAULT_MODELS.large_context_model:
        logger.critical(
            f"Content has {tokens} tokens, but no large context model is configured"
        )
    elif not model_name:
        model_name = DEFAULT_MODELS.default_transformation_model

    chain = get_model(model_name, model_type="language")
    if parser:
        chain = chain | parser

    if output_fixing_model_name and parser:
        output_fix_model = get_model(output_fixing_model_name, model_type="language")
        chain = chain | OutputFixingParser.from_llm(
            parser=parser,
            llm=output_fix_model,
        )

    if len(messages) > 0:
        response = chain.invoke([system_prompt] + messages)
    else:
        response = chain.invoke(system_prompt)

    return response
