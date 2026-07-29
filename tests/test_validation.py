from src.utils.validation import validate_code_quality, validate_file_path


def test_file_path_allows_regular_source_file() -> None:
    assert validate_file_path("src/service.py")


def test_file_path_rejects_traversal_automation_and_globs() -> None:
    for path in ("../secret.py", ".github/workflows/ci.yml", "*.py", ".env", "C:/tmp/x.py"):
        assert not validate_file_path(path)


def test_code_validation_rejects_syntax_and_dangerous_calls() -> None:
    assert not validate_code_quality("def broken(:\n", "x.py")["valid"]
    assert not validate_code_quality("eval('1 + 1')", "x.py")["valid"]
