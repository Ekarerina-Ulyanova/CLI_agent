"""
Issue processor for handling GitHub issues in daemon mode.
"""

from typing import Any, Dict, List

from src.agents.code_agent import CodeAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.github.client import GitHubClient
from src.utils.config import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class IssueProcessor:
    """Processor for monitoring and handling GitHub issues."""

    def __init__(self, github_client: GitHubClient, settings: Settings):
        self.github = github_client
        self.settings = settings
        self.code_agent = CodeAgent(github_client, settings)
        self.reviewer_agent = ReviewerAgent(github_client, settings)

    def process_pending_issues(self) -> Dict[str, Any]:
        """Process all pending issues that need attention."""
        results = {"issues_processed": 0, "prs_reviewed": 0, "errors": []}

        try:
            new_issues = self._get_new_issues()
            for issue in new_issues:
                try:
                    pr_number = self.code_agent.process_issue(issue.number)
                    if pr_number:
                        results["issues_processed"] += 1
                except Exception as e:
                    results["errors"].append(f"Issue #{issue.number}: {e}")

            pending_prs = self._get_pending_prs()
            for pr in pending_prs:
                try:
                    self.reviewer_agent.review_pull_request(pr.number)
                    results["prs_reviewed"] += 1
                except Exception as e:
                    results["errors"].append(f"PR #{pr.number}: {e}")

        except Exception as e:
            logger.error(f"Failed to process issues: {e}")
            results["errors"].append(f"Processor error: {e}")

        return results

    def _get_new_issues(self) -> List[Any]:
        """Get explicitly opted-in issues that have not reached a terminal state."""
        all_issues = self.github.get_open_issues()
        new_issues = []

        for issue in all_issues:
            if issue.pull_request:
                continue
            labels = {label.name for label in issue.labels}
            if self.settings.issue_label not in labels:
                continue
            if any(
                label in labels for label in ["in-progress", "needs-review", "ready", "blocked"]
            ):
                continue
            new_issues.append(issue)

        return new_issues

    def _get_pending_prs(self) -> List[Any]:
        """Get only agent PRs explicitly marked for review, once per revision."""
        repo = self.github.repo
        open_prs = list(repo.get_pulls(state="open"))

        pending_prs = []
        for pr in open_prs:
            labels = {label.name for label in pr.labels}

            if (
                self.settings.pr_label not in labels
                or self.settings.review_pending_label not in labels
            ):
                continue
            if self.settings.reviewed_label in labels or pr.draft:
                continue
            pending_prs.append(pr)

        return pending_prs
