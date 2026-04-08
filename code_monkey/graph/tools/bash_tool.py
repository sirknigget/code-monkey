from langchain_community.tools.shell.tool import ShellTool
from langchain_experimental.llm_bash.bash import BashProcess


class _BashProcessWithCwd(BashProcess):
    def __init__(self, cwd: str) -> None:
        super().__init__()
        self._cwd = cwd

    def _run(self, command: str) -> str:
        return super()._run(f"cd {self._cwd} && {command}")


def create_bash_tool(root_dir: str) -> ShellTool:
    return ShellTool(
        process=_BashProcessWithCwd(cwd=root_dir),
        ask_human_input=True,
    )
