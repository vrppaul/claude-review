# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it privately via [GitHub Security Advisories](https://github.com/vrppaul/claude-review/security/advisories/new).

Do **not** open a public issue for security vulnerabilities.

## Scope

claude-review is a local development tool that binds to `127.0.0.1`. The main security considerations are:

- **No remote access**: the server only listens on localhost
- **No secrets**: the tool does not handle credentials or API keys
- **Git subprocess safety**: all git commands use list arguments (no shell injection)
- **Input validation**: API inputs are validated via Pydantic schemas
