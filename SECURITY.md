# Security Policy

## Status

This is an **alpha** personal/research tool. It is not versioned with a formal release cadence.

## Scope

`photo-ai` is a local CLI tool. It:

- Makes API calls to local (LM Studio) or cloud (OpenAI, Anthropic) vision models
- Reads image files from your local filesystem
- Writes results to a local SQLite database
- Does not run a server, expose a network port, or handle user-supplied input from untrusted sources

The primary attack surface is credential handling — API keys passed via environment variables.

## Reporting a Vulnerability

If you find a security issue, please open a [GitHub issue](../../issues) or contact the maintainer directly via GitHub. Given the alpha state of this project, there is no formal SLA, but reports will be acknowledged promptly.

## Credentials

- **Never commit API keys.** Use environment variables: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`.
- The `.gitignore` excludes `*.db` files to prevent local analysis data from being committed.
