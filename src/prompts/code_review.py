"""
Prompt templates for code review tasks.
"""

from typing import Dict, Any, List

class CodeReviewPrompts:
    """Prompt templates for code review and analysis."""
    @staticmethod
    def get_code_review_prompt(
        diff_content: str,
        issue_description: str,
        ci_results: Dict[str, Any],
        files_changed: List[str],
        pr_title: str = ""
    ) -> str:
        """
        Create prompt for comprehensive code review.
        
        Args:
            diff_content (str): Git diff of changes
            issue_description (str): Original issue description
            ci_results (Dict[str, Any]): Results from CI jobs
            files_changed (List[str]): List of changed files
            pr_title (str): PR title
            
        Returns:
            str: Formatted prompt
        """
        ci_status = "Pass" if ci_results.get('success', False) else "Fail"
        ci_details = ci_results.get('details', 'No CI details')
        total_jobs = ci_results.get('total_jobs', len(ci_results.get('jobs', [])))

        ci_jobs_text = ""
        if ci_results.get('jobs'):
            ci_jobs_text = "CI/CD Jobs:\n"
            for job in ci_results['jobs']:
                status_icon = "✅" if job.get('state') == 'success' else "❌"
                ci_jobs_text += f"- {status_icon} {job.get('context', 'Unknown')}: {job.get('state', 'unknown')}\n"
        
        return f"""Perform a comprehensive code review for the following Pull Request:
PR Title: {pr_title}
Original Issue: {issue_description}

Files Changed ({len(files_changed)}):
{', '.join(files_changed)}

CI/CD Status: {ci_status} ({total_jobs} jobs)
{ci_jobs_text}
CI/CD Details: {ci_details}

Code Changes (diff):
{diff_content}

Review Checklist:

Correctness: Does the code correctly implement the requirements from the issue?
Completeness: Are all requirements from the issue addressed?
Code Quality: Is the code clean, readable, and maintainable?
Performance: Are there any performance issues or optimizations needed?
Security: Are there any security vulnerabilities or concerns?
Testing: Are there sufficient tests? Do they adequately cover the changes?
Documentation: Is the code well-documented with docstrings and comments?
Standards: Does it follow project conventions, PEP 8, and best practices?
Error Handling: Is there proper error handling and edge case consideration?
Design: Is the design appropriate and scalable?
Provide specific, actionable feedback. Focus on:
Critical issues that must be fixed before merging
Important improvements that should be considered
Minor suggestions for code polish
Return your review in JSON format:
{{
"summary": "Overall assessment of the changes",
"status": "approved|changes_requested|needs_work",
"issues_found": [
{{
"file": "file.py",
"line": 10,
"severity": "critical|high|medium|low",
"description": "Specific issue description",
"suggestion": "Specific suggested fix or improvement"
}}
],
"positive_feedback": ["Specific positive aspects of the code"],
"suggestions": ["General suggestions for improvement"],
"overall_score": 85,
"meets_requirements": true|false
}}

Important:
"status" should be "approved" only if the code is ready to merge
"changes_requested" if significant improvements are needed
"needs_work" if major issues are found
"overall_score" should be 0-100 based on code quality
"meets_requirements" should reflect whether the issue requirements are fully met"""

    @staticmethod
    def get_ci_analysis_prompt(ci_results: Dict[str, Any]) -> str:
        """
        Create prompt for analyzing CI/CD results.
            Args:
            ci_results (Dict[str, Any]): CI/CD job results
            
        Returns:
            str: Formatted prompt
        """
        ci_jobs = ci_results.get('jobs', [])
        success_count = sum(1 for job in ci_jobs if job.get('state') == 'success')
        total_jobs = len(ci_jobs)
        
        jobs_text = "\n".join([
            f"- {job.get('context', 'Unknown')}: {job.get('state', 'unknown')} - {job.get('description', 'No description')}"
            for job in ci_jobs
        ])
        
        return f"""Analyze the following CI/CD pipeline results:
CI/CD Jobs ({success_count}/{total_jobs} passed):
{jobs_text}

Overall Status: {"PASS" if ci_results.get('success', False) else "FAIL"}
Details: {ci_results.get('details', 'No details')}

Please analyze:

What is the overall status of the CI/CD pipeline?
Which jobs failed and why (based on available information)?
What is the impact of failed jobs on code quality?
Are there any patterns in the failures?
What recommendations would you give to fix the issues?
Provide analysis in JSON format:
{{
"overall_status": "pass|fail|partial",
"failed_jobs": ["job1", "job2"],
"test_coverage": 0-100 (estimate based on context),
"issues_found": [
{{
"type": "test_failure|linting_error|type_error|build_error",
"description": "Specific issue description",
"impact": "high|medium|low",
"suggestion": "Specific steps to fix"
}}
],
"recommendations": ["Specific recommendation 1", "Specific recommendation 2"]
}}"""
    @staticmethod
    def get_pr_summary_prompt(
        issue_description: str,
        changes_made: str,
        review_results: Dict[str, Any]
    ) -> str:
        """
        Create prompt for generating PR summary.
        
        Args:
            issue_description (str): Original issue
            changes_made (str): Description of changes
            review_results (Dict[str, Any]): Review results
            
        Returns:
            str: Formatted prompt
        """
        return f"""Generate a comprehensive summary for the Pull Request:

Original Issue: {issue_description}
Changes Made: {changes_made}
Review Results:
Status: {review_results.get('status', 'unknown')}
Score: {review_results.get('overall_score', 0)}/100
Meets Requirements: {review_results.get('meets_requirements', False)}
Summary: {review_results.get('summary', 'No review available')}

Generate a professional PR summary including:
What was implemented (brief overview)
Key changes made (bullet points)
Testing performed and results
Review feedback addressed
Any remaining considerations or future work
Recommendations for deployment
Format the summary in markdown with appropriate sections."""