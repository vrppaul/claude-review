# Stories

For whoever works on stories in claude-review: what a story is for, who
reads one and how, why the agent is advised as it is, and the decisions
behind it. What the agent is told is `src/claude_review/cli/good_story.md`;
how each part is built is said in its module (see "Where it lives").

## What a story is

A second way to read the same diff. The agent that made the change tells
it: an overview (what was asked, what was done, what to doubt), then
chapters, each a run of steps, each step a piece of one file with the
agent's reason above it. Threads, drafts and rounds are shared with the
Files view, and a story is always of the review's whole diff.

Tools that write a walkthrough of a pull request work it out from the diff
after the fact. Here the agent that made the change tells it: it knows why
each piece is as it is, and it stays to answer questions in threads.

## Who reads it, and what they need

The reader sees someone else's change for the first time and must judge
it: is it what was asked, is it right, was there a better way.

- Review tools list files alphabetically, which leaves the reader to work
  out how the parts connect (Baum 2017). That work takes the attention the
  judging needs.
- Attention fades down the list. Files shown earlier get more comments, and
  in an experiment one kind of defect had 64% lower odds of being found
  when its file came last rather than first (Fregnan 2022).
- Reviewers need to know whether another way would be better and whether
  they understood the change right (Pascarella 2018, as summarised in
  arXiv 2307.14406).

So the story does the connecting, and the reader's care goes to judging.
Its risk is the reverse: a story told well persuades, and a reader told
why first tends to accept how. Hence the bar every story is held to: easy
to check, not easy to believe.

## How the reader reads it

1. The overview at a glance: what was asked, what is done, what to doubt.
   The diagram's heart says where to read slowly.
2. The contents: chapter titles that tell the change in brief, each with
   its files and their counts.
3. The chapters one after another in one scroll, each a whole part, each
   reason above the code it explains.
4. Any block of the agent's words can be asked about, and the agent
   answers in its thread.
5. After a round, a step whose code changed is marked, and the agent tells
   the story again, whole.

## Why the advice says what it says

Each rule of `good_story.md`, and what it rests on.

- **The task first, then what is done.** Reviewers want the requirement
  first, then an overview (Baum 2017, on how a review starts).
- **A chapter is one idea, not a file or a layer.** A good order is mostly
  a good grouping: "group related change parts as closely as possible"
  (Baum, principle 1). A change made of several is understood best split
  by issue (Tao 2012). So a file may stand in two chapters.
- **A title says what the chapter achieves.** Reviewers follow an order
  whose rule they can see: "make the grouping explicit to the reviewer"
  (Baum, principle 6); one of its interviewees asked for the groups to be
  "made visible and ideally given sensible names".
- **Each chapter needs only what came before it.** "Provide information
  before it is needed" (Baum, principle 2), and where that conflicts with
  grouping, grouping wins (principle 3). Which way to go along calls is
  taste: Baum's interviewees leaned top-down and 85% of its survey
  bottom-up. So the advice names the way the data takes, not a direction.
- **Where to read slowly is pointed at, not put first.** The order is
  spent on understanding, and what comes last gets less care (Fregnan
  2022), so the overview's doubt and the diagram's heart point at it from
  the top.
- **A reason says why, never what.** The code shows what; why is what the
  diff does not carry. A step with no reason then tells the reader there
  is nothing to look for, which holds only while reasons are never filler.
- **Decisions and ways turned down, each with its reason**, answer "would
  another way be better" before it is asked. **What is left for later** is
  not reported as missed: changes split by concern drew fewer wrongly
  reported issues (Di Biase 2019).
- **A doubt the reader can check** is the counterweight to persuasion: a
  known risk, or behaviour the reader may not want, and where it is.
- **A test stands in the chapter of the behaviour it holds**: related parts
  stand together, and the closest two parts can be is "visible on the
  screen at the same time" (Baum, principle 5). Reviewers often start from
  the tests (Bouraffa 2025), and a chapter of tests at the end would put
  them where attention is lowest. Changed or
  removed assertions are named, as that is where a test may have been bent
  to fit the code. Decided 2026-10-14; the first design had a chapter of
  tests last.
- **A diagram only for a way of three parts or more, with one heart**: the
  diagram gives the change's shape, the chapters its order (prlens).
- **Nothing hidden.** Every changed line is in a step, in housekeeping or
  under "Not in the story". Without this a story is advertising.
- **Plain text, no praise.** The page shows texts as written, and praise is
  a claim the reader cannot check.
- **The language the agent speaks with the user**: a story is prose for
  that person. The page's own labels stay as they are. Decided 2026-10-14.

## Decisions, and why

- **Asked first, for each review.** A story spends the agent's tokens, so
  the reader is told the cost and asked before a review's story is
  written, until they choose to be asked no more. Decided 2026-10-23.
- **Short first.** Each kind of text has a length limit in the data
  (`TEXT_LIMITS`), and a text over it is refused with where the rest
  belongs, so shortness does not rest on goodwill.
- **Complete by lines, not hunks.** A step may be part of a hunk, so what a
  story covers is counted in changed lines.
- **The reader is never moved.** A story that arrives is offered, never
  put on screen by itself.
- **A reconstruction says so.** A story told from commits, by an agent that
  did not make the change, is marked "reconstructed" on the page.
- **Followed by what git says changed.** On a later take of the change, a
  step follows its code through the diff from the take it was told of to
  this one: a line kept moves as the lines above it moved, and a line the
  round rewrote stays the step's, so the step shows it as it now stands,
  marked changed. Found by its text, as a thread is, a step lost a
  reworded line and could land on another function's `}`. Where two
  steps' lines were rewritten in one block, the block is the upper step's.
  A step whose lines are all gone, or whose take git never wrote down,
  stands nowhere. Decided 2026-10-14; threads still follow by text.
- **The advice ships with the command, not in the skill.** The skill ships
  twice, as a folder (`npx skills add`) and as one file (the plugin's
  command), and the command line is installed apart from both. Only the
  command is sure to be the version that checks the story, so
  `claude-review story --help` prints the advice, and the skill names the
  help.

## Where it lives

- What the agent is told: `src/claude_review/cli/good_story.md`, the
  example and the limits in `src/claude_review/cli/story_help.py`, and the
  events in `skills/review-ui/SKILL.md`.
- The document and what it is held to: `src/claude_review/domain/story.py`,
  `src/claude_review/services/story_checks.py`.
- A story told on the change and followed onto later takes:
  `src/claude_review/services/story_telling.py`, `story_slices.py` beside
  it, `anchor_service.py` for the threads.
- The page: `frontend/src/lib/components/Story*.svelte`, with
  `frontend/src/lib/review/review-story.svelte.ts` holding the story.

## Sources

- Baum, Schneider, Bacchelli. [On the Optimal Order of Reading Source Code
  Changes for Review](http://tobiasbaum.github.io/rp/optimalordering.pdf),
  ICSME 2017. Interviews and an online survey; six principles of a good
  order, and how reviewers start and end a review.
- Fregnan, Braz, D'Ambros, Çalıklı, Bacchelli. [First Come First Served:
  The Impact of File Position on Code
  Review](https://arxiv.org/abs/2208.04259), ESEC/FSE 2022. 219,476 pull
  requests and an experiment with 106 participants.
- Tao, Dang, Xie, Zhang, Kim. [How Do Software Engineers Understand Code
  Changes?](https://www.microsoft.com/en-us/research/publication/how-do-software-engineers-understand-code-changes-an-exploratory-study-in-industry/),
  FSE 2012. Engineers at Microsoft: a change made of several is
  understood best split by issue.
- Pascarella, Spadini, Palomba, Bruntink, Bacchelli. [Information Needs in
  Contemporary Code
  Review](https://research.tudelft.nl/en/publications/information-needs-in-contemporary-code-review),
  CSCW 2018. Seven needs, from 900 review comments; the summary of which
  matter most is from [arXiv 2307.14406](https://arxiv.org/pdf/2307.14406).
- di Biase, Bruntink, van Deursen, Bacchelli. [The effects of change
  decomposition on code review](https://peerj.com/articles/cs-193/), PeerJ
  Computer Science 2019. 28 developers: changes split by concern drew
  fewer wrongly reported issues, with no change in defects found.
- Bouraffa, Brandt, Zaidman, Maalej. [Not One to Rule Them All: Mining
  Meaningful Code Review Orders From
  GitHub](https://arxiv.org/pdf/2506.10654), EASE 2025. 23,241 pull
  requests: 44.6% were not commented on in alphabetical order, and of
  those that changed both code and tests, 29% were read tests first.
- [Agent pull requests lose the
  narrative](https://prlens.dev/guides/agent-prs-lose-the-narrative),
  prlens. Why an agent's pull request comes without an order, and what
  restores it: a shape and an order.
