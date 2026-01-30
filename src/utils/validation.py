"""
Validation utilities for code quality and safety.
"""

import ast
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger(__name__)


def validate_code_quality(code: str, file_path: str) -> Dict[str, Any]:
    """
    Validate code quality and safety.
    
    Args:
        code (str): Code to validate
        file_path (str): Path to file for context
        
    Returns:
        Dict[str, Any]: Validation results
    """
    results = {
        "valid": True,
        "issues": [],
        "warnings": [],
        "suggestions": []
    }
    
    try:
        ast.parse(code)
    except SyntaxError as e:
        results["valid"] = False
        results["issues"].append({
            "type": "syntax_error",
            "line": e.lineno,
            "message": str(e)
        })
        return results

    security_issues = _check_security(code, file_path)
    results["issues"].extend(security_issues)

    style_suggestions = _check_code_style(code, file_path)
    results["suggestions"].extend(style_suggestions)

    performance_warnings = _check_performance(code)
    results["warnings"].extend(performance_warnings)
    
    if results["issues"]:
        results["valid"] = False
    
    return results


def _check_security(code: str, file_path: str) -> List[Dict[str, Any]]:
    """
    Check code for security issues.
    
    Args:
        code (str): Code to check
        file_path (str): File path for context
        
    Returns:
        List[Dict[str, Any]]: Security issues found
    """
    issues = []

    dangerous_patterns = [
        (r'eval\s*\(', 'eval', 'Use of eval() is dangerous'),
        (r'exec\s*\(', 'exec', 'Use of exec() is dangerous'),
        (r'__import__\s*\(', '__import__', 'Dynamic imports can be unsafe'),
        (r'pickle\.loads', 'pickle', 'Pickle can execute arbitrary code'),
        (r'subprocess\.Popen.*shell=True', 'shell injection', 'Shell injection risk'),
        (r'os\.system', 'os.system', 'Use subprocess instead of os.system'),
    ]
    
    for pattern, issue_type, message in dangerous_patterns:
        matches = re.finditer(pattern, code)
        for match in matches:
            line_num = code[:match.start()].count('\n') + 1
            issues.append({
                "type": "security",
                "subtype": issue_type,
                "line": line_num,
                "message": message,
                "severity": "high"
            })

    secret_patterns = [
        (r'password\s*=\s*["\'].+["\']', 'hardcoded password'),
        (r'api[_-]?key\s*=\s*["\'].+["\']', 'hardcoded API key'),
        (r'token\s*=\s*["\'].+["\']', 'hardcoded token'),
        (r'secret\s*=\s*["\'].+["\']', 'hardcoded secret'),
    ]
    
    for pattern, issue_type in secret_patterns:
        matches = re.finditer(pattern, code, re.IGNORECASE)
        for match in matches:
            line_num = code[:match.start()].count('\n') + 1
            issues.append({
                "type": "security",
                "subtype": issue_type,
                "line": line_num,
                "message": f"Potential hardcoded {issue_type}",
                "severity": "high"
            })
    
    return issues


def _check_code_style(code: str, file_path: str) -> List[Dict[str, Any]]:
    """
    Check code style and conventions.
    
    Args:
        code (str): Code to check
        file_path (str): File path for context
        
    Returns:
        List[Dict[str, Any]]: Style suggestions
    """
    suggestions = []

    lines = code.split('\n')
    for i, line in enumerate(lines, 1):
        if len(line) > 100:
            suggestions.append({
                "type": "style",
                "line": i,
                "message": f"Line too long ({len(line)} characters)",
                "suggestion": "Break into multiple lines"
            })

    function_defs = re.finditer(r'def\s+(\w+)\s*\(([^)]*)\)\s*(->\s*[^:]+)?:', code)
    for match in function_defs:
        line_num = code[:match.start()].count('\n') + 1
        return_hint = match.group(3)
        
        if not return_hint:
            suggestions.append({
                "type": "style",
                "line": line_num,
                "message": f"Function '{match.group(1)}' missing return type hint",
                "suggestion": "Add return type annotation"
            })
    
    return suggestions


def _check_performance(code: str) -> List[Dict[str, Any]]:
    """
    Check code for performance issues.
    
    Args:
        code (str): Code to check
        
    Returns:
        List[Dict[str, Any]]: Performance warnings
    """
    warnings = []

    loop_depth = 0
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        
        if stripped.startswith(('for ', 'while ', 'async for ')):
            loop_depth += 1
            if loop_depth > 2:
                warnings.append({
                    "type": "performance",
                    "line": i,
                    "message": f"Deeply nested loop (depth: {loop_depth})",
                    "suggestion": "Consider refactoring or using vectorized operations"
                })
        elif stripped.startswith(('if ', 'elif ', 'else:', 'try:', 'except ')):

            pass
        elif stripped and not stripped.startswith(('#', '"', "'")):

            loop_depth = 0

    for i, line in enumerate(lines, 1):
        if 'for' in line or 'while' in line:

            if 'len(' in line and 'range' in line:
                warnings.append({
                    "type": "performance",
                    "line": i,
                    "message": "Calling len() in loop condition",
                    "suggestion": "Calculate length once before loop"
                })
    
    return warnings


def validate_file_path(file_path: str) -> bool:
    """
    Validate file path for safety.
    
    Args:
        file_path (str): File path to validate
        
    Returns:
        bool: True if path is safe
    """
    if '..' in file_path:
        return False

    if file_path.startswith('/'):
        return False

    if any(char in file_path for char in ['~', '$', '`']):
        return False

    valid_extensions = {'.py', '.md', '.txt', '.yml', '.yaml', '.json', '.ini', '.cfg'}
    file_ext = Path(file_path).suffix.lower()
    
    if file_ext not in valid_extensions and file_ext:
        return False
    
    return True