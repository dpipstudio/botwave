# Contributing to BotWave

Thank you for your interest in contributing to **BotWave**!  
Contributions of all kinds are welcome, whether it’s code, documentation, bug reports, or suggestions.

Please take a moment to read this guide before contributing.


## Ways to Contribute

You can contribute by:
- Reporting bugs
- Suggesting new features or improvements
- Improving documentation
- Submitting pull requests
- Reviewing existing pull requests


## Reporting Bugs & Issues

If you encounter a bug or unexpected behavior, please open an issue in the  
[/issues](/issues) section.

When reporting an issue, try to include:
- A clear and descriptive title
- Steps to reproduce the issue
- Expected behavior vs actual behavior
- Relevant logs, screenshots, or error messages
- Your environment (OS, version, setup, etc.)

**Security vulnerabilities should NOT be reported via issues.**  
Please refer to the `SECURITY.md` file for responsible disclosure instructions.


## Feature Requests

Feature requests are welcome!  
Before opening a new issue, please check if a similar request already exists.

When suggesting a feature:
- Explain the problem it solves
- Describe the proposed solution
- Mention any alternatives you’ve considered


## Pull Requests

We’re happy to review pull requests!

Before submitting a PR:
- Fork the repository and create a new branch
- Keep changes focused and relevant
- Follow the existing code style and structure
- Test your changes where applicable
- Update documentation if needed

When opening a pull request:
- Clearly describe what your PR does
- Reference related issues if applicable
- Be open to feedback and requested changes


## Code Style & Guidelines

- Keep code clean, readable, and well-organized (at least try to)
- Avoid unnecessary dependencies
- Comment complex or non-obvious logic

## Commit Messages

Even though we won't reject contributions that don't follow our commit formatting, we'd appreciate it if you followed this pattern when writing commits:

```
[<component>] <path>: <commit message>
```

The message is made up of 3 parts:

- **Component**: the specific part of the project affected by the change. Examples: `client`, `server`, `docs`, `workflows`, etc. If you can't find a specific enough component, you can use a generic term such as `project`.
- **Path**: the path within that component. To avoid long paths, you can omit the part that's already implied by the component. For example, if the component is `workflows`, you can simply write `wiki-mirror.yml` and we'll understand that the commit concerns `.github/workflows/wiki-mirror.yml`. If the commit affects multiple paths, you can use globbing, or separate them with commas. Examples: `ops/*.py`, `shared/tls.py, shared/http.py`.
- **Commit message**: a short message describing your changes.

### Examples

```
[server] ops/live.py: fix ALSA rate being wrongly sent
[client] client.py: better exception handling
[docs] README.md: update installation steps
[workflows] wiki-mirror.yml: ensure the new commit recommendation
[docs] client/client.md: updated cli documentation
```

## Community & Conduct

Be respectful and constructive in discussions.  
Harassment, hate speech, or hostile behavior will not be tolerated.


## Questions

If you’re unsure about anything, feel free to open an issue and ask.

Thanks for helping make **BotWave** better <3
