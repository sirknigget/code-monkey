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


**lead developer**

prompt: devloper role + project context + direct user requests

tools: FS read, FS secure write (pass to security reviewer first), CLI
