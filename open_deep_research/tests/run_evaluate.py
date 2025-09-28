from langsmith import Client
from tests.evaluators import eval_overall_quality, eval_relevance, eval_structure, eval_correctness, eval_groundedness, eval_completeness
from dotenv import load_dotenv
import asyncio
from open_deep_research.deep_researcher import deep_researcher_builder
from langgraph.checkpoint.memory import MemorySaver
import uuid

load_dotenv("../.env")

client = Client()

# NOTE: Configure the right dataset and evaluators
dataset_name = "Deep Research Bench"
evaluators = [eval_overall_quality, eval_relevance, eval_structure, eval_correctness, eval_groundedness, eval_completeness]
# NOTE: Configure the right parameters for the experiment, these will be logged in the metadata
max_structured_output_retries = 3
allow_clarification = False
max_concurrent_research_units = 10
search_api = "tavily" # NOTE: We use Tavily to stay consistent
max_researcher_iterations = 6
max_react_tool_calls = 10
summarization_model = "openai:gpt-4.1-mini"
summarization_model_max_tokens = 8192
research_model = "openai:gpt-5" # "anthropic:claude-sonnet-4-20250514"
research_model_max_tokens = 10000
compression_model = "openai:gpt-4.1"
compression_model_max_tokens = 10000
final_report_model = "openai:gpt-4.1"
final_report_model_max_tokens = 10000

async def target(
    inputs: dict,
):
    graph = deep_researcher_builder.compile(checkpointer=MemorySaver())
    config = {
        "configurable": {
            "thread_id": str(uuid.uuid4()),
        }
    }
    # NOTE: Configure the right dataset and evaluators
    config["configurable"]["max_structured_output_retries"] = max_structured_output_retries
    config["configurable"]["allow_clarification"] = allow_clarification
    config["configurable"]["max_concurrent_research_units"] = max_concurrent_research_units
    config["configurable"]["search_api"] = search_api
    config["configurable"]["max_researcher_iterations"] = max_researcher_iterations
    config["configurable"]["max_react_tool_calls"] = max_react_tool_calls
    config["configurable"]["summarization_model"] = summarization_model
    config["configurable"]["summarization_model_max_tokens"] = summarization_model_max_tokens
    config["configurable"]["research_model"] = research_model
    config["configurable"]["research_model_max_tokens"] = research_model_max_tokens
    config["configurable"]["compression_model"] = compression_model
    config["configurable"]["compression_model_max_tokens"] = compression_model_max_tokens
    config["configurable"]["final_report_model"] = final_report_model
    config["configurable"]["final_report_model_max_tokens"] = final_report_model_max_tokens
    # NOTE: We do not use MCP tools to stay consistent
    final_state = await graph.ainvoke(
        {"messages": [{"role": "user", "content": inputs["messages"][0]["content"]}]},
        config
    )
    return final_state

async def main():
    return await client.aevaluate(
        target,
        data=dataset_name,
        evaluators=evaluators,
        experiment_prefix=f"ODR GPT-5, Tavily Search",
        max_concurrency=10,
        metadata={
            "max_structured_output_retries": max_structured_output_retries,
            "allow_clarification": allow_clarification,
            "max_concurrent_research_units": max_concurrent_research_units,
            "search_api": search_api,
            "max_researcher_iterations": max_researcher_iterations,
            "max_react_tool_calls": max_react_tool_calls,
            "summarization_model": summarization_model,
            "summarization_model_max_tokens": summarization_model_max_tokens,
            "research_model": research_model,
            "research_model_max_tokens": research_model_max_tokens,
            "compression_model": compression_model,
            "compression_model_max_tokens": compression_model_max_tokens,
            "final_report_model": final_report_model,
            "final_report_model_max_tokens": final_report_model_max_tokens,
        }
    )

if __name__ == "__main__":
    results = asyncio.run(main())
    print(results)