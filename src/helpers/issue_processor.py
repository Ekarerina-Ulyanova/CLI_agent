"""
Issue processor for handling GitHub issues in daemon mode.
"""

import time
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone

from src.utils.config import settings
from src.utils.logger import get_logger
from src.github.client import GitHubClient
from src.agents.code_agent import CodeAgent
from src.agents.reviewer_agent import ReviewerAgent

logger = get_logger(__name__)


class IssueProcessor:
    """Processor for monitoring and handling GitHub issues."""
    
    def __init__(self, github_client: GitHubClient):
        self.github = github_client
        self.code_agent = CodeAgent(github_client)
        self.reviewer_agent = ReviewerAgent(github_client)
        self.processed_issues = set()
        self.last_check_time = None
    
    def process_pending_issues(self) -> Dict[str, Any]:
        """Process all pending issues that need attention."""
        results = {
            "issues_processed": 0,
            "prs_reviewed": 0,
            "errors": []
        }
        
        try:
            new_issues = self._get_new_issues()
            for issue in new_issues:
                try:
                    pr_number = self.code_agent.process_issue(issue.number)
                    if pr_number:
                        results["issues_processed"] += 1
                        self.processed_issues.add(issue.number)
                except Exception as e:
                    results["errors"].append(f"Issue #{issue.number}: {e}")

            pending_prs = self._get_pending_prs()
            for pr in pending_prs:
                try:
                    self.reviewer_agent.review_pull_request(pr.number)
                    results["prs_reviewed"] += 1
                except Exception as e:
                    results["errors"].append(f"PR #{pr.number}: {e}")
            
            self.last_check_time = datetime.now()
            
        except Exception as e:
            logger.error(f"Failed to process issues: {e}")
            results["errors"].append(f"Processor error: {e}")
        
        return results
    
    def _get_new_issues(self) -> List[Any]:
        """Get new issues that haven't been processed."""
        all_issues = self.github.get_open_issues()
        new_issues = []
        
        for issue in all_issues:
            if issue.number in self.processed_issues:
                continue

            labels = {label.name for label in issue.labels}
            if any(label in labels for label in ["in-progress", "processed", "agent-handled"]):
                self.processed_issues.add(issue.number)
                continue

            created_at = issue.created_at
            if isinstance(created_at, datetime):
                current_time = datetime.now(timezone.utc)
                
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                
                time_diff = current_time - created_at
                if time_diff < timedelta(hours=24):
                    new_issues.append(issue)
        
        return new_issues
    
    def _get_pending_prs(self) -> List[Any]:
        """Get PRs that need review."""
        repo = self.github.repo
        open_prs = list(repo.get_pulls(state='open'))
        
        pending_prs = []
        for pr in open_prs:
            labels = {label.name for label in pr.labels}
            
            if "approved" in labels:
                continue

            updated_at = pr.updated_at
            if isinstance(updated_at, datetime):
                current_time = datetime.now(timezone.utc)
                
                if updated_at.tzinfo is None:
                    updated_at = updated_at.replace(tzinfo=timezone.utc)
                
                time_diff = current_time - updated_at
                if time_diff < timedelta(hours=1):
                    pending_prs.append(pr)
        
        return pending_prs