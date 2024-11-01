from langchain.output_parsers import OutputFixingParser
from loguru import logger

from open_notebook.domain.models import DefaultModels
from open_notebook.models import model_manager
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
    DEFAULT_MODELS = DefaultModels.load()
    tokens = token_count(str(system_prompt) + str(messages))

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

    chain = model_manager.get_default_model("transformation")
    if parser:
        chain = chain | parser

    if output_fixing_model_id and parser:
        output_fix_model = model_manager.get_model(output_fixing_model_id)
        chain = chain | OutputFixingParser.from_llm(
            parser=parser,
            llm=output_fix_model,
        )

    if len(messages) > 0:
        response = chain.invoke([system_prompt] + messages)
    else:
        response = chain.invoke(system_prompt)

    return response
