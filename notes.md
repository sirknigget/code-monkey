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



project mapper class that creates the project context files from code. the class knows how to scan the whole project or get a list of paths to update.
for a scanned project, it will check against the file hashes and only update modified filed, while updating their new hashes.
once its known which files to update, it will run over the directory structure starting from top level and progressing deeper. it will only run on directories where a change occured.
for each code file to update, it will prompt an LLM to summarize the file and its purpose (LLM provided on class initialization). it will also run the code parser to get a definition tree.
after finishing file summarizations and parsing for a directory, it will also prompt an LLM to create a module summary - using only code file summaries and their parsed elements.
if a module summary existed already, the LLM will be prompted to just update it with the new information.
for every subfolder (module), and every code file summarization inside it, a short summary of the parent module will be provided to the LLM summarization prompt.
once the whole traversal is complete, a project context summary will be created in a separate file, using a tree formatted representation of all module and code summaries, fed to an LLM with a summarization prompt.



**lead developer**

prompt: devloper role + project context + direct user requests

tools: FS read, FS secure write (pass to security reviewer first), CLI
