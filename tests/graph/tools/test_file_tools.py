from code_monkey.graph.tools.file_tools import create_file_tools


def test_write_and_read_file(tmp_path):
    tools = create_file_tools(root_dir=str(tmp_path))
    write_tool = next(t for t in tools if t.name == "write_file")
    read_tool = next(t for t in tools if t.name == "read_file")

    write_tool.run({"file_path": "hello.txt", "text": "hello world"})
    content = read_tool.run({"file_path": "hello.txt"})

    assert content == "hello world"


def test_write_creates_file(tmp_path):
    tools = create_file_tools(root_dir=str(tmp_path))
    write_tool = next(t for t in tools if t.name == "write_file")

    result = write_tool.run({"file_path": "new_file.txt", "text": "created"})

    assert result == "File written successfully to new_file.txt."
    assert (tmp_path / "new_file.txt").read_text() == "created"


def test_read_nonexistent_file_returns_error(tmp_path):
    tools = create_file_tools(root_dir=str(tmp_path))
    read_tool = next(t for t in tools if t.name == "read_file")

    result = read_tool.run({"file_path": "missing.txt"})

    assert result == "Error: no such file or directory: missing.txt"
