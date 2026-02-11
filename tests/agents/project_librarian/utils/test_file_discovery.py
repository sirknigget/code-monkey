"""Tests for file discovery utilities."""

from pathlib import Path

from code_monkey.agents.project_librarian.utils.file_discovery import discover_python_files


class TestDiscoverPythonFiles:
    """Test suite for discover_python_files function."""

    def test_discovers_python_files_at_root_and_nested(
        self, tmp_path: Path
    ) -> None:
        """Verify Python files at root and nested levels are discovered."""
        # Create test structure
        (tmp_path / "root_file.py").touch()
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested_file.py").touch()

        # Discover files
        result = discover_python_files(tmp_path)

        # Verify both files found as relative paths
        assert len(result) == 2
        assert Path("root_file.py") in result
        assert Path("subdir/nested_file.py") in result

    def test_excludes_git_directory(self, tmp_path: Path) -> None:
        """Verify .git directory contents are excluded."""
        # Create Python file in root and in .git
        (tmp_path / "main.py").touch()
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config.py").touch()

        result = discover_python_files(tmp_path)

        # Only root file should be found
        assert len(result) == 1
        assert Path("main.py") in result
        assert Path(".git/config.py") not in result

    def test_excludes_venv_directory(self, tmp_path: Path) -> None:
        """Verify venv directory contents are excluded."""
        # Create Python file in root and in venv
        (tmp_path / "app.py").touch()
        venv_dir = tmp_path / "venv"
        venv_dir.mkdir()
        nested = venv_dir / "lib" / "site-packages"
        nested.mkdir(parents=True)
        (nested / "package.py").touch()

        result = discover_python_files(tmp_path)

        # Only root file should be found
        assert len(result) == 1
        assert Path("app.py") in result

    def test_excludes_pycache_directory(self, tmp_path: Path) -> None:
        """Verify __pycache__ directory contents are excluded."""
        # Create Python file in root and in __pycache__
        (tmp_path / "module.py").touch()
        pycache_dir = tmp_path / "__pycache__"
        pycache_dir.mkdir()
        (pycache_dir / "module.cpython-312.pyc").touch()

        result = discover_python_files(tmp_path)

        # Only root file should be found
        assert len(result) == 1
        assert Path("module.py") in result

    def test_returns_sorted_list(self, tmp_path: Path) -> None:
        """Verify returned list is sorted alphabetically."""
        # Create files in non-alphabetical order
        (tmp_path / "zebra.py").touch()
        (tmp_path / "apple.py").touch()
        (tmp_path / "banana.py").touch()

        result = discover_python_files(tmp_path)

        # Verify sorted order
        assert result == sorted(result)
        assert [f.name for f in result] == ["apple.py", "banana.py", "zebra.py"]

    def test_excludes_codemonkey_cache_directory(self, tmp_path: Path) -> None:
        """Verify .codemonkey cache directory contents are excluded."""
        (tmp_path / "service.py").touch()
        cache_dir = tmp_path / ".codemonkey"
        cache_dir.mkdir()
        (cache_dir / "helper.py").touch()

        result = discover_python_files(tmp_path)

        assert result == [Path("service.py")]

    def test_empty_directory_returns_empty_list(self, tmp_path: Path) -> None:
        """Verify empty directory returns empty list."""
        result = discover_python_files(tmp_path)

        assert result == []

    def test_custom_exclude_dirs_override_default(self, tmp_path: Path) -> None:
        """Verify caller-supplied exclude_dirs replaces the default."""
        (tmp_path / "main.py").touch()
        custom_dir = tmp_path / "custom_excluded"
        custom_dir.mkdir()
        (custom_dir / "internal.py").touch()

        result = discover_python_files(tmp_path, exclude_dirs=frozenset({"custom_excluded"}))

        assert result == [Path("main.py")]
