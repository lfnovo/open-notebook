from langchain.output_parsers import OutputFixingParser
from loguru import logger

from open_notebook.config import DEFAULT_MODELS
from open_notebook.models import get_model
from open_notebook.prompter import Prompter
from open_notebook.utils import token_count


def run_pattern(
    pattern_name: str,
    model_id=None,
    messages=[],
    state: dict = {},
    parser=None,
    output_fixing_model_id=None,
) -> dict:
    system_prompt = Prompter(prompt_template=pattern_name, parser=parser).render(
        data=state
    )

    tokens = token_count(str(system_prompt) + str(messages))

    model_id = (
        DEFAULT_MODELS.large_context_model
        or DEFAULT_MODELS.default_transformation_model
        or DEFAULT_MODELS.default_chat_model
    )
    if tokens > 105_000:
        model_id = DEFAULT_MODELS.large_context_model
        logger.debug(
            f"Using large context model ({model_id}) because the content has {tokens} tokens"
        )

    model_id = (
        model_id
        or DEFAULT_MODELS.default_transformation_model
        or DEFAULT_MODELS.default_chat_model
    )

    chain = get_model(model_id, model_type="language")
    if parser:
        chain = chain | parser

    if output_fixing_model_id and parser:
        output_fix_model = get_model(output_fixing_model_id, model_type="language")
        chain = chain | OutputFixingParser.from_llm(
            parser=parser,
            llm=output_fix_model,
        )

    if len(messages) > 0:
        response = chain.invoke([system_prompt] + messages)
    else:
        response = chain.invoke(system_prompt)

    return response
