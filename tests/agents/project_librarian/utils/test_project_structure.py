"""Unit tests for ProjectStructure."""

from __future__ import annotations

from pathlib import Path

from code_monkey.agents.project_librarian.utils.project_structure import ProjectStructure


class TestBuildRootLabel:
    def test_root_folder_name_is_first_line(self, tmp_path: Path) -> None:
        result = ProjectStructure(tmp_path).build()
        assert result.split("\n")[0] == f"{tmp_path.name}/"


class TestSingleFile:
    def test_single_file_appears_in_output(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("# main", encoding="utf-8")

        result = ProjectStructure(tmp_path).build()

        assert "main.py" in result

    def test_tree_connector_used_for_single_entry(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("# main", encoding="utf-8")

        result = ProjectStructure(tmp_path).build()

        # Single entry is the last, so uses └──
        assert "└── main.py" in result


class TestNestedDirectory:
    def test_subdirectory_shown_with_trailing_slash(self, tmp_path: Path) -> None:
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "mod.py").write_text("", encoding="utf-8")

        result = ProjectStructure(tmp_path).build()

        assert "pkg/" in result

    def test_nested_file_appears_indented(self, tmp_path: Path) -> None:
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "mod.py").write_text("", encoding="utf-8")

        result = ProjectStructure(tmp_path).build()

        # mod.py must appear after pkg/ with indentation
        lines = result.split("\n")
        pkg_idx = next(i for i, line in enumerate(lines) if "pkg/" in line)
        mod_idx = next(i for i, line in enumerate(lines) if "mod.py" in line)
        assert mod_idx > pkg_idx

    def test_multiple_files_branch_and_last_connectors(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("", encoding="utf-8")
        (tmp_path / "b.py").write_text("", encoding="utf-8")

        result = ProjectStructure(tmp_path).build()

        # First file uses ├──, last file uses └──
        assert "├── a.py" in result
        assert "└── b.py" in result


class TestPythonIgnoreList:
    def test_pycache_excluded(self, tmp_path: Path) -> None:
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "mod.cpython-312.pyc").write_text("", encoding="utf-8")

        result = ProjectStructure(tmp_path).build()

        assert "__pycache__" not in result

    def test_venv_excluded(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "python").write_text("", encoding="utf-8")

        result = ProjectStructure(tmp_path).build()

        assert ".venv" not in result

    def test_codemonkey_cache_excluded(self, tmp_path: Path) -> None:
        cache = tmp_path / ".codemonkey"
        cache.mkdir()
        (cache / "file_hashes.json").write_text("{}", encoding="utf-8")

        result = ProjectStructure(tmp_path).build()

        assert ".codemonkey" not in result

    def test_git_dir_excluded(self, tmp_path: Path) -> None:
        git = tmp_path / ".git"
        git.mkdir()
        (git / "HEAD").write_text("ref: refs/heads/main", encoding="utf-8")

        result = ProjectStructure(tmp_path).build()

        assert ".git" not in result


class TestGitignore:
    def test_gitignored_directory_excluded(self, tmp_path: Path) -> None:
        secret_dir = tmp_path / "secrets"
        secret_dir.mkdir()
        (secret_dir / "key.txt").write_text("key", encoding="utf-8")
        (tmp_path / ".gitignore").write_text("secrets/\n", encoding="utf-8")

        result = ProjectStructure(tmp_path).build()

        assert "secrets" not in result

    def test_gitignored_file_pattern_excluded(self, tmp_path: Path) -> None:
        (tmp_path / "local.cfg").write_text("secret=1", encoding="utf-8")
        (tmp_path / "app.py").write_text("# app", encoding="utf-8")
        (tmp_path / ".gitignore").write_text("*.cfg\n", encoding="utf-8")

        result = ProjectStructure(tmp_path).build()

        assert "local.cfg" not in result
        assert "app.py" in result

    def test_gitignore_comments_and_blank_lines_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "keep.py").write_text("", encoding="utf-8")
        (tmp_path / ".gitignore").write_text(
            "# this is a comment\n\nkeep.py\n", encoding="utf-8"
        )

        # "keep.py" IS ignored per .gitignore — confirm it is excluded
        result = ProjectStructure(tmp_path).build()

        assert "keep.py" not in result

    def test_no_gitignore_does_not_raise(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("", encoding="utf-8")

        result = ProjectStructure(tmp_path).build()

        assert "main.py" in result


class TestSortingOrder:
    def test_directories_listed_before_files(self, tmp_path: Path) -> None:
        (tmp_path / "z_file.py").write_text("", encoding="utf-8")
        pkg = tmp_path / "a_pkg"
        pkg.mkdir()
        (pkg / "mod.py").write_text("", encoding="utf-8")

        result = ProjectStructure(tmp_path).build()

        lines = result.split("\n")
        dir_idx = next(i for i, line in enumerate(lines) if "a_pkg/" in line)
        file_idx = next(i for i, line in enumerate(lines) if "z_file.py" in line)
        assert dir_idx < file_idx


class TestEmptyDirectory:
    def test_empty_root_produces_only_root_label(self, tmp_path: Path) -> None:
        result = ProjectStructure(tmp_path).build()

        assert result == f"{tmp_path.name}/"
