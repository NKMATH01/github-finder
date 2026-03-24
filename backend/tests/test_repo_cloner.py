"""repo_cloner 단위 테스트 — URL 검증 + 보안."""

import sys
sys.path.insert(0, ".")

import pytest
from services.repo_cloner import validate_clone_url, GITHUB_URL_PATTERN
from models.error_models import AppException


def test_valid_github_url():
    url = "https://github.com/owner/repo"
    assert validate_clone_url(url) == url


def test_valid_github_url_with_git():
    url = "https://github.com/owner/repo.git"
    assert validate_clone_url(url) == url


def test_valid_github_url_with_dots():
    url = "https://github.com/my-org/my.repo-name"
    assert validate_clone_url(url) == url


def test_invalid_url_no_github():
    with pytest.raises(AppException) as exc_info:
        validate_clone_url("https://gitlab.com/owner/repo")
    assert exc_info.value.code == "CLONE_FAILED"


def test_invalid_url_injection():
    with pytest.raises(AppException):
        validate_clone_url("https://github.com/owner/repo; rm -rf /")


def test_invalid_url_empty():
    with pytest.raises(AppException):
        validate_clone_url("")


def test_invalid_url_no_repo():
    with pytest.raises(AppException):
        validate_clone_url("https://github.com/owner")


def test_invalid_url_path_traversal():
    with pytest.raises(AppException):
        validate_clone_url("https://github.com/../../etc/passwd")


def test_github_url_pattern_regex():
    """정규식 패턴이 올바른 URL만 매칭하는지 확인."""
    valid = [
        "https://github.com/user/repo",
        "https://github.com/org-name/repo_name.git",
        "https://github.com/a/b",
    ]
    invalid = [
        "http://github.com/user/repo",  # http
        "https://github.com/user/",     # trailing slash
        "https://github.com/user",      # no repo
        "https://github.com/user/repo/tree/main",  # extra path
        "ftp://github.com/user/repo",   # wrong protocol
    ]

    for url in valid:
        assert GITHUB_URL_PATTERN.match(url), f"Should match: {url}"

    for url in invalid:
        assert not GITHUB_URL_PATTERN.match(url), f"Should NOT match: {url}"
