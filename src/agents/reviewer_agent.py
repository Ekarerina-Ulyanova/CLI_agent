"""
Reviewer Agent implementation for automated code review.
"""

import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.utils.logger import get_logger
from src.github.client import GitHubClient
from src.llm.openrouter_client import OpenRouterClient
from src.prompts.code_review import CodeReviewPrompts

logger = get_logger(__name__)


class ReviewerAgent:
    """AI Reviewer Agent for automated code review and analysis."""
    
    def __init__(self, github_client: GitHubClient):
        self.github = github_client
        self.llm = OpenRouterClient(temperature=0.2)
        self.prompts = CodeReviewPrompts()
        logger.info(f"ReviewerAgent initialized for repository: {github_client.repo_name}")
    
    def review_pull_request(self, pr_number: int) -> Dict[str, Any]:
        """Review a Pull Request and provide feedback."""
        logger.info(f"Starting review of PR #{pr_number}")
        
        try:
            # Get PR information
            pr = self.github.get_pull_request(pr_number)
            issue_number = self._extract_issue_number(pr.body)
            
            # Get CI/CD status
            ci_status = self.github.get_ci_status(pr_number)
            
            # Get diff using GitHub API
            diff_content = self.github.get_pr_diff(pr_number)
            files_changed = self._get_changed_files(pr)
            
            # Prepare review data
            review_data = {
                "diff_content": diff_content[:15000] + "\n...[truncated]" if len(diff_content) > 15000 else diff_content or "No diff available",
                "issue_description": pr.body or "No description",
                "ci_results": ci_status,
                "files_changed": files_changed,
                "pr_number": pr_number,
                "issue_number": issue_number,
                "pr_title": pr.title
            }
            
            # Perform review using LLM
            review_results = self._perform_llm_review(review_data)
            
            # Post review results
            self._post_review_feedback(pr_number, review_results)
            
            # Determine next steps
            next_action = self._determine_next_action(review_results, ci_status)
            
            # Take action if needed
            if next_action == "merge" and review_results.get("meets_requirements", False):
                if self.github.merge_pull_request(pr_number):
                    logger.info(f"Merged PR #{pr_number}")
            
            return {
                "review": review_results,
                "next_action": next_action,
                "pr_number": pr_number
            }
            
        except Exception as e:
            logger.error(f"Failed to review PR #{pr_number}: {e}", exc_info=True)
            self.github.add_pr_comment(pr_number, f"❌ **Review Error**: {str(e)[:500]}")
            raise
    
    def _extract_issue_number(self, pr_body: str) -> Optional[int]:
        """Extract issue number from PR body."""
        if not pr_body:
            return None
        
        match = re.search(r'#(\d+)', pr_body)
        return int(match.group(1)) if match else None
    
    def _get_changed_files(self, pr) -> List[str]:
        """Get list of changed files in PR."""
        try:
            files = pr.get_files()
            return [file.filename for file in files]
        except Exception as e:
            logger.error(f"Failed to get changed files: {e}")
            return []
    
    def _perform_llm_review(self, review_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform code review using LLM."""
        prompt = self.prompts.get_code_review_prompt(
            diff_content=review_data["diff_content"],
            issue_description=review_data["issue_description"],
            ci_results=review_data["ci_results"],
            files_changed=review_data["files_changed"],
            pr_title=review_data.get("pr_title", "")
        )
        
        messages = [
            self.llm.create_system_message("You are an experienced code reviewer. Provide detailed, constructive feedback."),
            self.llm.create_human_message(prompt)
        ]
        
        try:
            response = self.llm.generate(messages, max_tokens=3000)

            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON from LLM response")

            return self._create_fallback_review(response)
            
        except Exception as e:
            logger.error(f"LLM review failed: {e}")
            return {
                "summary": "Review failed due to technical error.",
                "status": "needs_work",
                "issues_found": [],
                "positive_feedback": [],
                "suggestions": ["Please check the implementation manually."],
                "overall_score": 0,
                "meets_requirements": False
            }
    
    def _create_fallback_review(self, response: str) -> Dict[str, Any]:
        """Create fallback review from non-JSON response."""
        status = "needs_work"
        if "approved" in response.lower():
            status = "approved"
        elif "changes" in response.lower():
            status = "changes_requested"
        
        return {
            "summary": response[:500] + "..." if len(response) > 500 else response,
            "status": status,
            "issues_found": [],
            "positive_feedback": [],
            "suggestions": ["Could not parse detailed review. Please review manually."],
            "overall_score": 50,
            "meets_requirements": False
        }
    
    def _post_review_feedback(self, pr_number: int, review_results: Dict[str, Any]) -> None:
        """Post review feedback to Pull Request."""
        status = review_results.get("status", "unknown")
        score = review_results.get("overall_score", 0)

        comment = self._format_review_comment(review_results)

        pr = self.github.get_pull_request(pr_number)
        current_labels = {label.name for label in pr.labels}
        review_labels = {"approved", "changes-requested", "needs-work"}
        new_labels = current_labels - review_labels
        
        if status == "approved" and review_results.get("meets_requirements", False):
            new_labels.add("approved")
        elif status == "changes_requested":
            new_labels.add("changes-requested")
        else:
            new_labels.add("needs-work")
        
        pr.set_labels(*list(new_labels))

        self.github.add_pr_comment(pr_number, comment)
    
    def _format_review_comment(self, review_results: Dict[str, Any]) -> str:
        """Format review results as a GitHub comment."""
        status_emoji = {
            "approved": "✅",
            "changes_requested": "🔄",
            "needs_work": "⚠️"
        }
        
        status = review_results.get("status", "needs_work")
        emoji = status_emoji.get(status, "📝")
        
        comment = f"""## {emoji} AI Code Review

**Overall Status**: {status.replace('_', ' ').title()}
**Score**: {review_results.get('overall_score', 0)}/100
**Meets Requirements**: {'Yes' if review_results.get('meets_requirements') else 'No'}

### Summary
{review_results.get('summary', 'No summary provided.')}

### Positive Feedback
{self._format_list(review_results.get('positive_feedback', []))}

### Issues Found
{self._format_issues(review_results.get('issues_found', []))}

### Suggestions
{self._format_list(review_results.get('suggestions', []))}

---

*Review generated by AI Reviewer Agent on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"""
        
        return comment
    
    def _format_list(self, items: List[str]) -> str:
        """Format list items as markdown."""
        if not items:
            return "*None*"
        return "\n".join([f"* {item}" for item in items])
    
    def _format_issues(self, issues: List[Dict[str, Any]]) -> str:
        """Format issues as markdown table."""
        if not issues:
            return "*No issues found*"
        
        issues_to_show = issues[:10]
        hidden_count = len(issues) - len(issues_to_show)
        
        table = "| File | Line | Severity | Description |\n"
        table += "|------|------|----------|-------------|\n"
        
        for issue in issues_to_show:
            file = issue.get("file", "unknown")[:40]
            line = issue.get("line", "N/A")
            severity = issue.get("severity", "low")
            description = issue.get("description", "")[:80]
            
            table += f"| `{file}` | {line} | {severity} | {description} |\n"
        
        if hidden_count > 0:
            table += f"\n*... and {hidden_count} more issues*"
        
        return table
    
    def _determine_next_action(self, review_results: Dict[str, Any], 
                              ci_status: Dict[str, Any]) -> str:
        """Determine next action based on review and CI results."""
        meets_requirements = review_results.get("meets_requirements", False)
        review_status = review_results.get("status", "needs_work")
        ci_success = ci_status.get("success", False)
        
        if meets_requirements and review_status == "approved" and ci_success:
            return "merge"
        elif not ci_success:
            return "fix_ci"
        elif not meets_requirements or review_status != "approved":
            return "request_changes"
        else:
            return "wait"
    
    def analyze_ci_results(self, pr_number: int) -> Dict[str, Any]:
        """Analyze CI/CD results for a PR."""
        logger.info(f"Analyzing CI results for PR #{pr_number}")
        ci_status = self.github.get_ci_status(pr_number)
        
        prompt = self.prompts.get_ci_analysis_prompt(ci_status)
        
        messages = [
            self.llm.create_system_message("You are a DevOps engineer analyzing CI/CD pipeline results."),
            self.llm.create_human_message(prompt)
        ]
        
        try:
            response = self.llm.generate(messages)
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    logger.error("Failed to parse CI analysis JSON")
            
            return {
                "overall_status": "unknown",
                "failed_jobs": [],
                "test_coverage": 0,
                "issues_found": [],
                "recommendations": ["Unable to parse CI results. Manual review required."]
            }
                
        except Exception as e:
            logger.error(f"CI analysis failed: {e}")
            return {
                "overall_status": "error",
                "failed_jobs": [],
                "test_coverage": 0,
                "issues_found": [{"type": "analysis_error", "description": str(e)}],
                "recommendations": ["Manual review required"]
            }