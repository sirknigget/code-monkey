"""Tests for code parsing utilities."""

import pytest

from code_monkey.agents.project_librarian.utilities.code_parser import (
    ParsedCode,
    parse_python_code,
)


class TestExtractsClassNames:
    """Tests for class name extraction."""

    def test_extracts_single_class(self) -> None:
        """Should extract a single class name."""
        source = "class Foo:\n    pass"
        result = parse_python_code(source)
        assert result.classes == ["Foo"]

    def test_extracts_multiple_classes(self) -> None:
        """Should extract multiple class names."""
        source = """
class Foo:
    pass

class Bar:
    pass
"""
        result = parse_python_code(source)
        assert result.classes == ["Foo", "Bar"]


class TestExtractsFunctionNames:
    """Tests for function name extraction."""

    def test_extracts_single_function(self) -> None:
        """Should extract a single function name."""
        source = "def foo():\n    pass"
        result = parse_python_code(source)
        assert result.functions == ["foo"]

    def test_extracts_multiple_functions(self) -> None:
        """Should extract multiple function names."""
        source = """
def foo():
    pass

def bar():
    pass
"""
        result = parse_python_code(source)
        assert result.functions == ["foo", "bar"]


class TestExtractsAsyncFunctions:
    """Tests for async function extraction."""

    def test_extracts_async_function(self) -> None:
        """Should extract async function with 'async' prefix."""
        source = "async def async_foo():\n    pass"
        result = parse_python_code(source)
        assert result.functions == ["async async_foo"]

    def test_extracts_mixed_sync_and_async(self) -> None:
        """Should extract both sync and async functions."""
        source = """
def sync_func():
    pass

async def async_func():
    pass
"""
        result = parse_python_code(source)
        assert result.functions == ["sync_func", "async async_func"]


class TestExtractsImports:
    """Tests for import statement extraction."""

    def test_extracts_simple_import(self) -> None:
        """Should extract simple import statements."""
        source = "import os"
        result = parse_python_code(source)
        assert result.imports == ["os"]

    def test_extracts_multiple_imports(self) -> None:
        """Should extract multiple import statements."""
        source = """
import os
import sys
"""
        result = parse_python_code(source)
        assert result.imports == ["os", "sys"]

    def test_extracts_import_with_alias(self) -> None:
        """Should extract import with alias."""
        source = "import os as operating_system"
        result = parse_python_code(source)
        assert result.imports == ["operating_system"]


class TestExtractsImportFrom:
    """Tests for from-import statement extraction."""

    def test_extracts_from_import(self) -> None:
        """Should extract from-import statements."""
        source = "from pathlib import Path"
        result = parse_python_code(source)
        assert result.imports == ["pathlib.Path"]

    def test_extracts_from_import_multiple(self) -> None:
        """Should extract multiple names from from-import."""
        source = "from typing import List, Dict, Optional"
        result = parse_python_code(source)
        assert result.imports == ["typing.List", "typing.Dict", "typing.Optional"]


class TestExtractsAllStructure:
    """Tests for comprehensive structure extraction."""

    def test_extracts_all_structure(self) -> None:
        """Should extract classes, functions, and imports together."""
        source = """
import os

from typing import List

class MyClass:
    def method(self):
        pass

async def async_method():
    pass
"""
        result = parse_python_code(source)
        assert result.classes == ["MyClass"]
        assert result.functions == ["method", "async async_method"]
        assert result.imports == ["os", "typing.List"]


class TestSyntaxErrorHandling:
    """Tests for syntax error handling."""

    def test_syntax_error_returns_empty(self) -> None:
        """Should return empty ParsedCode on syntax error."""
        source = "def invalidSyntax(  # missing colon"
        result = parse_python_code(source)
        assert result == ParsedCode(classes=[], functions=[], imports=[])

    def test_empty_source_returns_empty(self) -> None:
        """Should return empty ParsedCode for empty source."""
        source = ""
        result = parse_python_code(source)
        assert result == ParsedCode(classes=[], functions=[], imports=[])


class TestParsedCodeStructure:
    """Tests for ParsedCode NamedTuple structure."""

    def test_parsed_code_is_namedtuple(self) -> None:
        """Should be a proper NamedTuple."""
        result = ParsedCode(classes=["A"], functions=["b"], imports=["c"])
        assert result.classes == ["A"]
        assert result.functions == ["b"]
        assert result.imports == ["c"]

    def test_parsed_code_empty_default(self) -> None:
        """Should support empty initialization."""
        result = ParsedCode()
        assert result.classes == []
        assert result.functions == []
        assert result.imports == []
