from types import SimpleNamespace

from src.helpers.issue_processor import IssueProcessor
from src.utils.config import Settings


def _labels(*names: str):
    return [SimpleNamespace(name=name) for name in names]


def test_pending_issues_require_opt_in_and_exclude_pull_requests() -> None:
    eligible = SimpleNamespace(number=1, labels=_labels("agent:implement"), pull_request=None)
    unlabelled = SimpleNamespace(number=2, labels=_labels(), pull_request=None)
    pull_request = SimpleNamespace(
        number=3, labels=_labels("agent:implement"), pull_request={"url": "x"}
    )
    processor = object.__new__(IssueProcessor)
    processor.settings = Settings()
    processor.github = SimpleNamespace(get_open_issues=lambda: [eligible, unlabelled, pull_request])

    # GitHubClient filters PRs; retaining this assertion makes the policy explicit
    # for alternate client implementations as well.
    assert processor._get_new_issues() == [eligible]
