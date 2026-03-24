"""github_searcher 단위 테스트 — 데이터 모델 + 필터링 로직."""

import sys
sys.path.insert(0, ".")

from services.github_searcher import RepoBasicInfo, RepoDetailedInfo


def test_repo_basic_info_creation():
    repo = RepoBasicInfo(
        owner="google",
        name="mediapipe",
        full_name="google/mediapipe",
        url="https://github.com/google/mediapipe",
        description="Cross-platform ML solutions",
        stars=27000,
        forks=5000,
        language="Python",
        updated_at="2024-11-15T00:00:00Z",
        open_issues=500,
        has_wiki=True,
        license_name="Apache-2.0",
        size_kb=180000,
        topics=["machine-learning", "computer-vision"],
    )
    assert repo.full_name == "google/mediapipe"
    assert repo.stars == 27000
    assert len(repo.topics) == 2


def test_repo_detailed_info_extends_basic():
    basic = RepoBasicInfo(
        owner="test", name="repo", full_name="test/repo",
        url="https://github.com/test/repo", description="",
        stars=100, forks=10, language="Python",
        updated_at="2024-01-01", open_issues=5,
        has_wiki=False, license_name=None, size_kb=1000,
    )
    detailed = RepoDetailedInfo(**vars(basic))
    assert detailed.readme_content == ""
    assert detailed.file_tree == []
    assert detailed.dependency_files == {}
    assert detailed.recent_issues == []


def test_repo_detailed_info_with_data():
    detailed = RepoDetailedInfo(
        owner="test", name="repo", full_name="test/repo",
        url="https://github.com/test/repo", description="desc",
        stars=500, forks=50, language="JavaScript",
        updated_at="2024-06-01", open_issues=10,
        has_wiki=True, license_name="MIT", size_kb=5000,
        readme_content="# Test Repo\nSome content",
        file_tree=["src/index.js", "package.json"],
        dependency_files={"package.json": '{"name": "test"}'},
        recent_issues=[{"title": "Bug", "state": "open", "labels": ["bug"]}],
        closed_issues_count=8,
        total_issues_count=10,
    )
    assert len(detailed.file_tree) == 2
    assert "package.json" in detailed.dependency_files
    assert detailed.closed_issues_count == 8
    assert detailed.total_issues_count == 10


def test_repo_sorting_by_stars():
    repos = [
        RepoBasicInfo(owner="a", name="low", full_name="a/low", url="", description="",
                     stars=50, forks=0, language="", updated_at="", open_issues=0,
                     has_wiki=False, license_name=None, size_kb=0),
        RepoBasicInfo(owner="b", name="high", full_name="b/high", url="", description="",
                     stars=5000, forks=0, language="", updated_at="", open_issues=0,
                     has_wiki=False, license_name=None, size_kb=0),
        RepoBasicInfo(owner="c", name="mid", full_name="c/mid", url="", description="",
                     stars=500, forks=0, language="", updated_at="", open_issues=0,
                     has_wiki=False, license_name=None, size_kb=0),
    ]
    sorted_repos = sorted(repos, key=lambda r: r.stars, reverse=True)
    assert sorted_repos[0].full_name == "b/high"
    assert sorted_repos[1].full_name == "c/mid"
    assert sorted_repos[2].full_name == "a/low"


def test_readme_truncation_logic():
    """README가 4000자 초과 시 잘라내는 로직 확인."""
    long_readme = "x" * 5000
    if len(long_readme) > 4000:
        truncated = long_readme[:3000] + "\n...(중략)...\n" + long_readme[-1000:]
    else:
        truncated = long_readme
    assert len(truncated) < len(long_readme)
    assert "중략" in truncated
