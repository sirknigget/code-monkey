import warnings

import pytest

from code_monkey.graph.tools.bash_tool import bash_tool


@pytest.fixture(autouse=True)
def suppress_shell_warning():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield


def test_bash_tool_echo():
    result = bash_tool.run({"commands": "echo hello"})

    assert result == "hello\n"


def test_bash_tool_multiline_output():
    result = bash_tool.run({"commands": "printf 'line1\\nline2\\n'"})

    assert result == "line1\nline2\n"


def test_bash_tool_captures_stderr():
    result = bash_tool.run({"commands": ">&2 echo my_error; exit 2"})

    assert result == "my_error\n"


def test_bash_tool_accepts_command_list():
    result = bash_tool.run({"commands": ["echo first", "echo second"]})

    assert result == "first\nsecond\n"
