from langchain_community.tools.file_management import ReadFileTool, WriteFileTool
from langchain_core.tools import BaseTool


def create_file_tools(root_dir: str) -> list[BaseTool]:
    """Create file read/write tools scoped to the given root directory."""
    return [
        ReadFileTool(root_dir=root_dir),
        WriteFileTool(root_dir=root_dir),
    ]
