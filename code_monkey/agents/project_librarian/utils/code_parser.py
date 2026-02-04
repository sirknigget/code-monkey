"""Code parsing utilities for the Project Librarian agent.

Provides AST-based extraction of classes, functions, and imports from
Python source files to understand code structure.
"""

import ast
from typing import NamedTuple


class CodeNode(NamedTuple):
    """Represents a node in the code structure tree.

    Attributes:
        name: The name of the class or function.
        type: The type of node - "class" or "function".
        children: List of child nodes (methods for classes, empty for functions).
                  Inner classes are children of their parent class.
    """

    name: str
    type: str
    children: list["CodeNode"] = []


class ParsedCode(NamedTuple):
    """Represents extracted structure from Python source code.

    Attributes:
        classes: List of CodeNode objects for top-level classes.
                 Each class node may have method nodes as children.
        functions: List of CodeNode objects for top-level functions.
        imports: List of import statements found in the source.
    """

    classes: list[CodeNode] = []
    functions: list[CodeNode] = []
    imports: list[str] = []

    found_syntax_error: bool = False

    def llm_friendly_string(self, include_imports: bool = True) -> str:
        """Return a formatted string representation suitable for LLM consumption.

        Args:
            include_imports: Whether to include the imports section in the output.
                Defaults to True.

        Returns:
            A formatted string showing classes, functions, and imports
            in a tree-like structure with proper indentation.
        """
        lines = []

        if self.classes:
            lines.append("=== Classes ===")
            for cls in self.classes:
                lines.append(self._format_node(cls, 0))
            lines.append("")

        if self.functions:
            lines.append("=== Functions ===")
            for func in self.functions:
                lines.append(f"- {func.name}")
            lines.append("")

        if include_imports and self.imports:
            lines.append("=== Imports ===")
            for imp in self.imports:
                lines.append(f"- {imp}")
        if (self.found_syntax_error):
            lines.append("")
            lines.append("=== Note ===")
            lines.append(
                "The source code contained syntax errors and could not be fully parsed."
            )
        return "\n".join(lines)

    def _format_node(self, node: CodeNode, indent: int) -> str:
        """Format a CodeNode with proper indentation for tree display.

        Args:
            node: The CodeNode to format.
            indent: Current indentation level (0 = no indent).

        Returns:
            A formatted string representation of the node and its children.
        """
        prefix = "  " * indent
        lines = [f"{prefix}- {node.name}"]

        for child in node.children:
            lines.append(self._format_node(child, indent + 1))

        return "\n".join(lines)


class CodeExtractor(ast.NodeVisitor):
    """AST visitor that extracts code structure from Python source.

    Builds a tree structure with 2 depth levels:
    - Top level: classes and functions
    - Second level: methods and inner classes (children of classes)

    Does not nest deeper than 2 levels.
    """

    def __init__(self) -> None:
        """Initialize empty lists for extracted elements."""
        self.classes: list[CodeNode] = []
        self.functions: list[CodeNode] = []
        self.imports: list[str] = []
        self._in_class_body: bool = False

    def _process_class_body(self, node: ast.ClassDef, class_node: CodeNode) -> None:
        """Process a class body for methods and inner classes.

        Handles 2-level nesting: class methods and inner classes become children.
        Inner class methods are also extracted (but not deeper nesting).

        Args:
            node: The ClassDef AST node.
            class_node: The CodeNode to populate with children.
        """
        # Set flag to indicate we're inside a class body
        previous_state = self._in_class_body
        self._in_class_body = True

        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                func_node = CodeNode(
                    name=child.name, type="function", children=[]
                )
                class_node.children.append(func_node)
            elif isinstance(child, ast.AsyncFunctionDef):
                func_node = CodeNode(
                    name=f"async {child.name}", type="function", children=[]
                )
                class_node.children.append(func_node)
            elif isinstance(child, ast.ClassDef):
                # Create inner class node
                inner_node = CodeNode(
                    name=child.name, type="class", children=[]
                )
                # Process inner class body for its methods
                self._process_class_body(child, inner_node)
                class_node.children.append(inner_node)
            # Skip other node types (pass, docstring, assignments, etc.)

        # Restore previous state
        self._in_class_body = previous_state

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit a class definition node.

        Creates a class node and processes its body for methods and
        inner classes. Inner class methods are also extracted.

        Args:
            node: The ClassDef AST node.
        """
        class_node = CodeNode(name=node.name, type="class", children=[])

        # Process class body for methods and inner classes
        self._process_class_body(node, class_node)

        # Add class to top-level list (classes are always top-level in our tree)
        self.classes.append(class_node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit a function definition node.

        Only adds to self.functions if not inside a class body.

        Args:
            node: The FunctionDef AST node.
        """
        if not self._in_class_body:
            func_node = CodeNode(name=node.name, type="function", children=[])
            self.functions.append(func_node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit an async function definition node.

        Only adds to self.functions if not inside a class body.

        Args:
            node: The AsyncFunctionDef AST node.
        """
        if not self._in_class_body:
            func_node = CodeNode(
                name=f"async {node.name}", type="function", children=[]
            )
            self.functions.append(func_node)

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
        A ParsedCode NamedTuple containing:
        - classes: List of CodeNode objects for top-level classes
        - functions: List of CodeNode objects for top-level functions
        - imports: List of import statements found in the source
        Returns an empty ParsedCode if the source contains
        syntax errors.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ParsedCode(classes=[], functions=[], imports=[], found_syntax_error=True)

    extractor = CodeExtractor()
    extractor.visit(tree)

    return ParsedCode(
        classes=extractor.classes,
        functions=extractor.functions,
        imports=extractor.imports,
    )
