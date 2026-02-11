"""Unit tests for gitignore utilities."""

from __future__ import annotations

from pathlib import Path

from code_monkey.agents.project_librarian.utils.gitignore import (
    is_gitignore_match,
    is_path_gitignored,
    load_gitignore_patterns,
)


class TestLoadGitignorePatterns:
    def test_returns_empty_list_when_no_gitignore(self, tmp_path: Path) -> None:
        result = load_gitignore_patterns(tmp_path)

        assert result == []

    def test_loads_patterns_from_gitignore(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("*.cfg\nsecrets/\n", encoding="utf-8")

        result = load_gitignore_patterns(tmp_path)

        assert result == ["*.cfg", "secrets/"]

    def test_skips_blank_lines(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("*.log\n\n*.tmp\n", encoding="utf-8")

        result = load_gitignore_patterns(tmp_path)

        assert result == ["*.log", "*.tmp"]

    def test_skips_comment_lines(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("# ignore logs\n*.log\n", encoding="utf-8")

        result = load_gitignore_patterns(tmp_path)

        assert result == ["*.log"]

    def test_skips_negation_lines(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("*.log\n!important.log\n", encoding="utf-8")

        result = load_gitignore_patterns(tmp_path)

        assert result == ["*.log"]


class TestIsGitignoreMatch:
    def test_matches_by_name_glob(self) -> None:
        assert is_gitignore_match("secret.cfg", "config/secret.cfg", ["*.cfg"]) is True

    def test_matches_by_relative_path(self) -> None:
        assert is_gitignore_match("key.txt", "secrets/key.txt", ["secrets/key.txt"]) is True

    def test_matches_directory_pattern_without_trailing_slash(self) -> None:
        assert is_gitignore_match("secrets", "secrets", ["secrets/"]) is True

    def test_no_match_returns_false(self) -> None:
        assert is_gitignore_match("app.py", "app.py", ["*.cfg"]) is False

    def test_empty_patterns_returns_false(self) -> None:
        assert is_gitignore_match("anything", "anything", []) is False

    def test_matches_doublestar_pattern(self) -> None:
        assert is_gitignore_match("generated.js", "src/generated.js", ["**/generated.js"]) is True


class TestIsPathGitignored:
    def test_file_directly_matched_by_pattern(self) -> None:
        assert is_path_gitignored(Path("local.cfg"), ["*.cfg"]) is True

    def test_file_inside_ignored_directory(self) -> None:
        assert is_path_gitignored(Path("secrets/key.txt"), ["secrets/"]) is True

    def test_deeply_nested_file_inside_ignored_directory(self) -> None:
        assert is_path_gitignored(Path("vendor/lib/deep/module.py"), ["vendor/"]) is True

    def test_non_ignored_file_returns_false(self) -> None:
        assert is_path_gitignored(Path("src/main.py"), ["*.cfg", "secrets/"]) is False

    def test_empty_patterns_returns_false(self) -> None:
        assert is_path_gitignored(Path("anything/file.py"), []) is False
