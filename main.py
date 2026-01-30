"""
Main entry point for the Coding Agents system.
Handles CLI interface and service orchestration.
"""

import sys
import time
from typing import Optional

import click
from rich.console import Console

from src.utils.config import Settings
from src.utils.logger import setup_logger
from src.github.client import GitHubClient
from src.llm.openrouter_client import OpenRouterClient

console = Console()
logger = setup_logger(__name__)


@click.group()
def cli():
    """Coding Agents CLI - Automated SDLC System"""
    pass


def init_services() -> tuple:
    """
    Initialize all required services.
    
    Returns:
        tuple: (settings, github_client, llm_client)
    """
    logger.info("Initializing application services...")
    
    try:
        settings = Settings()
        logger.info(f"Settings loaded: {settings.github_repository}")

        github_client = GitHubClient(
            token=settings.github_token,
            repo_name=settings.github_repository
        )
        logger.info(f"GitHub client initialized for {github_client.repo.full_name}")

        llm_client = OpenRouterClient()
        logger.info(f"OpenRouter client initialized with model: {settings.openrouter_model}")
        
        return settings, github_client, llm_client
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}", exc_info=True)
        console.print(f"[red]Failed to initialize services: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--mode', type=click.Choice(['daemon', 'single']), default='daemon',
              help='Run mode: daemon (continuous) or single (one-time)')
@click.option('--issue-number', type=int, help='Process specific issue number')
@click.option('--pr-number', type=int, help='Review specific PR number')
def run(mode: str, issue_number: Optional[int], pr_number: Optional[int]):
    """Run the Coding Agents system."""
    logger.info(f"Starting Coding Agents system in {mode} mode")
    
    try:
        settings, github_client, llm_client = init_services()

        console.print("[yellow]Testing OpenRouter connection...[/yellow]")
        if not llm_client.test_connection():
            console.print("[red]✗ OpenRouter connection failed[/red]")
            sys.exit(1)
        console.print("[green]✓ OpenRouter connection successful[/green]")
        
        console.print("[yellow]Testing GitHub connection...[/yellow]")
        console.print(f"[green]✓ GitHub connection successful: {github_client.repo.full_name}[/green]")

        if mode == 'single':
            if issue_number:
                process_single_issue(github_client, issue_number)
            elif pr_number:
                process_single_pr(github_client, pr_number)
            else:
                click.echo("Please specify --issue-number or --pr-number for single mode")
        else:
            run_daemon(github_client)
            
    except KeyboardInterrupt:
        logger.info("System shutdown requested by user")
        console.print("[yellow]Shutting down agent...[/yellow]")
    except Exception as e:
        logger.error(f"Failed to run agent: {e}", exc_info=True)
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def process_single_issue(github_client: GitHubClient, issue_number: int):
    """Process a single GitHub issue."""
    logger.info(f"Processing single issue #{issue_number}")
    
    try:
        from src.agents.code_agent import CodeAgent
        code_agent = CodeAgent(github_client)
        pr_number = code_agent.process_issue(issue_number)
        
        if pr_number:
            console.print(f"[green]✓ Successfully created PR #{pr_number} for issue #{issue_number}[/green]")
        else:
            console.print(f"[yellow]Failed to process issue #{issue_number}[/yellow]")
    except Exception as e:
        logger.error(f"Error processing issue #{issue_number}: {e}", exc_info=True)
        console.print(f"[red]Error processing issue #{issue_number}: {e}[/red]")


def process_single_pr(github_client: GitHubClient, pr_number: int):
    """Review a single GitHub Pull Request."""
    logger.info(f"Reviewing single PR #{pr_number}")
    
    try:
        from src.agents.reviewer_agent import ReviewerAgent
        reviewer_agent = ReviewerAgent(github_client)
        result = reviewer_agent.review_pull_request(pr_number)
        
        console.print(f"[green]✓ Successfully reviewed PR #{pr_number}[/green]")
    except Exception as e:
        logger.error(f"Error reviewing PR #{pr_number}: {e}", exc_info=True)
        console.print(f"[red]Error reviewing PR #{pr_number}: {e}[/red]")


def run_daemon(github_client: GitHubClient):
    """Run agent in daemon mode, continuously monitoring for new issues."""
    console.print("[green]Starting agent in daemon mode[/green]")
    
    from src.agents.issue_processor import IssueProcessor
    processor = IssueProcessor(github_client)
    check_interval = 60  # seconds
    
    try:
        while True:
            try:
                processor.process_pending_issues()
                time.sleep(check_interval)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.error(f"Error in daemon mode: {e}")
                time.sleep(10)
    except KeyboardInterrupt:
        console.print("[yellow]Shutting down agent...[/yellow]")


@cli.command()
def test_openrouter():
    """Test OpenRouter API connection and model."""
    console.print("[bold]Testing OpenRouter API[/bold]")
    
    try:
        settings, _, llm_client = init_services()
        
        if llm_client.test_connection():
            console.print("[green]✓ API Connection: OK[/green]")
            
            console.print("[yellow]Testing text generation...[/yellow]")
            messages = [
                llm_client.create_system_message("You are a helpful assistant."),
                llm_client.create_human_message("Say 'Hello from Coding Agent' in a creative way.")
            ]
            
            response = llm_client.generate(messages, max_tokens=50)
            console.print(f"[green]✓ Text Generation: OK[/green]")
            console.print(f"[blue]Response: {response}[/blue]")
        else:
            console.print("[red]✗ API Connection: FAILED[/red]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


if __name__ == '__main__':
    logger.info("Starting Coding Agents CLI")
    cli()