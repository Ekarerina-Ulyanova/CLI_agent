"""
GitHub API client for repository operations.
"""

import base64
from typing import Dict, List, Any, Optional
import requests
from github import Github
from github.Repository import Repository
from github.Issue import Issue
from github.PullRequest import PullRequest

from src.utils.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GitHubClient:
    """Client for GitHub API operations."""
    
    def __init__(self, token: str, repo_name: str):
        self.github = Github(token)
        self.repo = self.github.get_repo(repo_name)
        self.repo_name = repo_name
        self.token = token
        logger.info(f"Connected to repository: {self.repo.full_name}")
    
    def get_issue(self, issue_number: int) -> Issue:
        return self.repo.get_issue(number=issue_number)
    
    def get_open_issues(self) -> List[Issue]:
        return list(self.repo.get_issues(state='open'))
    
    def update_issue_status(self, issue_number: int, status: str, comment: str = "") -> None:
        """Update issue status with comment."""
        issue = self.get_issue(issue_number)
        
        if comment:
            issue.create_comment(f"**Status Update**: {status}\n\n{comment}")

        current_labels = {label.name for label in issue.labels}
        status_labels = {"in-progress", "needs-review", "ready", "blocked"}
        new_labels = current_labels - status_labels
        new_labels.add(status.lower().replace(" ", "-"))
        
        issue.set_labels(*list(new_labels))
    
    def create_branch(self, branch_name: str, base_branch: str = None) -> None:
        if base_branch is None:
            base_branch = settings.default_base_branch
        
        sb = self.repo.get_branch(base_branch)
        self.repo.create_git_ref(
            ref=f'refs/heads/{branch_name}',
            sha=sb.commit.sha
        )
    
    def get_file_content(self, file_path: str, ref: str = None) -> Optional[str]:
        try:
            content = self.repo.get_contents(file_path, ref=ref)
            return base64.b64decode(content.content).decode('utf-8')
        except Exception:
            return None
    
    def create_or_update_file(self, file_path: str, content: str, 
                             commit_message: str, branch: str) -> Dict[str, Any]:
        try:
            existing = self.repo.get_contents(file_path, ref=branch)
            result = self.repo.update_file(
                path=file_path,
                message=commit_message,
                content=content,
                sha=existing.sha,
                branch=branch
            )
            return {"status": "updated", "commit": result['commit'].sha}
        except Exception:
            result = self.repo.create_file(
                path=file_path,
                message=commit_message,
                content=content,
                branch=branch
            )
            return {"status": "created", "commit": result['commit'].sha}
    
    def create_pull_request(self, title: str, body: str, 
                           head_branch: str, base_branch: str = None) -> PullRequest:
        if base_branch is None:
            base_branch = settings.default_base_branch
        
        return self.repo.create_pull(
            title=title,
            body=body,
            head=head_branch,
            base=base_branch
        )
    
    def get_pull_request(self, pr_number: int) -> PullRequest:
        return self.repo.get_pull(number=pr_number)
    
    def get_changed_files(self, pr_number: int) -> List[str]:
        pr = self.get_pull_request(pr_number)
        files = pr.get_files()
        return [file.filename for file in files]
    
    def add_pr_comment(self, pr_number: int, comment: str) -> None:
        pr = self.get_pull_request(pr_number)
        pr.create_issue_comment(comment)
    
    def get_ci_status(self, pr_number: int) -> Dict[str, Any]:
        pr = self.get_pull_request(pr_number)
        commits = list(pr.get_commits())
        
        if not commits:
            return {"success": False, "jobs": [], "details": "No commits found"}
        
        latest_commit = commits[-1]
        statuses = list(latest_commit.get_statuses())
        
        results = {
            "success": True,
            "jobs": [],
            "details": ""
        }
        
        for status in statuses:
            job_info = {
                "context": status.context,
                "state": status.state,
                "description": status.description,
                "target_url": status.target_url
            }
            results["jobs"].append(job_info)
            
            if status.state != "success":
                results["success"] = False
                results["details"] += f"{status.context}: {status.state}\n"
        
        return results
    
    def merge_pull_request(self, pr_number: int, merge_method: str = "squash") -> bool:
        try:
            pr = self.get_pull_request(pr_number)
            pr.merge(merge_method=merge_method)
            return True
        except Exception as e:
            logger.error(f"Failed to merge PR #{pr_number}: {e}")
            return False
    
    def get_repository_tree(self, recursive: bool = True):
        return self.repo.get_git_tree('HEAD', recursive=recursive).tree
    
    def get_directory_contents(self, path: str = ""):
        return self.repo.get_contents(path)
    
    def get_pr_diff(self, pr_number: int) -> str:
        """Get diff for a Pull Request using GitHub API."""
        logger.debug(f"Getting diff for PR #{pr_number}")
        try:
            owner, repo = self.repo_name.split('/')
            url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"

            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3.diff"
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            diff_content = response.text
            logger.debug(f"Retrieved diff for PR #{pr_number} ({len(diff_content)} chars)")
            return diff_content
            
        except requests.RequestException as e:
            logger.error(f"Failed to get diff for PR #{pr_number}: {e}")
            return self._get_diff_from_files(pr_number)
        except Exception as e:
            logger.error(f"Unexpected error getting diff for PR #{pr_number}: {e}")
            return ""
    
    def _get_diff_from_files(self, pr_number: int) -> str:
        """Fallback: construct diff from changed files."""
        try:
            pr = self.get_pull_request(pr_number)
            files = pr.get_files()
            
            diff_parts = []
            for file in files:
                diff_parts.append(f"--- a/{file.filename}")
                diff_parts.append(f"+++ b/{file.filename}")
                if hasattr(file, 'patch') and file.patch:
                    diff_parts.append(f"{file.patch}")
                else:
                    diff_parts.append(f"@@ -0,0 +1,{file.additions} @@")
                    diff_parts.append("+[File content changed]")
                diff_parts.append("")
            
            return "\n".join(diff_parts)
        except Exception as e:
            logger.error(f"Failed to construct diff from files: {e}")
            return f"Failed to get diff for PR #{pr_number}"