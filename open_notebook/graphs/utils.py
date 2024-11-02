from langchain.output_parsers import OutputFixingParser
from langchain_core.messages import AIMessage
from loguru import logger

from open_notebook.models import model_manager
from open_notebook.prompter import Prompter
from open_notebook.utils import token_count


def provision_model(content, config, default_type):
    """
    Returns the best model to use based on the context size and on whether there is a specific model being requested in Config.
    If context > 105_000, returns the large_context_model
    If model_id is specified in Config, returns that model
    Otherwise, returns the default model for the given type
    """
    tokens = token_count(content)

    if tokens > 105_000:
        logger.debug(
            f"Using large context model because the content has {tokens} tokens"
        )
        return model_manager.get_default_model("large_context")
    elif config.get("configurable", {}).get("model_id"):
        return model_manager.get_model(config.get("configurable", {}).get("model_id"))
    else:
        return model_manager.get_default_model(default_type)


# todo: turn into a graph
def run_pattern(
    pattern_name: str,
    config,
    messages=[],
    state: dict = {},
    parser=None,
    output_fixing_model_id=None,
) -> AIMessage:
    system_prompt = Prompter(prompt_template=pattern_name, parser=parser).render(
        data=state
    )
    chain = provision_model(
        str(system_prompt) + str(messages), config, "transformation"
    )

    if parser:
        chain = chain | parser

    if output_fixing_model_id and parser:
        output_fix_model = model_manager.get_model(output_fixing_model_id)
        chain = chain | OutputFixingParser.from_llm(
            parser=parser,
            llm=output_fix_model,
        )

    # todo: precisa deste if?
    if len(messages) > 0:
        response = chain.invoke([system_prompt] + messages)
    else:
        response = chain.invoke(system_prompt)

    return response
