# Agent instructions

These instructions apply to all agents working in this repository.

## Writing

- Do not hard-wrap prose in Markdown or comments. Keep each paragraph on one line and let the editor wrap it visually.
- Write like a person explaining something to another person. Use plain words, direct sentences, and concrete details.
- Avoid colons, semicolons, em dashes, and double hyphens as punctuation in prose. Split the sentence or rephrase it instead. This does not apply to code, commands, configuration syntax, URLs, or exact quotations.
- Keep documentation concise. Use headings and lists when they make the content easier to read, without turning every short explanation into a section.
- Avoid stock phrases, marketing language, filler, and repetitive summaries.
- Write comments that explain a reason, constraint, or surprising behavior. Do not narrate what the code already makes obvious.
- Match the language and tone of the surrounding document. Keep repository documentation in English unless asked otherwise.
- Clearly distinguish what is implemented from what is planned. Do not describe an intended setup as already deployed.

## Working in this repository

- Read the relevant README and existing files before making changes. Follow established patterns and prefer simple, maintainable solutions.
- Keep changes focused on the request. Preserve unrelated edits and avoid opportunistic rewrites or formatting changes.
- Handle routine, reversible choices without asking for confirmation. Ask when a missing detail materially changes the result and cannot be inferred from the repository.
- Prefer persistent changes through this repository over manual changes to running systems. Only deploy or modify live infrastructure when the user has authorized it.
- Keep credentials encrypted with SOPS. Never include plaintext secrets in documentation, comments, command output, or commits.
- Update related documentation when a change affects how something works or how it is operated.
- Run checks appropriate to the change. Use `make syntax` for Ansible changes. Treat `make check` as a command that contacts real hosts, and be careful with secret values in its diff output.
- Do not commit or push unless asked.

## Communication

- Be concise and direct. Explain meaningful decisions and tradeoffs without narrating every tool call.
- State assumptions and uncertainty plainly. Do not claim something was tested or deployed unless it was.
- When finished, explain what changed, what was checked, and anything that still needs attention.
