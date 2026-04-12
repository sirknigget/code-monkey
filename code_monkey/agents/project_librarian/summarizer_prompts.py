FILE_SUMMARY_TEMPLATE = """You are a code analyst. Summarize this code file concisely.

File: {filepath}

Code:
{code}

Requirements:
- State the file's primary purpose
- Mention key classes and functions and imports
- Use active voice
- Keep the summary under {max_lines} lines, including bullet points or wrapping

Summary:"""

####

MODULE_SUMMARY_TEMPLATE = """You are a code analyst. Summarize this Python module (directory).

Module: {module_path}

File summaries:
{file_summaries}

Submodule summaries:
{submodule_summaries}

Requirements:
- Describe the module's purpose and what it provides
- Explain relationships between files
- Mention key exports/APIs
- Keep the summary under {max_lines} lines, including bullet points or wrapping

Summary:"""

#####

PROJECT_SUMMARY_TEMPLATE = """You are a code analyst. Create a project overview with the most important parts.

Project name: {project_name}

Module summaries by directory:
{module_summaries}

Requirements:
- Show module purpose
- Focus on key modules and their responsibilities
- Keep the entire project description under {max_lines} lines total. 
= If the project is too large, omit less important modules and files, but keep the most critical ones to keep the output under {max_lines} lines.

Project structure for your reference:
{project_structure}

If the project is empty, too partial or unclear, simply say something like "The project is empty or lacks sufficient information to provide a summary." and do not attempt to summarize.
"""
