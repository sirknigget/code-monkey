# Quick Plan: Tree Structure for Code Parser

**Task:** Modify code_parser.py to return a tree structure with 2 depth levels

## Tasks

### 1. Modify ParsedCode NamedTuple to support tree structure

**File:** `code_monkey/agents/project_librarian/utilities/code_parser.py`

Change `ParsedCode` to hold tree nodes instead of flat lists. Each node should have:
- `name`: str
- `type`: str ("class" or "function")
- `children`: list of child nodes (max 1 level deep for methods/inner classes)

**Current structure (flat):**
```python
class ParsedCode(NamedTuple):
    classes: list[str]
    functions: list[str]
    imports: list[str]
```

**New structure (tree):**
```python
class CodeNode(NamedTuple):
    name: str
    type: str  # "class" or "function"
    children: list["CodeNode"] = []

class ParsedCode(NamedTuple):
    classes: list[CodeNode]  # Each class node may have methods as children
    functions: list[CodeNode]  # Top-level functions
    imports: list[str]
```

### 2. Update CodeExtractor to build tree structure

**Changes:**
- Track current class context during traversal
- When visiting methods, add them as children to current class node
- When visiting inner classes, add them as children to current class node
- Top-level functions go directly to `functions` list

**Key logic:**
```python
def visit_ClassDef(self, node):
    class_node = CodeNode(name=node.name, type="class", children=[])
    self.classes.append(class_node)
    # Don't call generic_visit - we control what gets added as children
    # Methods found at this level will be added as children to this class_node

def visit_FunctionDef(self, node):
    if self.current_class:
        self.current_class.children.append(CodeNode(name=node.name, type="function"))
    else:
        self.functions.append(CodeNode(name=node.name, type="function"))
```

### 3. Update tests in test_code_parser.py

**Test changes:**
- `TestExtractsClassNames`: Verify classes are CodeNode objects with correct name/type
- `TestExtractsFunctionNames`: Verify functions are CodeNode objects
- `TestExtractsAsyncFunctions`: Verify async functions have type="function" and "async " prefix on name
- `TestExtractsImports`: No change (imports remain flat list of strings)
- `TestSyntaxErrorHandling`: Verify empty ParsedCode with empty class/function lists
- `TestParsedCodeStructure`: Verify CodeNode structure and children attribute

**New test for tree structure:**
```python
class TestTreeStructure:
    def test_class_with_methods(self):
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
        method_names = [c.name for c in my_class.children]
        assert "method1" in method_names
        assert "async method2" in method_names

    def test_inner_class(self):
        source = """
        class Outer:
            class Inner:
                pass
        """
        result = parse_python_code(source)
        outer = result.classes[0]
        assert outer.name == "Outer"
        assert len(outer.children) == 1
        inner = outer.children[0]
        assert inner.name == "Inner"
        assert inner.type == "class"

    def test_no_nesting_deeper_than_2_levels(self):
        """Verify methods of inner class don't get added to outer class."""
        source = """
        class Outer:
            class Inner:
                def inner_method(self):
                    pass
        """
        result = parse_python_code(source)
        outer = result.classes[0]
        # Only the inner class, not its method
        assert len(outer.children) == 1
        assert outer.children[0].name == "Inner"
```

### 4. Update tests in test_utilities_integration.py

**Changes:**
- `TestFullWorkflow`: Update assertions to use new tree structure
- `TestDirectoryAnalysis`: Update assertions for nested class/method parsing

## Verification

Run tests to verify:
```bash
uv run pytest tests/agents/project_librarian/test_code_parser.py tests/agents/project_librarian/test_utilities_integration.py -v
```

All tests should pass with the new tree structure.
