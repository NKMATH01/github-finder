"""structure_analyzer 단위 테스트 — 파일 수집 + 트리 요약 로직."""

import sys
import os
import tempfile
sys.path.insert(0, ".")

from services.structure_analyzer import _summarize_tree, _collect_file_contents, PRIORITY_FILES


def test_priority_files_list():
    """우선 분석 파일 목록이 올바른지 확인."""
    assert "README.md" in PRIORITY_FILES
    assert "package.json" in PRIORITY_FILES
    assert "requirements.txt" in PRIORITY_FILES
    assert "Dockerfile" in PRIORITY_FILES


def test_summarize_tree_basic():
    """임시 디렉토리로 트리 요약 테스트."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 파일 생성
        open(os.path.join(tmpdir, "main.py"), "w").close()
        open(os.path.join(tmpdir, "README.md"), "w").close()
        os.makedirs(os.path.join(tmpdir, "src"))
        open(os.path.join(tmpdir, "src", "app.py"), "w").close()

        summary = _summarize_tree(tmpdir)
        assert "main.py" in summary
        assert "README.md" in summary
        assert "src" in summary


def test_summarize_tree_excludes_git():
    """_summarize_tree가 .git 디렉토리를 제외하는지 확인."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, ".git", "objects"))
        open(os.path.join(tmpdir, "app.py"), "w").close()

        summary = _summarize_tree(tmpdir)
        assert ".git" not in summary
        assert "app.py" in summary


def test_summarize_tree_excludes_node_modules():
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "node_modules", "pkg"))
        open(os.path.join(tmpdir, "index.js"), "w").close()

        summary = _summarize_tree(tmpdir)
        assert "node_modules" not in summary
        assert "index.js" in summary


def test_collect_file_contents_priority():
    """우선 파일이 존재하면 수집하는지 확인."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "requirements.txt"), "w") as f:
            f.write("flask==2.0\nrequests==2.28\n")
        with open(os.path.join(tmpdir, "README.md"), "w") as f:
            f.write("# Test Project\nDescription here.")

        contents = _collect_file_contents(tmpdir)
        assert "requirements.txt" in contents
        assert "flask" in contents["requirements.txt"]


def test_collect_file_contents_with_key_files():
    """key_files가 있으면 해당 파일도 수집하는지 확인."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "src"))
        with open(os.path.join(tmpdir, "src", "core.py"), "w") as f:
            f.write("def main(): pass\n")

        key_files = [{"path": "src/core.py", "importance": "core"}]
        contents = _collect_file_contents(tmpdir, key_files)
        assert "src/core.py" in contents


def test_summarize_tree_max_entries():
    """max_entries 제한이 동작하는지 확인."""
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(100):
            open(os.path.join(tmpdir, f"file_{i}.txt"), "w").close()

        summary = _summarize_tree(tmpdir, max_entries=10)
        assert "truncated" in summary
