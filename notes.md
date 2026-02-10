agents:

**web researcher**

prompt: request

tools: google search, playwright

result: summary

**project librarian**

init: scan all project files and compare hashes to cache (.codemonkey/file-hashes)

for every dirty file, read the file and summarize into: summary, class and function signatures

compose all summaries into context json (.codemonkey/code-context)

compose a summary of the whole project or adjust the existing one (.codemonkey/project-context)


class ProjectMapper(working_dir):

method map_modules():

1. Load dict of modified files using project_file_hashes.py
2. Load current ModuleContext from cache_manager.py (can be None on first run)
3. Consolidates both returned dict and current ModuleContext, to create a revised ModuleContext where each file or module that was modified has the field "summary" set to None. A modified, added or deleted file will exist in the modified file dict and its summary should be None. A module containing any modification will also reset its summary to None. This should be traversed bottom-to-top, such that any file change will trigger summary=None in all its parents.
4. Summarization will work on this new ModuleContext from bottom to top using summarizer.py. Each file in a module will be summarized first (load code from file). Then, the containing module will be summarized using a list of its file summaries (either new or cached). Then, traversing upwards, each parent module will be summarized according to files and submodules, until we reach the root level.



**lead developer**

prompt: devloper role + project context + direct user requests

tools: FS read, FS secure write (pass to security reviewer first), CLI
