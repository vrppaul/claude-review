---
name: handover
description: Write a handover for the next agent in the project's memory, so it knows what to do, why, how and where the owner's word is still needed; then have a cheap model check every claim in it. Use when the owner asks for a handover, or when a session nears the end of its context with work open.
---

# Handover

A handover is what the next agent cannot learn from the code, git, the rule
files or the memory index: the owner's intent, the reasons behind what was
built, what was turned down, the state of the world, the traps met, and
where the owner's word is still needed. Everything else it only points at.

It is written for an agent that will be responsible for what it does next.
So it is a set of claims to check, not proof, and it says so to its reader.

## Where it goes

- In memory, never in the repository: the project's memory directory under
  `~/.claude/projects/`, file `project_handover.md`.
- A new block at the top, headed `## 0-<NAME>, session <id> (<date>, <UTC
  window>). READ THIS FIRST; every block below is history`. Mark the block
  that was first until now as history.
- Update the file's frontmatter `description` (it is what loads in every
  session) and the handover's line in `MEMORY.md`, both naming the new
  block and HEAD.
- A correction from the owner that must hold from now on goes to a feedback
  memory of its own, not to the handover: the handover goes stale when its
  work is done, a rule must not.

## 1. Gather the facts, by commands only

Every fact in the block is read off a command run now, never recalled:

- branch, HEAD, and what is pushed: compare with every remote branch it
  could be on (`git log --oneline -1 origin/<branch>`, `git rev-list
  --count origin/<branch>..HEAD`);
- what is uncommitted, and whose it is (`git status --short`, `git diff
  <file>`): lines the owner keeps uncommitted are named as theirs;
- the last runs of each suite, with the counts read from their output, and
  the commit they ran at; what no run has checked is said as such;
- what is still running: servers, worktrees, background agents.

## 2. The owner's words, verbatim

Find the session's transcript (`~/.claude/projects/<project>/<session>.jsonl`)
and take every message the owner wrote this session: the entries of type
`user`, and `queue-operation` for what they sent while a turn ran. Search it
with `grep` or a short script that reads it line by line; never print it
whole. Quote each message word for word, with its UTC time, and after it one
line of what was answered or done. Mark plainly what the owner approved and
what they have not said yes to yet.

Words of an earlier session that the work rests on are quoted the same way,
with that session's id and where they stand in its transcript.

## 3. Write the block

In this order, each part short; a part with nothing to say is left out.

1. **Before your first answer.** The transcript's path, and: read the quoted
   words there before answering "what next"; never answer it from this block
   alone.
2. **You are responsible for what you do next.** This block is a set of
   claims. Before your first step, check what you will build on, cheaply:
   `git status` and `git log`; that a file, a name or a test it names
   exists; the owner's words in the transcript. Where the block and git or
   the code differ, git and the code win: say so. A reading of the owner's
   words this block calls unconfirmed is a question, not a decision. Do not
   run whole suites to check the block: the counts below stand until you
   change their code. Run the tests of the part you touch, as the project's
   rule on test runs says.
3. **State, checked at <UTC time>.** The facts of step 1.
4. **The owner's words.** Step 2.
5. **Done.** Each piece by commit, and for each: what it did; why — the
   owner's motive in their words; why this construction; what was turned
   down and why, so nobody improves it back; how it was checked (a test seen
   failing, a reviewer, a run with its count), or that nothing checked it.
6. **Readings the owner has not confirmed**, each with what it rests on.
7. **What the owner will see changed.**
8. **Next.** What waits for the owner's word, and what does not. For each
   step, the approved line it carries out, and the sources to read for it —
   memory files by `[[name]]`, TODO sections, files. Never a plan retold with
   a construction the owner did not approve.
9. **Other open work**: everything left or deferred, written also where its
   doer reads it (the project's TODO), with why it is left and whose
   decision it waits on.
10. **Traps met**: what cost time and is in no file — a tool that lies, a
    command that needs a flag, a gate that sees more than it seems to.
11. **How the work was done**, where it should go on that way: the cycle of a
    piece, its reviews, how commits are made.

Point at rules, never retell them. Write it as an index: the next agent
reads the block, then only what its next step names.

## 4. Have it checked

Start a subagent on the cheapest model (Haiku), read-only, with this brief,
filling in the paths:

> You check a handover note against the facts. You change nothing: read
> only. Spawn no subagents. Run no test suite and no build: where the note
> gives a test count, say "not checked by a run" unless something you can
> read contradicts it.
>
> The note: the block `<heading>` at the top of `<memory>/project_handover.md`,
> its frontmatter `description`, and its line in `<memory>/MEMORY.md`. The
> repository: `<repo>`. The transcript it quotes: `<transcript>` — large;
> search it with grep or a short script, print only short excerpts.
>
> Check every factual claim by a command: branch, HEAD, what is pushed and
> what is not; uncommitted files; each commit named exists and does what the
> note says; each file, name, setting and test it names exists; each quote
> of the owner stands word for word in an entry of type `user` or
> `queue-operation` at the time given, to the minute; each `[[name]]` is a
> memory file whose frontmatter `name` matches; each item called open is
> still open where the note says it is.
>
> Then read the block as an agent that knows nothing else would, and say
> what it lacks to know what to do first, why, where the owner's word is
> still needed, and how it would check its own work; and where it can be
> read two ways.
>
> Report, at most 40 lines: each claim, OK or WRONG with what you found;
> then what is missing or unclear. Facts only.

Why a separate model: the writer believes its own block. Why the cheapest:
the check is reading and searching, not judgement, and it must not cost the
owner a heavy model's quota.

## 5. Fix, then report

Correct every WRONG, close every gap the check found that a next agent
would need, and fix the repository where the check finds it disagrees with
itself (a CHANGELOG line the code contradicts). Then tell the owner, in a
few lines: where the block is, what the check found and what you changed.
