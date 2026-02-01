"""Tests for code parsing utilities."""

import pytest

from code_monkey.agents.project_librarian.utilities.code_parser import (
    CodeNode,
    ParsedCode,
    parse_python_code,
)


class TestExtractsClassNames:
    """Tests for class name extraction."""

    def test_extracts_single_class(self) -> None:
        """Should extract a single class name."""
        source = "class Foo:\n    pass"
        result = parse_python_code(source)
        assert len(result.classes) == 1
        assert result.classes[0].name == "Foo"
        assert result.classes[0].type == "class"

    def test_extracts_multiple_classes(self) -> None:
        """Should extract multiple class names."""
        source = """
class Foo:
    pass

class Bar:
    pass
"""
        result = parse_python_code(source)
        assert len(result.classes) == 2
        assert result.classes[0].name == "Foo"
        assert result.classes[1].name == "Bar"


class TestExtractsFunctionNames:
    """Tests for function name extraction."""

    def test_extracts_single_function(self) -> None:
        """Should extract a single function name."""
        source = "def foo():\n    pass"
        result = parse_python_code(source)
        assert len(result.functions) == 1
        assert result.functions[0].name == "foo"
        assert result.functions[0].type == "function"

    def test_extracts_multiple_functions(self) -> None:
        """Should extract multiple function names."""
        source = """
def foo():
    pass

def bar():
    pass
"""
        result = parse_python_code(source)
        assert len(result.functions) == 2
        assert result.functions[0].name == "foo"
        assert result.functions[1].name == "bar"


class TestExtractsAsyncFunctions:
    """Tests for async function extraction."""

    def test_extracts_async_function(self) -> None:
        """Should extract async function with 'async' prefix."""
        source = "async def async_foo():\n    pass"
        result = parse_python_code(source)
        assert len(result.functions) == 1
        assert result.functions[0].name == "async async_foo"
        assert result.functions[0].type == "function"

    def test_extracts_mixed_sync_and_async(self) -> None:
        """Should extract both sync and async functions."""
        source = """
def sync_func():
    pass

async def async_func():
    pass
"""
        result = parse_python_code(source)
        assert len(result.functions) == 2
        assert result.functions[0].name == "sync_func"
        assert result.functions[1].name == "async async_func"


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


class TestTreeStructure:
    """Tests for the tree structure with 2 depth levels."""

    def test_class_with_methods(self) -> None:
        """Should extract class with methods as children."""
        source = """
class MyClass:
    def method1(self):
        pass

    async def method2(self):
        pass
"""
        result = parse_python_code(source)
        assert len(result.classes) == 1
        my_class = result.classes[0]
        assert my_class.name == "MyClass"
        assert my_class.type == "class"
        assert len(my_class.children) == 2

        child_names = [c.name for c in my_class.children]
        assert "method1" in child_names
        assert "async method2" in child_names

        for child in my_class.children:
            assert child.type == "function"
            assert len(child.children) == 0  # No deeper nesting

    def test_top_level_function_has_no_children(self) -> None:
        """Top-level functions should have empty children list."""
        source = "def foo():\n    pass"
        result = parse_python_code(source)
        assert len(result.functions) == 1
        assert result.functions[0].children == []

    def test_inner_class(self) -> None:
        """Should extract inner class as child of outer class."""
        source = """
class Outer:
    class Inner:
        pass
"""
        result = parse_python_code(source)
        assert len(result.classes) == 1
        outer = result.classes[0]
        assert outer.name == "Outer"
        assert len(outer.children) == 1

        inner = outer.children[0]
        assert inner.name == "Inner"
        assert inner.type == "class"
        assert len(inner.children) == 0  # No methods of inner class

    def test_inner_class_with_methods(self) -> None:
        """Inner class methods should be children of inner class, not outer."""
        source = """
class Outer:
    class Inner:
        def inner_method(self):
            pass
"""
        result = parse_python_code(source)
        outer = result.classes[0]
        # Only the inner class as child, not its method
        assert len(outer.children) == 1
        assert outer.children[0].name == "Inner"

        # Method should be child of inner class
        inner = outer.children[0]
        assert len(inner.children) == 1
        assert inner.children[0].name == "inner_method"

    def test_no_nesting_deeper_than_2_levels(self) -> None:
        """Verify methods of deeply nested classes don't propagate up."""
        source = """
class Level1:
    class Level2:
        class Level3:
            def deep_method(self):
                pass
"""
        result = parse_python_code(source)
        level1 = result.classes[0]
        assert level1.name == "Level1"

        # Level1 has Level2 as child
        assert len(level1.children) == 1
        level2 = level1.children[0]
        assert level2.name == "Level2"
        assert level2.type == "class"

        # Level2 has Level3 as child (not deep_method)
        assert len(level2.children) == 1
        level3 = level2.children[0]
        assert level3.name == "Level3"
        assert level3.type == "class"

        # Level3 has the method
        assert len(level3.children) == 1
        assert level3.children[0].name == "deep_method"

    def test_class_without_methods(self) -> None:
        """Class with no methods should have empty children list."""
        source = "class EmptyClass:\n    pass"
        result = parse_python_code(source)
        assert len(result.classes) == 1
        assert result.classes[0].children == []

    def test_multiple_classes_with_methods(self) -> None:
        """Each class should have its own isolated children."""
        source = """
class ClassA:
    def method_a(self):
        pass

class ClassB:
    def method_b(self):
        pass
    async def async_b(self):
        pass
"""
        result = parse_python_code(source)
        assert len(result.classes) == 2

        class_a = result.classes[0]
        assert class_a.name == "ClassA"
        assert len(class_a.children) == 1
        assert class_a.children[0].name == "method_a"

        class_b = result.classes[1]
        assert class_b.name == "ClassB"
        assert len(class_b.children) == 2
        child_names = [c.name for c in class_b.children]
        assert "method_b" in child_names
        assert "async async_b" in child_names


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
        result = ParsedCode(
            classes=[CodeNode(name="A", type="class")],
            functions=[CodeNode(name="b", type="function")],
            imports=["c"],
        )
        assert len(result.classes) == 1
        assert result.classes[0].name == "A"
        assert len(result.functions) == 1
        assert result.functions[0].name == "b"
        assert result.imports == ["c"]

    def test_parsed_code_empty_default(self) -> None:
        """Should support empty initialization."""
        result = ParsedCode()
        assert result.classes == []
        assert result.functions == []
        assert result.imports == []


class TestCodeNodeStructure:
    """Tests for CodeNode structure."""

    def test_code_node_with_children(self) -> None:
        """CodeNode should support children attribute."""
        node = CodeNode(
            name="MyClass",
            type="class",
            children=[
                CodeNode(name="method", type="function"),
            ],
        )
        assert node.name == "MyClass"
        assert node.type == "class"
        assert len(node.children) == 1
        assert node.children[0].name == "method"

    def test_code_node_default_children(self) -> None:
        """CodeNode should default to empty children list."""
        node = CodeNode(name="func", type="function")
        assert node.children == []


class TestLlmFriendlyString:
    """Tests for llm_friendly_string method."""

    def test_empty_parsed_code(self) -> None:
        """Empty ParsedCode should return empty string."""
        result = ParsedCode()
        assert result.llm_friendly_string() == ""

    def test_classes_with_methods(self) -> None:
        """Should format classes with methods correctly."""
        code = ParsedCode(
            classes=[
                CodeNode(
                    name="MyClass",
                    type="class",
                    children=[
                        CodeNode(name="method1", type="function"),
                        CodeNode(name="async method2", type="function"),
                    ],
                )
            ]
        )
        result = code.llm_friendly_string()
        assert "=== Classes ===" in result
        assert "- MyClass" in result
        assert "  - method1" in result
        assert "  - async method2" in result

    def test_functions_only(self) -> None:
        """Should format functions correctly."""
        code = ParsedCode(
            functions=[
                CodeNode(name="func1", type="function"),
                CodeNode(name="async func2", type="function"),
            ]
        )
        result = code.llm_friendly_string()
        assert "=== Functions ===" in result
        assert "- func1" in result
        assert "- async func2" in result

    def test_imports_only(self) -> None:
        """Should format imports correctly."""
        code = ParsedCode(imports=["os", "sys", "pathlib.Path"])
        result = code.llm_friendly_string()
        assert "=== Imports ===" in result
        assert "- os" in result
        assert "- sys" in result
        assert "- pathlib.Path" in result

    def test_full_structure(self) -> None:
        """Should format all sections when present."""
        code = ParsedCode(
            classes=[
                CodeNode(
                    name="Outer",
                    type="class",
                    children=[
                        CodeNode(
                            name="Inner",
                            type="class",
                            children=[
                                CodeNode(name="inner_method", type="function"),
                            ],
                        ),
                        CodeNode(name="outer_method", type="function"),
                    ],
                )
            ],
            functions=[CodeNode(name="top_level", type="function")],
            imports=["os", "typing.List"],
        )
        result = code.llm_friendly_string()

        assert "=== Classes ===" in result
        assert "=== Functions ===" in result
        assert "=== Imports ===" in result

        # Check class hierarchy
        assert "- Outer" in result
        assert "  - Inner" in result
        assert "    - inner_method" in result
        assert "  - outer_method" in result

    def test_inner_class_structure(self) -> None:
        """Should correctly show inner class nesting."""
        code = ParsedCode(
            classes=[
                CodeNode(
                    name="Container",
                    type="class",
                    children=[
                        CodeNode(
                            name="Nested",
                            type="class",
                            children=[CodeNode(name="nested_method", type="function")],
                        )
                    ],
                )
            ]
        )
        result = code.llm_friendly_string()
        lines = result.split("\n")
        container_idx = next(i for i, line in enumerate(lines) if "- Container" in line)
        nested_idx = next(i for i, line in enumerate(lines) if "- Nested" in line)
        method_idx = next(i for i, line in enumerate(lines) if "nested_method" in line)

        assert container_idx < nested_idx < method_idx

    def test_excludes_imports_when_false(self) -> None:
        """Should exclude imports section when include_imports=False."""
        code = ParsedCode(
            classes=[CodeNode(name="MyClass", type="class")],
            functions=[CodeNode(name="func1", type="function")],
            imports=["os", "sys"],
        )
        result = code.llm_friendly_string(include_imports=False)

        assert "=== Classes ===" in result
        assert "=== Functions ===" in result
        assert "=== Imports ===" not in result
        assert "- os" not in result
        assert "- sys" not in result
        assert "- MyClass" in result
        assert "- func1" in result

    def test_includes_imports_by_default(self) -> None:
        """Imports should be included by default (backward compatibility)."""
        code = ParsedCode(
            classes=[CodeNode(name="MyClass", type="class")],
            imports=["os"],
        )
        result = code.llm_friendly_string()

        assert "=== Imports ===" in result
        assert "- os" in result

    def test_explicit_include_imports_true(self) -> None:
        """Should include imports when explicitly set to True."""
        code = ParsedCode(
            functions=[CodeNode(name="func", type="function")],
            imports=["typing"],
        )
        result = code.llm_friendly_string(include_imports=True)

        assert "=== Functions ===" in result
        assert "=== Imports ===" in result
        assert "- typing" in result
