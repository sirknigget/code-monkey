"""Integration tests for Project Librarian utilities.

Verifies that all utilities work together cohesively and provide
a unified interface for project analysis.
"""

import tempfile
import textwrap
from pathlib import Path

import pytest

from code_monkey.agents.project_librarian.utilities import (
    compute_file_hash,
    discover_python_files,
    parse_python_code,
)


class TestFullWorkflow:
    """Test complete workflow from file discovery to code parsing."""

    def test_discover_and_parse_multiple_files(self):
        """Find files, compute hashes, parse code structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create test files
            file1 = tmppath / "module1.py"
            file1.write_text(
                textwrap.dedent(
                    """
                    class DataProcessor:
                        def process(self, data):
                            return data.upper()

                        async def async_process(self, data):
                            return data.lower()
                    """
                )
            )

            file2 = tmppath / "module2.py"
            file2.write_text(
                textwrap.dedent(
                    """
                    from typing import List

                    class Validator:
                        def validate(self, value: str) -> bool:
                            return len(value) > 0
                    """
                )
            )

            # Discover Python files
            files = discover_python_files(tmppath)
            assert len(files) == 2
            assert file1 in files
            assert file2 in files

            # Compute hashes for each file
            hashes = {f: compute_file_hash(f) for f in files}
            for f in files:
                assert len(hashes[f]) == 64  # SHA-256 hex digest

            # Parse code structure
            for f in files:
                source = f.read_text()
                parsed = parse_python_code(source)
                assert len(parsed.classes) >= 1

                # Check tree structure
                for cls in parsed.classes:
                    assert cls.type == "class"
                    for method in cls.children:
                        assert method.type == "function"

    def test_hash_changes_after_modification(self):
        """Verify hash changes when file content changes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            test_file = tmppath / "test.py"
            test_file.write_text("original content")

            original_hash = compute_file_hash(test_file)

            # Modify file
            test_file.write_text("modified content")
            new_hash = compute_file_hash(test_file)

            assert original_hash != new_hash


class TestDirectoryAnalysis:
    """Test analysis of directories with multiple files containing various constructs."""

    def test_directory_with_classes_and_functions(self):
        """Test parsing files with classes, async functions, and imports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create a complex test file
            complex_file = tmppath / "complex.py"
            complex_file.write_text(
                textwrap.dedent(
                    """
                    import os
                    import sys
                    from typing import Dict, List, Optional

                    class BaseClass:
                        pass

                    class DerivedClass(BaseClass):
                        def method_one(self):
                            pass

                        async def method_two(self):
                            pass

                    def standalone_function():
                        return "hello"

                    async def async_function():
                        return "world"
                    """
                )
            )

            # Discover and analyze
            files = discover_python_files(tmppath)
            assert len(files) == 1

            source = files[0].read_text()
            parsed = parse_python_code(source)

            # Check tree structure
            assert len(parsed.classes) == 2

            base_class = parsed.classes[0]
            assert base_class.name == "BaseClass"
            assert base_class.type == "class"
            assert len(base_class.children) == 0

            derived_class = parsed.classes[1]
            assert derived_class.name == "DerivedClass"
            assert derived_class.type == "class"
            assert len(derived_class.children) == 2

            method_names = [c.name for c in derived_class.children]
            assert "method_one" in method_names
            assert "async method_two" in method_names

            # Check top-level functions
            assert len(parsed.functions) == 2
            func_names = [f.name for f in parsed.functions]
            assert "standalone_function" in func_names
            assert "async async_function" in func_names

            # Check imports
            assert "os" in parsed.imports
            assert "sys" in parsed.imports
            assert "typing.Dict" in parsed.imports

    def test_nested_directory_structure(self):
        """Test file discovery in nested directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create nested structure
            (tmppath / "src").mkdir()
            (tmppath / "src" / "main.py").write_text("class Main: pass")
            (tmppath / "src" / "utils.py").write_text("def helper(): pass")
            (tmppath / "tests").mkdir()
            (tmppath / "tests" / "test_main.py").write_text("class TestMain: pass")
            (tmppath / "tests" / "test_utils.py").write_text("class TestUtils: pass")

            # Discover files (should include nested dirs but exclude __pycache__)
            files = discover_python_files(tmppath)
            file_names = [f.name for f in files]

            assert "main.py" in file_names
            assert "utils.py" in file_names
            assert "test_main.py" in file_names
            assert "test_utils.py" in file_names

    def test_empty_directory(self):
        """Test handling of directories with no Python files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create non-Python files
            (tmppath / "readme.txt").write_text("README")
            (tmppath / "config.json").write_text("{}")

            files = discover_python_files(tmppath)
            assert len(files) == 0


class TestRejectsNonPythonFiles:
    """Test that only .py files are returned by the pattern."""

    def test_excludes_non_python_extensions(self):
        """Verify non-Python files are not included in discovery."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create various file types
            (tmppath / "valid.py").write_text("x = 1")
            (tmppath / "script.py").write_text("y = 2")
            (tmppath / "readme.md").write_text("# Readme")
            (tmppath / "config.json").write_text("{}")
            (tmppath / "Dockerfile").write_text("FROM python:3.12")
            (tmppath / ".env").write_text("DEBUG=true")

            files = discover_python_files(tmppath)
            file_names = [f.name for f in files]

            assert len(files) == 2
            assert "valid.py" in file_names
            assert "script.py" in file_names
            assert "readme.md" not in file_names
            assert "config.json" not in file_names

    def test_excludes_pycache_and_venv(self):
        """Verify __pycache__, .venv, and similar are excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create normal Python file
            (tmppath / "main.py").write_text("x = 1")

            # Create excluded directories
            (tmppath / "__pycache__").mkdir()
            (tmppath / "__pycache__" / "module.pyc").write_text("bytes")

            (tmppath / ".venv").mkdir()
            (tmppath / ".venv" / "lib").mkdir()
            (tmppath / ".venv" / "lib" / "site-packages").mkdir()
            (tmppath / ".venv" / "lib" / "site-packages" / "package.py").write_text(
                "x = 1"
            )

            (tmppath / "node_modules").mkdir()
            (tmppath / "node_modules" / "package").mkdir()
            (tmppath / "node_modules" / "package" / "index.js").write_text("console.log")

            files = discover_python_files(tmppath)
            file_names = [f.name for f in files]

            assert len(files) == 1
            assert "main.py" in file_names


class TestImportFromUtilitiesModule:
    """Test that utilities can be imported from the unified module."""

    def test_import_all_utilities(self):
        """Verify all utilities are importable from the module."""
        from code_monkey.agents.project_librarian.utilities import (
            compute_file_hash,
            discover_python_files,
            parse_python_code,
        )

        # Verify they are callable
        assert callable(compute_file_hash)
        assert callable(discover_python_files)
        assert callable(parse_python_code)

    def test_import_single_line(self):
        """Verify single-line import pattern works."""
        # This is the documented import pattern
        from code_monkey.agents.project_librarian.utilities import (
            discover_python_files,
            parse_python_code,
            compute_file_hash,
        )

        assert callable(discover_python_files)
        assert callable(parse_python_code)
        assert callable(compute_file_hash)


class TestTreeStructureIntegration:
    """Integration tests specifically for tree structure functionality."""

    def test_complex_inheritance_hierarchy(self):
        """Test parsing of nested class inheritance structures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            test_file = tmppath / "inheritance.py"
            test_file.write_text(
                textwrap.dedent(
                    """
                    class Animal:
                        def breathe(self):
                            pass

                    class Dog(Animal):
                        def bark(self):
                            pass

                        class ServiceDog(Dog):
                            def assist(self):
                                pass

                            def bark_loudly(self):
                                pass
                    """
                )
            )

            files = discover_python_files(tmppath)
            assert len(files) == 1

            source = files[0].read_text()
            parsed = parse_python_code(source)

            # Animal and Dog are top-level classes (inheritance doesn't create nesting)
            # ServiceDog is an inner class of Dog
            assert len(parsed.classes) == 2  # Animal and Dog

            # Find Animal and Dog by name
            animal = next((c for c in parsed.classes if c.name == "Animal"), None)
            dog = next((c for c in parsed.classes if c.name == "Dog"), None)

            assert animal is not None
            assert animal.name == "Animal"
            assert len(animal.children) == 1
            assert animal.children[0].name == "breathe"

            assert dog is not None
            assert dog.name == "Dog"

            # Dog has bark method and ServiceDog as inner class
            assert len(dog.children) == 2  # bark method and ServiceDog class
            child_types = [c.type for c in dog.children]
            assert "function" in child_types
            assert "class" in child_types

            # Find ServiceDog child
            service_dog = [c for c in dog.children if c.type == "class"][0]
            assert service_dog.name == "ServiceDog"
            assert len(service_dog.children) == 2  # assist and bark_loudly methods

    def test_mixed_top_level_and_nested(self):
        """Test file with both top-level and nested definitions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            test_file = tmppath / "mixed.py"
            test_file.write_text(
                textwrap.dedent(
                    """
                    # Top-level function
                    def top_function():
                        pass

                    # Top-level class
                    class TopClass:
                        def top_method(self):
                            pass

                        class NestedClass:
                            def nested_method(self):
                                pass

                    # Another top-level function
                    async def another_async():
                        pass
                    """
                )
            )

            files = discover_python_files(tmppath)
            parsed = parse_python_code(files[0].read_text())

            # Top-level functions
            assert len(parsed.functions) == 2
            func_names = [f.name for f in parsed.functions]
            assert "top_function" in func_names
            assert "async another_async" in func_names

            # Top-level classes
            assert len(parsed.classes) == 1  # Only TopClass
            top_class = parsed.classes[0]
            assert top_class.name == "TopClass"

            # TopClass has method and nested class
            assert len(top_class.children) == 2
            child_names = [c.name for c in top_class.children]
            assert "top_method" in child_names
            assert "NestedClass" in child_names

            # NestedClass has its own method
            nested_class = top_class.children[1]
            assert nested_class.type == "class"
            assert len(nested_class.children) == 1
            assert nested_class.children[0].name == "nested_method"
