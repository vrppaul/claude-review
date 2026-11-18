# The command line

`/review-ui` runs these commands for you. You need them to start a review by hand, or to see what the agent does.
Every command takes `--help`.

## Install

With [uv](https://docs.astral.sh/uv/getting-started/installation/):

```bash
uv tool install claude-review
```

It ships as a prebuilt wheel on [PyPI](https://pypi.org/project/claude-review/), so it needs no Node or pnpm.

## Opening a review

```bash
claude-review diff                         # the repository's uncommitted changes, untracked files included
claude-review diff /path/to/repo           # any directory in another repository
claude-review diff --base HEAD~3           # the changes since a commit
claude-review diff --base v0.5.0           # since a tag
claude-review files plan.md                # text files: plans, docs, configs, source code
claude-review files a.md b.py c.rs         # several at once
claude-review transcript conv.jsonl        # a Claude Code conversation
claude-review diff --port 8080             # a port of your choosing; 0 for any free one
claude-review diff --no-open               # print the address instead of opening the browser
claude-review --verbose diff               # diagnostic log on stderr; --verbose goes before the command
claude-review --version                    # the installed version
```

Without `--port`, the port is worked out from what is reviewed, so reopening the same review comes back to the same
address, and to the draft left in it. The review is served on `127.0.0.1` only.

The command runs until the review ends, then prints what you sent to stdout. While no agent calls `wait`, the threads
and the panel say that nobody is there to answer.

## Answering from the review

While a review is open, any comment can carry a question, and the panel carries everything that belongs to no
comment. These commands let the agent that wrote the change be the one that answers. Each takes the review's
`--port`, and each text given as `-` is read from stdin.

```bash
claude-review wait --port 8765 --until-event                          # wait for a question, a message or a round
claude-review reply --port 8765 --thread <id> --question <id> "..."   # answer in a thread
claude-review say --port 8765 --message <id> "..."                    # answer in the panel
claude-review say --port 8765 "..."                                   # speak first
claude-review status --port 8765 --model opus-5 --context "53% of 1M" # what only the agent knows
claude-review point --port 8765 --file a.py --lines 42-47 "..."       # raise a thread on a line
claude-review progress --port 8765 --message <id> --file a.py "..."   # what the agent is doing now
claude-review progress --port 8765 --done                             # the work is finished
claude-review show --port 8765 --file a.py                            # take the reader to a file
claude-review catch-up --port 8765                                    # catch up on a review under way
claude-review retake --port 8765                                      # take the diff again after a round
claude-review story --port 8765 --file story.json                     # tell the change as a story
```

`wait` prints one JSON object and exits: a question, a panel message, a round, a request for a story, something taken
back, `{"type":"closed"}` once the review is over, or `{"type":"timeout"}` when nothing was said. With
`--until-event` it waits on through the timeouts, so it can be driven from a loop.
[The skill](../skills/review-ui/SKILL.md) documents the loop, and `claude-review story --help` shows a story's whole
document.
