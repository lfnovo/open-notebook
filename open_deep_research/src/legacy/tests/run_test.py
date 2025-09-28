#!/usr/bin/env python
import os
import subprocess
import sys
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

console = Console()

"""
Simplified test runner for Open Deep Research with rich console output.

Example usage:
python tests/run_test.py --all  # Run all agents with rich output
python tests/run_test.py --agent multi_agent --supervisor-model "anthropic:claude-3-7-sonnet-latest"
python tests/run_test.py --agent graph --search-api tavily
"""

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run tests for Open Deep Research with rich console output")
    parser.add_argument("--rich-output", action="store_true", default=True, help="Show rich output in terminal (default: True)")
    parser.add_argument("--experiment-name", help="Name for the LangSmith experiment")
    parser.add_argument("--agent", choices=["multi_agent", "graph"], help="Run tests for a specific agent")
    parser.add_argument("--all", action="store_true", help="Run tests for all agents")
    
    # Model configuration options
    parser.add_argument("--supervisor-model", help="Model for supervisor agent (e.g., 'anthropic:claude-3-7-sonnet-latest')")
    parser.add_argument("--researcher-model", help="Model for researcher agent (e.g., 'anthropic:claude-3-5-sonnet-latest')")
    parser.add_argument("--planner-provider", help="Provider for planner model (e.g., 'anthropic')")
    parser.add_argument("--planner-model", help="Model for planner in graph-based agent (e.g., 'claude-3-7-sonnet-latest')")
    parser.add_argument("--writer-provider", help="Provider for writer model (e.g., 'anthropic')")
    parser.add_argument("--writer-model", help="Model for writer in graph-based agent (e.g., 'claude-3-5-sonnet-latest')")
    parser.add_argument("--eval-model", help="Model for evaluating report quality (default: openai:claude-3-7-sonnet-latest)")
    parser.add_argument("--max-search-depth", help="Maximum search depth for graph agent")
    
    # Search API configuration
    parser.add_argument("--search-api", choices=["tavily", "duckduckgo"], 
                        help="Search API to use for content retrieval")
    
    args = parser.parse_args()
    
    # Define available agents and their test configurations
    agents = {
        "multi_agent": {
            "test": "tests/test_report_quality.py::test_response_criteria_evaluation",
            "topic": "Model Context Protocol",
            "description": "Testing multi_agent with a full MCP report",
            "needs_research_agent_param": True,
        },
        "graph": {
            "test": "tests/test_report_quality.py::test_response_criteria_evaluation",
            "topic": "Model Context Protocol", 
            "description": "Testing graph agent with a full MCP report",
            "needs_research_agent_param": True,
        }
    }
    
    # Determine which agents to test
    if args.agent:
        if args.agent in agents:
            agents_to_test = [args.agent]
        else:
            console.print(f"[red]Error: Unknown agent '{args.agent}'[/red]")
            console.print(f"Available agents: {', '.join(agents.keys())}")
            return 1
    elif args.all:
        agents_to_test = list(agents.keys())
    else:
        # Default to testing all agents
        agents_to_test = list(agents.keys())
    
    # Run tests for each agent
    for agent in agents_to_test:
        console.print(Rule(f"[bold blue]Testing {agent.upper()} Agent[/bold blue]"))
        
        agent_config = agents[agent]
        
        # Set up LangSmith environment for this agent
        project_name = f"ODR: Pytest"
        os.environ["LANGSMITH_PROJECT"] = project_name
        os.environ["LANGSMITH_TEST_SUITE"] = project_name
        
        # Ensure tracing is enabled
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        
        # Set up experiment name
        experiment_name = args.experiment_name if args.experiment_name else f"{agent_config['topic']}"
        os.environ["LANGSMITH_EXPERIMENT"] = experiment_name
        
        console.print(f"[dim]Project: {project_name}[/dim]")
        console.print(f"[dim]Test: {agent_config['description']}[/dim]")
        console.print(f"[dim]Experiment: {experiment_name}[/dim]")
        
        # Run the test
        console.print(f"\n[green]Running test for {agent} agent...[/green]")
        run_test(agent, agent_config, args)
    
    console.print(Rule("[bold green]All tests complete[/bold green]"))

def run_test(agent, agent_config, args):
    """Run the pytest with rich console formatting."""
    # Base pytest options (added -s to disable output capturing)
    base_pytest_options = ["-v", "-s", "--disable-warnings", "--langsmith-output"]
    
    # Build the command
    cmd = ["python", "-m", "pytest", agent_config["test"]] + base_pytest_options
    
    # Add research agent parameter if needed
    if agent_config["needs_research_agent_param"]:
        cmd.append(f"--research-agent={agent}")
    
    # Add model configurations if provided
    add_model_configs(cmd, args)
    
    # Display command in a nice panel
    console.print(Panel(
        f"[bold]Running Command:[/bold]\n[dim]{' '.join(cmd)}[/dim]",
        style="blue",
        title="pytest execution"
    ))
    
    # Run the command with real-time output (no capture)
    console.print(f"\n[yellow]Starting test execution...[/yellow]\n")
    result = subprocess.run(cmd)
    
    # Display results with rich formatting
    console.print(f"\n[yellow]Test execution completed.[/yellow]")
    if result.returncode == 0:
        console.print(Panel(
            f"[bold green]✅ Test for {agent} PASSED[/bold green]",
            style="green",
            title="Test Result"
        ))
    else:
        console.print(Panel(
            f"[bold red]❌ Test for {agent} FAILED[/bold red]\n[red]Return code: {result.returncode}[/red]",
            style="red",
            title="Test Result"
        ))

def add_model_configs(cmd, args):
    """Add model configuration arguments to command."""
    if args.supervisor_model:
        cmd.append(f"--supervisor-model={args.supervisor_model}")
    if args.researcher_model:
        cmd.append(f"--researcher-model={args.researcher_model}")
    if args.planner_provider:
        cmd.append(f"--planner-provider={args.planner_provider}")
    if args.planner_model:
        cmd.append(f"--planner-model={args.planner_model}")
    if args.writer_provider:
        cmd.append(f"--writer-provider={args.writer_provider}")
    if args.writer_model:
        cmd.append(f"--writer-model={args.writer_model}")
    if args.eval_model:
        cmd.append(f"--eval-model={args.eval_model}")
    if args.search_api:
        cmd.append(f"--search-api={args.search_api}")
    if args.max_search_depth:
        cmd.append(f"--max-search-depth={args.max_search_depth}")

if __name__ == "__main__":
    sys.exit(main() or 0)