"""Code parsing utilities for the Project Librarian agent.

Provides AST-based extraction of classes, functions, and imports from
Python source files to understand code structure.
"""

import ast
from typing import NamedTuple


class ParsedCode(NamedTuple):
    """Represents extracted structure from Python source code.

    Attributes:
        classes: List of class names found in the source.
        functions: List of function names found in the source.
                  Async functions are prefixed with "async ".
        imports: List of import statements found in the source.
    """

    classes: list[str] = []
    functions: list[str] = []
    imports: list[str] = []


class CodeExtractor(ast.NodeVisitor):
    """AST visitor that extracts code structure from Python source.

    Extracts class names, function names (sync and async), and
    import statements from the AST.
    """

    def __init__(self) -> None:
        """Initialize empty lists for extracted elements."""
        self.classes: list[str] = []
        self.functions: list[str] = []
        self.imports: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit a class definition node.

        Args:
            node: The ClassDef AST node.
        """
        self.classes.append(node.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit a function definition node.

        Args:
            node: The FunctionDef AST node.
        """
        self.functions.append(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit an async function definition node.

        Args:
            node: The AsyncFunctionDef AST node.
        """
        self.functions.append(f"async {node.name}")
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Visit an import statement node.

        Args:
            node: The Import AST node.
        """
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports.append(name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit a from-import statement node.

        Args:
            node: The ImportFrom AST node.
        """
        module = node.module or ""
        for alias in node.names:
            if module:
                self.imports.append(f"{module}.{alias.name}")
            else:
                self.imports.append(alias.name)


def parse_python_code(source: str) -> ParsedCode:
    """Parse Python source code and extract structure.

    Extracts class names, function names, and import statements
    from the given Python source code.

    Args:
        source: The Python source code to parse.

    Returns:
        A ParsedCode NamedTuple containing lists of classes,
        functions, and imports found in the source.
        Returns an empty ParsedCode if the source contains
        syntax errors.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ParsedCode(classes=[], functions=[], imports=[])

    extractor = CodeExtractor()
    extractor.visit(tree)

    return ParsedCode(
        classes=extractor.classes,
        functions=extractor.functions,
        imports=extractor.imports,
    )
