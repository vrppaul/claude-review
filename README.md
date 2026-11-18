# claude-review

[![PyPI](https://img.shields.io/pypi/v/claude-review)](https://pypi.org/project/claude-review/)
[![Python](https://img.shields.io/python/required-version-toml?tomlFilePath=https://raw.githubusercontent.com/vrppaul/claude-review/master/pyproject.toml&label=python)](https://pypi.org/project/claude-review/)
[![CI](https://github.com/vrppaul/claude-review/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/vrppaul/claude-review/actions/workflows/ci.yml)
[![License](https://img.shields.io/pypi/l/claude-review)](https://github.com/vrppaul/claude-review/blob/master/LICENSE)

A local tool to understand what your coding agent changed and iterate on it fast. Like a pull request in your browser, where the agent answers instantly.

<!-- Links and images are addresses, not paths: PyPI shows this README too, and a path from the repository finds nothing there -->
<!-- A clip is a comment naming and describing it, an empty line and its address alone on a line, which GitHub plays. PyPI plays no video: pyproject.toml turns the three into the clip's poster, docs/<name>-poster.jpg -->

<!-- clip: hero — the agent's terminal and /review-ui, a question asked on a line and answered in its thread, a question in the agent's panel, the round sent and the fix shown on the line -->

https://github.com/user-attachments/assets/deed0eff-7214-482c-9e8d-54ffd2f26d89

## Start

Install the skill with the `skills` CLI, for Claude Code, Codex, Cursor and the other agents that CLI supports:

```bash
npx skills add vrppaul/claude-review -g -y
```

Or, in Claude Code, as a plugin:

```
/plugin marketplace add vrppaul/claude-review
/plugin install claude-review@claude-review-marketplace
```

Then, in Claude Code, type `/review-ui` in a repository with changes; another agent calls the skill its own way. It
installs or upgrades the CLI with [uv](https://docs.astral.sh/uv/getting-started/installation/), which must already
be on your machine, and opens the review in your browser. The agent that wrote the code stays attached to answer.

## Ask and fix on the line

Click a line number, or drag across several, and write. Press "Ask agent now" and the agent answers in that thread
while you read on.

What no single line covers, such as the plan, the tests or a file nobody commented on, goes in the agent's panel on
the right.

Comments you add wait for you to send them. Press "Send round" and the agent answers, makes the changes and takes the
diff again. Your threads stay on their lines, one whose lines are gone is marked outdated, and you read on from where
you were.

## Let the agent tell the story

Some changes are hard to take in from the diff. Press Story in the header: it says what a story will cost in tokens
and asks first. Then the agent that made the change tells it: what was asked, what it did and what to doubt, then
chapters in the order to read them, each piece of code under the reason it is that way. Ask about any of its words as
you would about a line.

<!-- clip: story — the story's three cards, its list of chapters, its diagram followed to a chapter, a question asked on the chapter's reason and answered under it -->

https://github.com/user-attachments/assets/ce703182-dafb-4ead-85b9-a9c567244f50

## Nothing new leaves your machine

- The review is served on 127.0.0.1, so only your machine can open it. There is no account.
- The page talks to nothing but that server, and its content security policy holds it to that.
  Links to GitHub open only when you click them.
- What you write goes to the agent on your machine, which talks to its model as it already does. claude-review
  itself reaches two places: `/review-ui` asks PyPI for the latest release, and feedback you hand to your agent is
  searched for among this project's issues on GitHub.

## Also

- Read the change against a branch, a tag or an earlier round, from the header.
- In Claude Code, review the agent's plan (`/review-ui plan`) or your conversation with it
  (`/review-ui transcript`); from the command line, any files (`claude-review files plan.md api.py`).
- The agent can raise a thread on a line itself, to show where it did something other than what you asked.
- Paste a screenshot into any comment or into the panel; the agent gets a file it can open.
- Keys move you through lines, files and comments; `?` lists them.

Everything it does: [docs/features.md](https://github.com/vrppaul/claude-review/blob/master/docs/features.md).
The command line: [docs/cli.md](https://github.com/vrppaul/claude-review/blob/master/docs/cli.md).

## Feedback

claude-review is open source and nothing here is for sale. Tell me what would make it useful to you.

[Open an issue](https://github.com/vrppaul/claude-review/issues), or press Send feedback under Help (`?`) in a review.
It shows you the issue word for word, with none of your code in it; then you open it on GitHub or hand it to your
agent, which files it once you say so.

To work on claude-review itself, read
[CONTRIBUTING.md](https://github.com/vrppaul/claude-review/blob/master/CONTRIBUTING.md).

## License

[MIT](https://github.com/vrppaul/claude-review/blob/master/LICENSE)
