"""
Prompt templates for code generation tasks.
"""

from typing import Dict, Any, List


class CodeGenerationPrompts:
    """Prompt templates for code generation and modification."""
    
    @staticmethod
    def get_issue_analysis_prompt(issue_data: Dict[str, Any], repo_context: Dict[str, Any] = None) -> str:
        """
        Create prompt for issue analysis.
        
        Args:
            issue_data (Dict[str, Any]): Issue data including title and body
            repo_context (Dict[str, Any]): Repository context information
            
        Returns:
            str: Formatted prompt
        """
        repo_info = ""
        if repo_context:
            repo_info = f"""
Repository Context:
- Name: {repo_context.get('name', 'Unknown')}
- Default Branch: {repo_context.get('default_branch', 'main')}
- Top Directories: {', '.join(repo_context.get('structure', {}).get('directories', []))}
- Top Files: {', '.join(repo_context.get('structure', {}).get('files', []))}
- File Types: {', '.join([f'{k}:{v}' for k, v in repo_context.get('file_types', {}).items()])}
"""
        
        return f"""Analyze the following GitHub issue and determine what code changes are needed:

Repository Information:
{repo_info}

Issue Information:
- Title: {issue_data.get('title', 'No title')}
- Number: #{issue_data.get('number', 'N/A')}
- Author: {issue_data.get('author', 'Unknown')}
- Labels: {', '.join(issue_data.get('labels', []))}

Issue Description:
{issue_data.get('body', 'No description')}

Please provide a comprehensive analysis including:
1. What is the main requirement or feature being requested?
2. What files need to be modified or created? Be specific about file paths.
   - If the issue applies to all files of a certain type (e.g., all Python files), use pattern: "*.py"
   - Consider the repository structure when suggesting file paths
3. What is the expected behavior after implementation?
4. Are there any edge cases to consider?
5. What is the complexity level (low/medium/high)?

Also provide an implementation plan:
1. Step-by-step approach to implement the changes
2. Estimated lines of code to be added/modified
3. Testing strategy

Provide your analysis in JSON format with the following structure:
{{
    "analysis": {{
        "requirement_summary": "string",
        "files_to_modify": ["file1.py", "file2.py", "*.py" (for patterns)],
        "expected_behavior": "string",
        "edge_cases": ["case1", "case2"],
        "complexity": "low|medium|high"
    }},
    "implementation_plan": {{
        "steps": ["step1", "step2"],
        "estimated_lines_of_code": 100,
        "testing_strategy": "string"
    }}
}}

IMPORTANT: Be specific about file paths. Consider the repository structure shown above."""
    
    @staticmethod
    def get_code_modification_prompt(
        file_content: str,
        issue_analysis: Dict[str, Any],
        file_path: str,
        context: str = ""
    ) -> str:
        """
        Create prompt for modifying existing code.
        
        Args:
            file_content (str): Current file content
            issue_analysis (Dict[str, Any]): Analysis of the issue
            file_path (str): Path to the file being modified
            context (str): Additional context about the file
            
        Returns:
            str: Formatted prompt
        """
        requirement = issue_analysis.get('requirement_summary', 'No requirements')
        expected_behavior = issue_analysis.get('expected_behavior', 'No expected behavior specified')
        edge_cases = issue_analysis.get('edge_cases', [])
        
        edge_cases_text = "\n".join([f"- {case}" for case in edge_cases]) if edge_cases else "None specified"
        
        return f"""Modify the following code file to implement the requested feature:

File: {file_path}
Issue Requirements: {requirement}
Expected Behavior: {expected_behavior}
Edge Cases to Consider:
{edge_cases_text}

Additional Context:
{context}

Current file content:
```python
{file_content}
Instructions:

Implement ONLY the changes needed to fulfill the requirements
Maintain existing code style, patterns, and conventions
Add or update docstrings and comments where appropriate
Ensure code is efficient, readable, and follows best practices
Follow PEP 8 guidelines for Python code
Add type hints where appropriate
Preserve existing functionality unless explicitly required to change
If the file already has good structure, improve it incrementally
Return ONLY the complete modified file content. Do not include explanations, markdown formatting, or code fences.
"""

    @staticmethod
    def get_new_file_prompt(
        file_path: str,
        issue_analysis: Dict[str, Any],
        project_context: str = "",
        similar_files: List[str] = None
    ) -> str:
        """
        Create prompt for creating new files.
        
        Args:
            file_path (str): Path for the new file
            issue_analysis (Dict[str, Any]): Analysis of the issue
            project_context (str): Context about the project
            similar_files (List[str]): List of similar file paths for reference
            
        Returns:
            str: Formatted prompt
        """
        requirement = issue_analysis.get('requirement_summary', 'No requirements')
        expected_behavior = issue_analysis.get('expected_behavior', 'No expected behavior specified')
        
        similar_files_text = ""
        if similar_files:
            similar_files_text = f"\nSimilar files in project for reference: {', '.join(similar_files)}"
        
        return f"""Create a new code file with the following specifications:
        File Path: {file_path}
Issue Requirements: {requirement}
Expected Behavior: {expected_behavior}
Project Context: {project_context}{similar_files_text}

Instructions:

Create a complete, working implementation that fulfills the requirements
Include all necessary imports at the top of the file
Add comprehensive docstrings for modules, classes, and functions
Include type hints for all function parameters and return values
Follow PEP 8 guidelines and Python best practices
Consider error handling and edge cases
Make the code modular, reusable, and maintainable
If applicable, include example usage or basic test
Match the style and conventions of the existing project
Return ONLY the complete file content. Do not include explanations, markdown formatting, or code fences."""

    @staticmethod
    def get_test_generation_prompt(
        code_content: str,
        file_path: str,
        issue_analysis: Dict[str, Any]
    ) -> str:
        """
        Create prompt for generating tests.
        
        Args:
            code_content (str): Code to test
            file_path (str): Path to the file
            issue_analysis (Dict[str, Any]): Issue analysis
            
        Returns:
            str: Formatted prompt
        """
        requirement = issue_analysis.get('requirement_summary', 'No requirements')
        
        return f"""Generate comprehensive unit tests for the following code:
File: {file_path}
Code to test:
{code_content}
Issue Requirements: {requirement}

Instructions:
Write comprehensive unit tests using pytest
Test all public functions, classes, and methods
Include both positive and negative test cases
Test edge cases mentioned in requirements: {', '.join(issue_analysis.get('edge_cases', []))}
Use appropriate fixtures, parameterization, and mocking when needed
Follow AAA pattern (Arrange, Act, Assert)
Ensure good test coverage of the new functionality
Include descriptive test names that explain what is being tested
Add comments for complex test scenarios
Follow existing test patterns if present in the project
Return ONLY the complete test file content. Do not include explanations, markdown formatting, or additional code fences."""