"""
Code Agent implementation for automated code generation and modification.
"""

import json
import os
import re
import subprocess
import tempfile
import urllib.parse
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.utils.config import settings
from src.utils.logger import get_logger
from src.github.client import GitHubClient
from src.llm.openrouter_client import OpenRouterClient
from src.prompts.code_generation import CodeGenerationPrompts
from src.utils.validation import validate_file_path

logger = get_logger(__name__)


class CodeAgent:
    """Code Agent for implementing changes based on GitHub issues."""
    
    def __init__(self, github_client: GitHubClient):
        self.github = github_client
        self.llm = OpenRouterClient(temperature=0.1)
        self.prompts = CodeGenerationPrompts()
        self.iteration_count = 0
        logger.info(f"CodeAgent initialized for repository: {github_client.repo_name}")
    
    def process_issue(self, issue_number: int) -> Optional[int]:
        """Process a GitHub issue and create implementation."""
        logger.info(f"Starting processing of issue #{issue_number}")
        
        try:
            # Step 1: Get and analyze issue
            issue = self.github.get_issue(issue_number)
            self.github.update_issue_status(issue_number, "in-progress", "Analyzing requirements...")
            
            analysis = self._analyze_issue(issue)
            logger.debug(f"Issue analysis: {json.dumps(analysis, indent=2)}")
            
            # Step 2: Create implementation plan
            plan = self._create_implementation_plan(issue_number, issue.title, analysis)
            branch_name = plan["branch_name"]
            
            # Step 3: Create branch
            self.github.create_branch(branch_name)
            self.github.update_issue_status(
                issue_number, "in-progress",
                f"Created branch `{branch_name}` and starting implementation..."
            )
            
            # Step 4: Implement changes
            changes_summary = self._implement_changes(plan, analysis)
            logger.info(f"Changes implemented: {changes_summary}")
            
            # Step 5: Run code quality checks
            quality_report = self._run_code_quality_checks(branch_name, plan.get("files_to_modify", []))
            
            # Step 6: Create Pull Request
            pr = self._create_pull_request(issue, branch_name, changes_summary, quality_report)
            
            # Step 7: Update issue status
            self.github.update_issue_status(
                issue_number, "needs-review",
                f"Pull Request #{pr.number} created and ready for review."
            )
            
            logger.info(f"Successfully processed issue #{issue_number}, created PR #{pr.number}")
            return pr.number
            
        except Exception as e:
            logger.error(f"Failed to process issue #{issue_number}: {e}", exc_info=True)
            self.github.update_issue_status(
                issue_number, "blocked",
                f"Error during processing: {str(e)}"
            )
            return None
    
    def _analyze_issue(self, issue) -> Dict[str, Any]:
        """Analyze issue requirements using LLM."""
        repo_context = self._get_repository_context()
        
        prompt = self.prompts.get_issue_analysis_prompt({
            "title": issue.title,
            "body": issue.body,
            "number": issue.number,
            "labels": [label.name for label in issue.labels]
        }, repo_context)
        
        messages = [
            self.llm.create_system_message("You are an experienced software developer analyzing GitHub issues."),
            self.llm.create_human_message(prompt)
        ]
        
        response = self.llm.generate(messages)
        
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                analysis = json.loads(json_match.group(0))

                requirement = analysis.get('analysis', {}).get('requirement_summary', '').lower()
                if not analysis.get('analysis', {}).get('files_to_modify'):
                    discovered_files = self._discover_relevant_files(requirement)
                    analysis['analysis']['files_to_modify'] = discovered_files
                
                return analysis
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON from LLM response")

        return {
            "analysis": {
                "requirement_summary": issue.title,
                "files_to_modify": [],
                "expected_behavior": issue.body[:200] if issue.body else "",
                "edge_cases": [],
                "complexity": "medium"
            }
        }
    
    def _get_repository_context(self) -> Dict[str, Any]:
        """Get repository context for issue analysis."""
        context = {
            "name": self.github.repo_name,
            "default_branch": settings.default_base_branch,
            "structure": {},
            "file_types": {}
        }
        
        try:
            contents = self.github.get_directory_contents("")
            dirs = []
            files = []
            
            for item in contents:
                if item.type == "dir":
                    dirs.append(item.name)
                else:
                    files.append(item.name)
                    ext = Path(item.name).suffix
                    context["file_types"][ext] = context["file_types"].get(ext, 0) + 1
            
            context["structure"]["directories"] = dirs[:10]
            context["structure"]["files"] = files[:10]
            
        except Exception as e:
            logger.warning(f"Failed to get repository context: {e}")
        
        return context
    
    def _discover_relevant_files(self, requirement: str) -> List[str]:
        """Discover relevant files in the repository based on requirement."""
        try:
            tree = self.github.get_repository_tree(recursive=True)
            if not tree:
                return []
            
            discovered_files = []
            patterns = self._determine_file_patterns(requirement)
            
            for item in tree:
                if any(self._pattern_matches(pattern, item.path) for pattern in patterns):

                    if not any(exclude in item.path for exclude in [
                        '__pycache__', 'node_modules/', 'venv/', '.venv/', 
                        'env/', 'dist/', 'build/', '.git'
                    ]):
                        discovered_files.append(item.path)
            
            return discovered_files[:50]
            
        except Exception as e:
            logger.error(f"Failed to discover files: {e}")
            return []
    
    def _determine_file_patterns(self, requirement: str) -> List[str]:
        """Determine file patterns from requirement text."""
        patterns = []
        
        if any(keyword in requirement for keyword in ['python', '.py', 'py file']):
            patterns.append('*.py')
        
        if any(keyword in requirement for keyword in ['documentation', 'readme', '.md', 'markdown']):
            patterns.append('*.md')
        
        if any(keyword in requirement for keyword in ['test', 'tests', 'testing']):
            patterns.append('*test*.py')
        
        if any(keyword in requirement for keyword in ['config', 'configuration', '.json', '.yaml', '.yml']):
            patterns.append('*.json')
            patterns.append('*.yaml')
            patterns.append('*.yml')
        
        if not patterns:
            patterns.append('*.py')
        
        return patterns
    
    def _pattern_matches(self, pattern: str, file_path: str) -> bool:
        """Check if file path matches pattern."""
        if pattern.startswith('*'):
            return file_path.endswith(pattern[1:]) or (pattern[1:-1] in file_path if '*' in pattern[1:-1] else False)
        return file_path == pattern
    
    def _create_implementation_plan(self, issue_number: int, issue_title: str, 
                                   analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create detailed implementation plan."""

        clean_title = re.sub(r'[^a-zA-Z0-9-]', '-', issue_title.lower())
        clean_title = re.sub(r'-+', '-', clean_title).strip('-')[:50]
        branch_name = f"{settings.branch_prefix}issue-{issue_number}-{clean_title}"[:100]
        
        return {
            "issue_number": issue_number,
            "branch_name": branch_name,
            "files_to_modify": analysis.get("analysis", {}).get("files_to_modify", []),
            "analysis": analysis
        }
    
    def _implement_changes(self, plan: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Implement code changes based on plan."""
        changes_made = []
        branch_name = plan["branch_name"]
        files_to_modify = plan.get("files_to_modify", [])
        
        logger.info(f"Implementing changes on branch '{branch_name}' for {len(files_to_modify)} files")
        
        for file_path in files_to_modify:
            try:
                if not validate_file_path(file_path):
                    logger.warning(f"Skipping invalid file path: {file_path}")
                    continue

                existing_content = self.github.get_file_content(file_path, ref=branch_name)
                
                if existing_content is not None:
                    new_content = self._modify_existing_file(file_path, existing_content, analysis)
                    action = "Modified"
                else:
                    new_content = self._create_new_file(file_path, analysis)
                    action = "Created"

                commit_message = f"Implement: {analysis.get('analysis', {}).get('requirement_summary', 'Requirements')}"
                result = self.github.create_or_update_file(
                    file_path=file_path,
                    content=new_content,
                    commit_message=commit_message,
                    branch=branch_name
                )
                
                changes_made.append(f"{action}: {file_path}")

                if self._should_generate_tests(file_path):
                    test_content = self._generate_tests(file_path, new_content, analysis)
                    if test_content:
                        test_file_path = self._get_test_file_path(file_path)
                        self.github.create_or_update_file(
                            file_path=test_file_path,
                            content=test_content,
                            commit_message=f"Add tests for {file_path}",
                            branch=branch_name
                        )
                        changes_made.append(f"Added tests: {test_file_path}")
                        
            except Exception as e:
                logger.error(f"Failed to process file {file_path}: {e}")
                continue
        
        return "\n".join(changes_made) if changes_made else "No changes were made"
    
    def _modify_existing_file(self, file_path: str, existing_content: str, 
                             analysis: Dict[str, Any]) -> str:
        """Modify existing file using LLM."""
        context = self._get_file_context(file_path)
        
        prompt = self.prompts.get_code_modification_prompt(
            existing_content, analysis, file_path, context
        )
        
        messages = [
            self.llm.create_system_message("You are an expert software developer modifying code to implement requirements."),
            self.llm.create_human_message(prompt)
        ]
        
        response = self.llm.generate(messages)
        return response.strip()
    
    def _get_file_context(self, file_path: str) -> str:
        """Get additional context about the file."""
        context_parts = []

        if file_path.endswith('.py'):
            try:
                content = self.github.get_file_content(file_path)
                if content:
                    imports = re.findall(r'^import\s+(\w+)', content, re.MULTILINE)
                    imports += re.findall(r'^from\s+(\w+)', content, re.MULTILINE)
                    if imports:
                        context_parts.append(f"Current imports: {', '.join(set(imports))}")
            except:
                pass
        
        return "\n".join(context_parts) if context_parts else ""
    
    def _create_new_file(self, file_path: str, analysis: Dict[str, Any]) -> str:
        """Create new file using LLM."""
        project_context = self._get_project_context()
        similar_files = self._get_similar_files(file_path)
        
        prompt = self.prompts.get_new_file_prompt(file_path, analysis, project_context, similar_files)
        
        messages = [
            self.llm.create_system_message("You are an expert software developer creating new code files."),
            self.llm.create_human_message(prompt)
        ]
        
        response = self.llm.generate(messages)
        return response.strip()
    
    def _get_project_context(self) -> str:
        """Get context about the project."""
        context_parts = []

        try:
            readme = self.github.get_file_content("README.md")
            if readme:
                context_parts.append(f"Project README:\n{readme[:1000]}")
        except:
            pass
        
        return "\n\n".join(context_parts) if context_parts else "No project context available"
    
    def _get_similar_files(self, file_path: str) -> List[str]:
        """Get similar files in the repository for context."""
        file_ext = Path(file_path).suffix
        
        try:
            tree = self.github.get_repository_tree(recursive=True)
            if not tree:
                return []
            
            similar_files = []
            for item in tree:
                if item.path.endswith(file_ext) and item.path != file_path:
                    similar_files.append(item.path)
                    if len(similar_files) >= 3:
                        break
            return similar_files
        except Exception as e:
            logger.error(f"Failed to get similar files: {e}")
            return []
    
    def _generate_tests(self, file_path: str, code_content: str, 
                       analysis: Dict[str, Any]) -> Optional[str]:
        """Generate tests for a file."""
        if not file_path.endswith('.py'):
            return None
        
        prompt = self.prompts.get_test_generation_prompt(code_content, file_path, analysis)
        
        messages = [
            self.llm.create_system_message("You are an expert in writing unit tests for Python code."),
            self.llm.create_human_message(prompt)
        ]
        
        try:
            response = self.llm.generate(messages)
            return response.strip()
        except Exception as e:
            logger.warning(f"Failed to generate tests for {file_path}: {e}")
            return None
    
    def _should_generate_tests(self, file_path: str) -> bool:
        """Determine if tests should be generated for a file."""
        return (file_path.endswith('.py') and 
                not file_path.startswith('test_') and 
                'test' not in file_path.lower())
    
    def _get_test_file_path(self, file_path: str) -> str:
        """Get test file path for a given file."""
        dir_name = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)
        test_name = f"test_{base_name}"

        try:
            contents = self.github.get_directory_contents("")
            for item in contents:
                if item.type == "dir" and "test" in item.name.lower():
                    return os.path.join(item.path, test_name if not dir_name else os.path.join(dir_name, test_name))
        except:
            pass

        return os.path.join("tests", test_name if not dir_name else os.path.join(dir_name, test_name))
    
    def _run_code_quality_checks(self, branch_name: str, changed_files: List[str]) -> Dict[str, Any]:
        """Run code quality checks on the branch."""
        logger.info(f"Running code quality checks on branch '{branch_name}'")
        
        if not settings.use_ruff and not settings.use_black and not settings.use_mypy:
            return {"status": "skipped", "details": "All checks disabled"}
        
        results = {
            "status": "completed",
            "ruff_passed": False,
            "black_passed": False,
            "mypy_passed": False,
            "details": ""
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                repo_url = self._get_repo_url_with_auth()

                clone_cmd = [
                    "git", "clone", 
                    "--depth", "1",
                    "--branch", branch_name,
                    repo_url, 
                    tmpdir
                ]
                
                logger.debug(f"Running clone command: {' '.join(clone_cmd)}")

                result = subprocess.run(
                    clone_cmd, 
                    capture_output=True, 
                    text=True,
                    timeout=300
                )
                
                if result.returncode != 0:
                    logger.error(f"Clone failed: {result.stderr}")
                    results["status"] = "failed"
                    results["details"] = f"Failed to clone repository: {result.stderr}"
                    return results
                
                logger.info(f"Successfully cloned branch {branch_name} to {tmpdir}")

                if settings.use_ruff and changed_files:
                    try:
                        python_files = [f for f in changed_files if f.endswith('.py')]
                        if python_files:
                            ruff_cmd = ["ruff", "check"] + python_files
                            ruff_result = subprocess.run(
                                ruff_cmd, 
                                cwd=tmpdir,
                                capture_output=True, 
                                text=True
                            )
                            results["ruff_passed"] = ruff_result.returncode == 0
                            if ruff_result.stderr:
                                results["details"] += f"Ruff errors:\n{ruff_result.stderr}\n"
                            if ruff_result.stdout:
                                results["details"] += f"Ruff warnings:\n{ruff_result.stdout}\n"
                    except Exception as e:
                        logger.error(f"Ruff check failed: {e}")
                        results["ruff_passed"] = False
                
                if settings.use_black and changed_files:
                    try:
                        python_files = [f for f in changed_files if f.endswith('.py')]
                        if python_files:
                            black_cmd = ["black", "--check", "--diff"] + python_files
                            black_result = subprocess.run(
                                black_cmd,
                                cwd=tmpdir,
                                capture_output=True,
                                text=True
                            )
                            results["black_passed"] = black_result.returncode == 0
                            if black_result.stderr:
                                results["details"] += f"Black errors:\n{black_result.stderr}\n"
                    except Exception as e:
                        logger.error(f"Black check failed: {e}")
                        results["black_passed"] = False
                
                if settings.use_mypy and changed_files:
                    try:
                        python_files = [f for f in changed_files if f.endswith('.py')]
                        if python_files:
                            mypy_cmd = ["mypy"] + python_files
                            mypy_result = subprocess.run(
                                mypy_cmd,
                                cwd=tmpdir,
                                capture_output=True,
                                text=True
                            )
                            results["mypy_passed"] = mypy_result.returncode == 0
                            if mypy_result.stderr:
                                results["details"] += f"MyPy errors:\n{mypy_result.stderr}\n"
                            if mypy_result.stdout:
                                results["details"] += f"MyPy type hints:\n{mypy_result.stdout}\n"
                    except Exception as e:
                        logger.error(f"MyPy check failed: {e}")
                        results["mypy_passed"] = False
                
            except subprocess.TimeoutExpired:
                logger.error("Git clone timed out after 5 minutes")
                results["status"] = "failed"
                results["details"] = "Clone operation timed out"
            except Exception as e:
                logger.error(f"Failed to run code quality checks: {e}")
                results["status"] = "failed"
                results["details"] = f"Error: {str(e)}"
        
        return results
    
    def _get_repo_url_with_auth(self) -> str:
        """Get repository URL with authentication token."""
        if not settings.github_token:
            return f"git@github.com:{self.github.repo_name}.git"
        encoded_token = urllib.parse.quote(settings.github_token, safe='')
        return f"https://{encoded_token}@github.com/{self.github.repo_name}.git"
    
    def _create_pull_request(self, issue, branch_name: str, changes_summary: str, 
                            quality_report: Dict[str, Any]) -> Any:
        """Create Pull Request for the changes."""
        pr_title = f"Implement: {issue.title}"

        formatted_changes = "\n".join([f"- {line}" for line in changes_summary.split("\n")])
        
        pr_body = f"""## Summary
Implements #{issue.number}

## Changes Made
{formatted_changes}

## Quality Checks
- Ruff: {'Passed' if quality_report.get('ruff_passed') else 'Failed'}
- Black: {'Passed' if quality_report.get('black_passed') else 'Failed'}
- MyPy: {'Passed' if quality_report.get('mypy_passed') else 'Failed'}

## Notes
This PR was automatically generated by the Coding Agent system.

---

**Issue**: #{issue.number}
**Branch**: {branch_name}
**Status**: Ready for review"""
        
        pr = self.github.create_pull_request(
            title=pr_title,
            body=pr_body,
            head_branch=branch_name
        )

        pr.add_to_labels("automated-pr", "agent-generated")
        
        return pr
    
    def handle_review_feedback(self, pr_number: int, feedback: str) -> bool:
        """Handle feedback from code review and make necessary changes."""
        self.iteration_count += 1
        
        if self.iteration_count > settings.max_iterations:
            logger.warning(f"Max iterations reached for PR #{pr_number}")
            self.github.add_pr_comment(
                pr_number,
                "Maximum iteration limit reached. Manual intervention required."
            )
            return False
        
        logger.info(f"Processing feedback for PR #{pr_number}, iteration {self.iteration_count}")

        self.github.add_pr_comment(
            pr_number,
            f"Received review feedback. Making adjustments (iteration {self.iteration_count}/{settings.max_iterations})..."
        )

        pr = self.github.get_pull_request(pr_number)
        changed_files = self.github.get_changed_files(pr_number)

        for file_path in changed_files:
            try:
                current_content = self.github.get_file_content(file_path, ref=pr.head.ref)
                if not current_content:
                    continue

                new_content = self._apply_feedback_to_file(file_path, current_content, feedback, pr.body)
                
                if new_content != current_content:
                    self.github.create_or_update_file(
                        file_path=file_path,
                        content=new_content,
                        commit_message=f"Apply review feedback for PR #{pr_number}",
                        branch=pr.head.ref
                    )
                    
            except Exception as e:
                logger.error(f"Failed to update file {file_path}: {e}")
                continue
        
        return True
    
    def _apply_feedback_to_file(self, file_path: str, current_content: str, 
                               feedback: str, pr_description: str) -> str:
        """Apply review feedback to a specific file."""
        prompt = f"""Apply the following review feedback to the code:

File: {file_path}

Review Feedback:
{feedback}

Original PR Description:
{pr_description}

Current Code:
```python
{current_content}
Instructions:

Apply the specific changes requested in the review feedback
Maintain existing functionality unless explicitly asked to change
Keep the same code style and conventions
Return the complete modified code

Modified Code:"""
        messages = [
        self.llm.create_system_message("You are a software developer applying code review feedback."),
        self.llm.create_human_message(prompt)
    ]
    
        response = self.llm.generate(messages)
        return response.strip()