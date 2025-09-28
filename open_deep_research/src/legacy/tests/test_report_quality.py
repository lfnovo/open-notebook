#!/usr/bin/env python

import os
import uuid
import pytest
import asyncio
from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model
from langsmith import testing as t
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

# Import the report generation agents
from legacy.graph import builder
from legacy.multi_agent import supervisor_builder

# Initialize rich console with force_terminal to ensure output even when pytest captures stdout
console = Console(force_terminal=True, width=120)

class CriteriaGrade(BaseModel):
    """Score the response against specific criteria."""
    grade: bool = Field(description="Does the response meet the provided criteria?")
    justification: str = Field(description="The justification for the grade and score, including specific examples from the response.")

# Function to create evaluation LLM at test time
def get_evaluation_llm(eval_model=None):
    """Create and return an evaluation LLM.
    
    Args:
        eval_model: Model identifier to use for evaluation
                    Format: "provider:model_name" (e.g., "anthropic:claude-3-7-sonnet-latest")
                    If None, it will use environment variable or default
    
    Returns:
        Structured LLM for generating evaluation grades
    """
    # Use provided model, then environment variable, then default
    model_to_use = eval_model or os.environ.get("EVAL_MODEL", "anthropic:claude-3-7-sonnet-latest")
    
    criteria_eval_llm = init_chat_model(model_to_use)
    return criteria_eval_llm.with_structured_output(CriteriaGrade)

RESPONSE_CRITERIA_SYSTEM_PROMPT = """
You are evaluating the quality of a research report. Please assess the report against the following criteria, being especially strict about section relevance.

1. Topic Relevance (Overall): Does the report directly address the user's input topic thoroughly?

2. Section Relevance (Critical): CAREFULLY assess each individual section for relevance to the main topic:
   - Identify each section by its ## header
   - For each section, determine if it is directly relevant to the primary topic
   - Flag any sections that seem tangential, off-topic, or only loosely connected to the main topic
   - A high-quality report should have NO irrelevant sections

3. Structure and Flow: Do the sections flow logically from one to the next, creating a cohesive narrative?

4. Introduction Quality: Does the introduction effectively provide context and set up the scope of the report?

5. Conclusion Quality: Does the conclusion meaningfully summarize key findings and insights from the report?

6. Structural Elements: Does the report use structural elements (e.g., tables, lists) to effectively convey information?

7. Section Headers: Are section headers properly formatted with Markdown (# for title, ## for sections, ### for subsections)?

8. Citations: Does the report properly cite sources in each main body section?

9. Overall Quality: Is the report well-researched, accurate, and professionally written?

Evaluation Instructions:
- Be STRICT about section relevance - ALL sections must clearly connect to the primary topic
- A report with even ONE irrelevant section should be considered flawed
- You must individually mention each section by name and assess its relevance
- Provide specific examples from the report to justify your evaluation for each criterion
- The report fails if any sections are irrelevant to the main topic, regardless of other qualities
""" 

# Define fixtures for test configuration
@pytest.fixture
def research_agent(request):
    """Get the research agent type from command line or environment variable."""
    return request.config.getoption("--research-agent") or os.environ.get("RESEARCH_AGENT", "multi_agent")

@pytest.fixture
def search_api(request):
    """Get the search API from command line or environment variable."""
    return request.config.getoption("--search-api") or os.environ.get("SEARCH_API", "tavily")

@pytest.fixture
def eval_model(request):
    """Get the evaluation model from command line or environment variable."""
    return request.config.getoption("--eval-model") or os.environ.get("EVAL_MODEL", "anthropic:claude-3-7-sonnet-latest")

@pytest.fixture
def models(request, research_agent):
    """Get model configurations based on agent type."""
    if research_agent == "multi_agent":
        return {
            "supervisor_model": (
                request.config.getoption("--supervisor-model") or 
                os.environ.get("SUPERVISOR_MODEL", "anthropic:claude-3-7-sonnet-latest")
            ),
            "researcher_model": (
                request.config.getoption("--researcher-model") or 
                os.environ.get("RESEARCHER_MODEL", "anthropic:claude-3-5-sonnet-latest")
            ),
        }
    else:  # graph agent
        return {
            "planner_provider": (
                request.config.getoption("--planner-provider") or 
                os.environ.get("PLANNER_PROVIDER", "anthropic")
            ),
            "planner_model": (
                request.config.getoption("--planner-model") or 
                os.environ.get("PLANNER_MODEL", "claude-3-7-sonnet-latest")
            ),
            "writer_provider": (
                request.config.getoption("--writer-provider") or 
                os.environ.get("WRITER_PROVIDER", "anthropic")
            ),
            "writer_model": (
                request.config.getoption("--writer-model") or 
                os.environ.get("WRITER_MODEL", "claude-3-5-sonnet-latest")
            ),
            "max_search_depth": int(
                request.config.getoption("--max-search-depth") or 
                os.environ.get("MAX_SEARCH_DEPTH", "2")
            ),
        }

# Note: Command line options are defined in conftest.py
# These fixtures still work with options defined there

@pytest.mark.langsmith
def test_response_criteria_evaluation(research_agent, search_api, models, eval_model):
    """Test if a report meets the specified quality criteria."""
    console.print(Panel.fit(
        f"[bold blue]Testing {research_agent} report generation with {search_api} search[/bold blue]",
        title="Test Configuration"
    ))
    
    # Create a table for model configuration
    models_table = Table(title="Model Configuration")
    models_table.add_column("Parameter", style="cyan")
    models_table.add_column("Value", style="green")
    
    for key, value in models.items():
        models_table.add_row(key, str(value))
    models_table.add_row("eval_model", eval_model)
    
    console.print(models_table)
    
    # Log inputs to LangSmith
    t.log_inputs({
        "agent_type": research_agent, 
        "search_api": search_api,
        "models": models,
        "eval_model": eval_model,
        "test": "report_quality_evaluation",
        "description": f"Testing report quality for {research_agent} with {search_api}"
    })
 
    # Run the appropriate agent based on the parameter
    if research_agent == "multi_agent":

        # Initial messages
        initial_msg = [{"role": "user", "content": "Give me a high-level overview of MCP (model context protocol). Keep the report to 3 main body sections. One section on the origins of MPC, one section on interesting examples of MCP servers, and one section on the future roadmap for MCP. Report should be written for a developer audience."}]

        # Checkpointer for the multi-agent approach
        checkpointer = MemorySaver()
        graph = supervisor_builder.compile(checkpointer=checkpointer)

        # Create configuration with the provided parameters
        config = {
            "thread_id": str(uuid.uuid4()),
            "search_api": search_api,
            "supervisor_model": models.get("supervisor_model"),
            "researcher_model": models.get("researcher_model"),
            "ask_for_clarification": False, # Don't ask for clarification from the user and proceed to write the report
            "process_search_results": "summarize", # Optionally summarize 
        }
        
        thread_config = {"configurable": config}

        # Run the workflow with asyncio
        asyncio.run(graph.ainvoke({"messages": initial_msg}, config=thread_config))
        
        # Get the final state once both invocations are complete
        final_state = graph.get_state(thread_config)
        report = final_state.values.get('final_report', "No report generated")
        console.print(f"[bold green]Report generated with length: {len(report)} characters[/bold green]")

    elif research_agent == "graph":
        
        # Topic query 
        topic_query = "Give me a high-level overview of MCP (model context protocol). Keep the report to 3 main body sections. One section on the origins of MPC, one section on interesting examples of MCP servers, and one section on the future roadmap for MCP. Report should be written for a developer audience."
   
        # Checkpointer for the graph approach
        checkpointer = MemorySaver()
        graph = builder.compile(checkpointer=checkpointer)
        
        # Configuration for the graph agent with provided parameters
        thread = {"configurable": {
            "thread_id": str(uuid.uuid4()),
            "search_api": search_api,
            "planner_provider": models.get("planner_provider", "anthropic"),
            "planner_model": models.get("planner_model", "claude-3-7-sonnet-latest"),
            "writer_provider": models.get("writer_provider", "anthropic"),
            "writer_model": models.get("writer_model", "claude-3-5-sonnet-latest"),
            "max_search_depth": models.get("max_search_depth", 2),
        }}
        
        async def run_graph_agent(thread):    
            # Run the graph until the interruption
            async for event in graph.astream({"topic":topic_query}, thread, stream_mode="updates"):
                if '__interrupt__' in event:
                    interrupt_value = event['__interrupt__'][0].value

            # Pass True to approve the report plan and proceed to write the report
            async for event in graph.astream(Command(resume=True), thread, stream_mode="updates"):
                # console.print(f"[dim]{event}[/dim]")
                # console.print()
                None
            
            final_state = graph.get_state(thread)
            report = final_state.values.get('final_report', "No report generated")
            return report
    
        report = asyncio.run(run_graph_agent(thread))

    # Get evaluation LLM using the specified model
    criteria_eval_structured_llm = get_evaluation_llm(eval_model)
    
    # Evaluate the report against our quality criteria
    eval_result = criteria_eval_structured_llm.invoke([
        {"role": "system", "content": RESPONSE_CRITERIA_SYSTEM_PROMPT},
        {"role": "user", "content": f"""\n\n Report: \n\n{report}\n\nEvaluate whether the report meets the criteria and provide detailed justification for your evaluation."""}
    ])

    # Extract section headers for analysis
    import re
    section_headers = re.findall(r'##\s+([^\n]+)', report)
    
    # Display the generated report
    console.print(Panel(
        Markdown(report),
        title="Generated Report",
        border_style="blue"
    ))
    
    # Create evaluation results display
    result_color = "green" if eval_result.grade else "red"
    result_text = "PASSED" if eval_result.grade else "FAILED"
    
    console.print(Panel.fit(
        f"[bold {result_color}]{result_text}[/bold {result_color}]",
        title="Evaluation Result"
    ))
    
    # Create sections table
    sections_table = Table(title="Report Structure Analysis")
    sections_table.add_column("Section", style="cyan")
    sections_table.add_column("Header", style="yellow")
    
    for i, header in enumerate(section_headers, 1):
        sections_table.add_row(f"Section {i}", header)
    
    console.print(sections_table)
    console.print(f"[bold]Total sections found: {len(section_headers)}[/bold]")
    
    # Display justification in a panel
    console.print(Panel(
        eval_result.justification,
        title="Evaluation Justification",
        border_style="yellow"
    ))
    
    # Log outputs to LangSmith
    t.log_outputs({
        "report": report,
        "evaluation_result": eval_result.grade,
        "justification": eval_result.justification,
        "report_length": len(report),
        "section_count": len(section_headers),
        "section_headers": section_headers,
    })
    
    # Test passes if the evaluation criteria are met
    assert eval_result.grade