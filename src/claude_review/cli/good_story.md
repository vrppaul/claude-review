# What makes a story good

A story is for a person who reads this change for the first time and must
judge it: is it what was asked, is it right, was there a better way. Your
order and grouping spare them piecing the change together, so their care
goes to judging it. A story told well also persuades: tell one that is
easy to check, not easy to believe.

Tell it in the language you speak with the user. The page shows every
text as it is written: no Markdown, no backticks.

## The overview

- task: what was asked, in the user's words.
- done: what is true now, as the reader can check it. Say what of the task
  is not done, here or in later.
- doubt: the one thing most worth checking, and where it is: a known risk,
  or behaviour the reader may not want. Never "edge cases may be missed",
  never a question you could answer yourself. If there is none, leave it
  out.
- decisions: each choice a reader might question, with its reason.
- turned_down: each way you did not take, and why, so "why not just…?" is
  answered before it is asked.
- later: what is left undone on purpose, so nobody reports it as missed.
- diagram: only where the change has a way through three parts or more.
  Each node leads to the chapter that tells it. Mark as the heart, with
  :::heart, the one node where the main decision lives: where to read
  slowly.

## Chapters

- A chapter is one idea: the pieces that change together, in whatever
  files and layers they are. A file may stand in two chapters.
- Its title says what the chapter achieves, so the titles alone tell the
  change in brief.
- Order the chapters so each needs only what came before it: along the
  way the data takes. Where order and grouping disagree, keep the group
  whole.
- Order is for understanding, so point at what to read slowly from the
  top instead: the overview's doubt and the diagram's heart. What comes
  last is read with less care, and a pointer from the top still reaches it.
- why: why these pieces belong together and why they are built this way,
  never what each one does.
- doubt: where this chapter is likeliest to be wrong, naming the step. If
  there is none, leave it out.
- A test stands in the chapter of the behaviour it holds. A chapter of
  tests is only for what several chapters share. Name every assertion the
  change altered or removed: that is where a test may have been bent to
  fit the code.
- A small change is a short story: one chapter, no diagram.

## Steps

- A step is one piece of one file. Split a long hunk where its ideas part,
  and give a long run of boilerplate a step of its own.
- Within a chapter, a step that defines comes before the steps that use it.
- reason: why this piece is the way it is: the limit it keeps to, the rule
  it holds, what would break otherwise. Never what it does: the code under
  it shows that. A step with nothing to explain has no reason, which tells
  the reader there is nothing to look for there.

## Nothing hidden

- Every changed line is in a step or in housekeeping. The reader sees any
  other under "Not in the story": a good story leaves nothing there.
- housekeeping is for files nobody reads, such as lock files and generated
  ones. Never code.
- told_from is commits when you did not make the change in this session,
  or no longer remember why it is as it is: the page then shows the story
  as your reading of it, not as what was decided.
- No praise, such as "clean" or "robust": say what the reader can check.
