# Changelog

## [Unreleased]

### Added
- **A story's diagram is drawn.** The diagram the agent writes in Mermaid
  stands under the overview's lines, under its caption, fitted to the
  column where it is wider, never drawn larger than its size; its nodes have
  the page's rounded corners, and the lines between them are drawn twice as
  wide as a node's edge. A screen reader names it by its caption, or "The
  change drawn" where the agent gave none. The node the
  agent marks as the heart of the change, with mermaid's `:::heart` as the
  example in `claude-review story --help` does, is edged in the agent's
  colour. A node the agent links to a chapter takes the reader to it when
  pressed, and "Open large" draws it again at its own size in a dialog
  headed by its caption, with a button that closes it, where a press on a
  node closes the dialog first. One that does not draw says why, by the line and the
  text mermaid did not expect there, and shows its source as written.
  Mermaid is fetched only when a story has a diagram to draw, and a source's
  own settings cannot change how safely, in what look or in what layout it
  is drawn. It is drawn once: the story comes back on screen with it
  standing drawn.
- **The reader asks about the story's own words.** Pointed at, or reached
  by the keyboard, every block of the agent's words — the Task, Done and
  Doubt of the overview, each thing its lists hold, a chapter's Why and
  Doubt, a step's reason — is banded and offers "Ask about
  this", floating over the block's top edge so no word moves, its end where
  the block's words end; a screen
  reader names each by its place, "Ask about this: Story · Doubt", "Ask
  about this: ch-2 · Why", so no two chapters' offers sound alike. The
  agent points at lines alone: a block of the story it names is refused.
  The comment is
  written under the block, inviting "Ask about this…", with Ask, Save and
  Cancel as on a line of code, and its thread hangs there, the block banded
  stronger meanwhile: below the frame of a chapter's Why, the warning of
  its Doubt, or a step's reason, never inside it. The overview's
  lists, under "More about this change", stand open whenever a thread or a
  comment hangs under anything they hold, and fold away only once none does.
  The replies, the finish pane and the panel name it `Story · Doubt`;
  picked there, it brings the story on screen with the keyboard on the
  thread, as a thread on lines does; and `n` and `p` walk
  the story's threads in the order it says what they hang on. A blue dot
  marks the contents' row of a part a thread hangs in, and its name says
  how many. The agent is handed the words with the question. When the
  agent tells the story again, each thread follows the words it was
  written on to the block that says them now; where none does, it stays
  under its block, outdated, or stands at the head of the story when the
  story no longer has that block, and `n` takes the reader there first.
  Either way it shows the words it was written against, wrapped as the
  story said them. A review that picks up such threads from an unsent
  draft before any story is told stands them there too, above what the
  reader waits on.
- **The reader asks the agent for a story of the change, and sees it being
  written.** A story is the change told by the agent that made it: a short
  overview, then chapters with its reason above each piece of code. Story in
  the header asks before the first one is written, since a story spends the
  agent's tokens, and says what this review would cost; the choice is kept
  behind the gear for every review. Where the story will be, the page says
  when it was asked for, when the agent took the request and how long it has
  been waited for, with the files to read meanwhile and a way to stop and to
  ask again. While the files are read the switch says the story is being
  written, and offers it once it has arrived, in a note that goes by itself
  after four seconds, a bar running out as it waits, or at once by its ×:
  the view never changes by itself. With no agent attached the page says
  how one is attached, and offers the files meanwhile.
- **Story is introduced once: by this release's news, or at the switch.**
  A reader back from an older release is told of Story on the news card,
  with the sketch and Try Story in place of Got it (Got it where the
  review tells no story); once shown, the card was the introduction. A
  reader who has never tried Story, by pressing it or by having a story
  on screen, and is shown no such card meets, once the welcome card and
  the tour are done, a pane under the switch pointing at Story, which is
  ringed in the agent's colour: what a story is, sketched, and what it
  spends, with Try Story and Don't show again. Try Story, on the card or
  the pane, does what Story in the header does, asking first while
  stories are off; the cross puts the pane away for this review alone;
  Don't show again puts it away in every review, and a note in its place
  says so for four seconds, fading, with Undo for a slip. A story's
  arrival, offered under the switch, stands there first, and the keyboard
  the pane held goes to Story. Story pressed, or a story on screen,
  before the review has heard whether it was introduced is kept all the
  same.
- **Every review knows whether Story was introduced to the reader.**
  `GET /api/guide` says `story_introduced` beside the release last shown,
  false for a reader shown around by a release before stories; `PUT
  /api/guide` takes either fact alone and keeps the other as it was.
- **A story, sketched.** The question asked before stories are turned on
  shows what a story is in the review's own colours, without a word: the
  contents on their axis, a chapter read and the one being read with its
  files, beside the overview with its doubt, a diagram, and a step's reason
  over its code. Where a story is being written the same sketch stands
  greyed over the wait, what the agent writes first pulsing in its colour,
  and standing still for a reader who asked for less motion.
- **The agent is told when a story is wanted, and how one is written.**
  `wait` hands over `story_request` and `story_cancel`; `claude-review story
  --help` shows the document whole and says how long each of its texts may
  be; the skill says what to do at each.
- **The agent is told what makes a story good.** `claude-review story
  --help` ends with it, written for the person who reads the story: a
  chapter is one idea, not a file, and its title alone tells it; each
  chapter needs only what came before it; a reason says why, never what; a
  doubt is one the reader can check; a test stands in the chapter of what it
  holds, every assertion the change altered named; and the story is told in
  the language the agent speaks with the user. Its example is a story told
  so, of the change that let a reader paste a screenshot.
- **A comment being written is never lost.** What is typed and pasted into a
  new comment, a reply or an edit is kept by the review, not by the box that
  shows it: folding the file or the thread, switching to two columns and
  back, or reloading the page brings it back as it was, without taking the
  cursor. Several comments can be started in one file, each on its own lines,
  as on GitHub; picking lines that already have one brings that one back.
- **Context opens up or down by twenty lines, or all at once, and below the
  last change.** Each gap between hunks offers ↑ 20, ↓ 20 and "Show all", as
  GitHub does, and a file's end has a gap of its own. A gap longer than the
  server hands back in one read offers "Show N" in place of "Show all", N
  lines a press.
- **The page says when its review cannot be reached.** A bar under the
  header says it is trying again and that nothing is sent until the review
  is back; Send, End and the panel wait meanwhile. A request nothing
  answered says so in words, once.
- **Words being typed and a thread are never dropped without asking.**
  Escape or Cancel on a comment that holds something, and Delete on a
  thread, ask first, in a small pane by the control that asked — over
  Cancel, under the bin — with the safe answer holding the keyboard. The
  rest of the page stays to be pressed, and a press anywhere else puts the
  question away.
- **A moved file says where it was** — "old → new" in the tree and over the
  file — and a file that became a link says "file → link".
- **A question asked in a thread can be taken back**, as a panel message
  can; the panel's "Stop" now reads "Take back". Once the agent has stopped
  listening, one set of words says so.
- **A screen reader finds the diff, each file, each thread and what the
  agent says**: the diff is the page's main part, each file and thread is
  named, the panel's turns are a log, new answers are said as they arrive,
  and the column grips are window splitters.
- **The agent's `@path:12-39` in the panel is a chip**, as a reader's is.
- **What the agent says can be piped in.** `say`, `reply`, `point` and
  `progress` read their text from stdin given `-`, and the skill hands it
  over from a quoted heredoc, so backticks and `$` in an answer stay as
  written rather than being run by the shell.
- **A thread read in full lists its images as files to open**
  (`catch-up --thread`).
- **`GET /api/threads`** says the threads the review holds; a page that
  opens with no draft of its own starts from them.
- **`GET /api/conversation`** says what was said in the panel, oldest first,
  each part under the id every page knows it by; the `chat` push carries
  that id as `said_id`.

### Changed
- **Tests hold what someone can name, and run when their part changed.**
  A test is written for a behaviour — what the command line prints or
  refuses, what a route answers, what the reader sees or where the keyboard
  lands — once, at the cheapest level that sees it; never for a look, a
  declaration or internals (`.claude/rules/tests.md`). About a thousand
  cases that held none went. A test does one thing and checks what came of
  it, never how it looks: a browser test asks what is in view, what a press
  reached, or how far an area scrolled, and a commit refuses one that reads
  a box, a size or a style. `uv run pytest` leaves the API
  schema's fuzzing out unless asked for with `-m schema`; `scripts/look.py`
  only serves a long change and its story, for whoever looks at the page.
- **One set of buttons across the page.** Every button is one of a few
  tones at one of two heights: primary, the one act a pane or a card leads
  to; quiet, an act that must not outweigh the words beside it; secondary,
  edged on the page's own ground, an act on what is read — a thread's
  Resolve and Reopen, "Ask about this", Ask now, Take back; danger, the
  same in the colour of what destroys — the bin and Delete; and the
  reader's own, on their mark's tint — the base picker while it narrows
  the diff, and "changed since round N". 24 pixels among words, 32 where a
  pane, a card or a bar ends. A button that is an icon alone says what it
  does under the pointer. Each lights the same way under the pointer in
  both themes, the primary a little more so its blue shows it too; one
  that cannot be pressed keeps its ground and steps back to muted words,
  the primary on a surface's grey. A thread's buttons stand 24 pixels tall
  with a field's corners, where they stood 26 with a box's; every × is the
  cross the rest of the page draws; "Skip tour" and the release's link are
  links, in the colour of the reader's controls. A track of segments — how
  the review is read, the diff's layout, the theme, what a comment asks
  for — stands 24 pixels tall, level with the buttons beside it, where it
  stood 26.5.
- **A rule for the page's parts: every kind comes from its library.**
  `.claude/rules/page.md` says each kind of element the page draws — a
  button, a field, a pane, a notice, a mark, a list's row — is a part of
  `frontend/src/lib/ui/`, and a kind the library lacks is added there
  first, with a rule in eslint that refuses it anywhere else. Two rules it
  held that eslint and stylelint hold whole, no `style="…"` or `z-` utility
  in markup and what scrolls being a `cr-scroller`, are left to them.
- **One look for every field.** The field a comment is written in had
  DaisyUI's room and corner, the summary and a message to the agent their
  own; all three now stand alike, and a message stands as tall as the
  summary before anything is written in it. The two filters, which stood
  on two grounds, stand on none, edged in the reader's mark as the fields
  to write in are. The field a reply is begun in, a surface's grey edge,
  is edged as the field it opens, in the agent's colour in a thread the
  agent raised, and lit under the pointer as whatever can be pressed is;
  the avatar beside it stands at the top of its row, as every speaker's
  does. The settings' checkboxes are the browser's own, in the colour of
  the reader's controls, each named by its words. Fields, filters and
  checkboxes are parts of the library, and eslint refuses an `<input>`, a
  `<textarea>`, a `<select>`, an element given a field's role or one made
  editable anywhere else.
- **One look for what is on its way, for what failed, and for nothing.**
  Whatever is on its way — the review opening, a review being sent, an
  image uploading, an answer, the agent at work, a story being written —
  breathes as three dots, where the page drew DaisyUI's spinner at two
  sizes beside its own dots. Why something could not be done is said in
  small words in the colour of what fails, in one form wherever it is said,
  where it stood in five forms at three sizes; a review that cannot be
  opened says so the same way, where DaisyUI's alert said it. A list or a
  view with nothing in it — the replies, the tree, the bases, the diff, a
  file, the panel — says so in muted words in the middle of its room, at a
  list's size in a list and a view's in a view, where it stood in five
  forms. An icon that says something by its colour — a check of something
  done, the bin, the agent's book, a warning, the base in force, the
  panel's empty mark — takes it from its tone. The library draws each of
  these. eslint refuses a class of any of DaisyUI's components anywhere,
  and the colour of what fails outside the library, as stylelint does in
  every stylesheet but the library's.
- **The pane a control opens, its question and its note are the
  library's.** Popover, the question asked before something is lost, the
  note put by a control, a fold's toggle and a column's grip moved into
  `frontend/src/lib/ui/`, which builds on nothing of the page. Every name
  the tour lights a place by is written through `tourStop`, which holds it
  to the tour's stops, or handed to a component whose prop is typed so:
  two of the eleven written were held before, and eslint refuses one
  written bare.
- **One column and one bar.** The tree of files, a story's contents and
  the agent's panel stand in one column of the library: as wide as the
  reader left it, sized by its grip on the edge facing what is read, on
  the page's own ground, and lying over what is read on a screen too
  narrow to keep it beside; the panel's field to write in stands at its
  foot. The review's header, a file's and a story piece's, and a column's
  are one bar, at its room for each; a file's bar steps back once the file
  is viewed. eslint refuses a raised ground ruled off above or below
  drawn outside the library.
- **Images, links and a file's letter are the library's.** An image pasted
  into what is said is one thumbnail, uploading, lost or shown, which
  opens at its full size or is taken off by its cross; the news's picture
  is a picture of the library's. A link in words written in Markdown takes
  the library's link: the reader's control colour at the weight of its
  line, underlined under the pointer, where the typography plugin drew it
  underlined and heavier. What became of a file is its letter of the
  library's. eslint refuses an `<img>` or an `<a>` drawn outside it. A
  turn's avatar stays the thread's own drawing: the turn and the thread's
  spine are laid out from its size.
- **Every size is taken off one scale.** Room between things is one of
  nine steps from 0 to 32 pixels, words one of a few sizes in two weights
  at their size's own leading, a line 1 or 2 pixels, a corner a field's or
  a box's. What moves, in a thread: who said a turn is named at its head's
  size, 12 pixels, where it was 13, and what was said stands 4 pixels under
  it, where it stood 3; the field to reply in has the corner of the field
  it opens, 4 pixels, where it had 6. In the panel: the agent's branches of
  work are listed at 12 pixels, where they were 13, a pixel further apart,
  on a 1 pixel rail a pixel further in, where it was 1.5; the line of what it is doing stands 20 pixels tall,
  where it stood 21; an answer stays marked 2 seconds as it lands, where it
  stayed 1.8; an image still uploading says so at 11 pixels, where it said
  it at 10; the words of an empty panel take 20 pixels a line, where they
  took 22.75. In a story: its chapters stand 12 pixels apart in its
  contents, where they stood 10, their numbers at 11 pixels, where they
  were 10; what it leaves out is headed at a chapter's size, 18 pixels,
  where it was 16; the overview's Task and Done are headed in bold, as its
  lists are, and all three heads sit on the line of their words, 6 pixels
  lower than they stood; Story's introduction takes 20 pixels a line,
  where it took 22.75; Story's question stands its parts 12 pixels apart, where they
  stood 14, and its buttons 8, where they stood 10; its introduction, the
  facts and buttons of its waiting room and a diagram stand theirs 8
  pixels apart, where they stood 10, and the waiting room its column 24,
  where it stood 22; a fact of a story on its way stands its mark in a
  column as wide as the mark, 14 pixels, where it was 18; the sketch and
  the news's drawing stand what they hold 12 pixels in, where they stood
  10. Elsewhere: the guide's card speaks at 14 pixels, where it spoke at
  13, its parts 8 pixels apart, where they stood 10, and "Also in this
  release" 12 pixels under its rule, where it stood 10; the settings stand
  their parts 8 pixels apart, where they stood 10; Help's keys stand 16
  pixels under its rows, where they stood 20; a passing note stands its
  words 12 pixels in from its left edge and 8 from its right, where they
  stood 14 and 10; a segment of a track stands its words 8 pixels in from
  either side, where they stood 10, its corner 2 pixels, where it was 3.
- **A story follows its code when the diff is taken again.** Each step
  follows its lines through what git says changed between the take it was
  told of and this one: a line kept moves as the lines above it moved, a
  line the round rewrote stays the step's, and where one block the round
  rewrote held lines of two steps, it is the upper step's. The step is cut
  again from the take as it now stands, and what the round added that no
  step tells is left out beside it. Each step of `GET /api/story` says
  where its code stands now, `now`: the lines it stands at, the piece they
  are and whether a round changed it since it was told
  (`changed_since_told`), or `null` where the review cannot place its code
  in the change now — its file left it, all its lines are gone, or git
  could not say what changed since. A step's own `lines` stay the lines it was
  told on: the page knows its place by them and a thread on its reason its
  block, so neither moves with its code, and a step that stands nowhere
  claims no line another step's code has moved to. Such a step shows no
  code, never other code at its old numbers: its number and its reason,
  still open to a question, and one
  line, "Its code in app.py is no longer found.", where its number stands; it counts as no file of
  its chapter, whose head then counts only its steps, and the agent asked
  for the story again is told it with `lines` `null`. Every told step says
  whether a thread may name its file (`commentable`). The
  story is always followed from the story as told, so code put back reads
  as told again. It is still the story of the round it was told in;
  `moved_on` says the round a take first found the code moved on in, which
  later takes keep while it stays so, and, where the round changed them,
  how many changed lines no step told when it was told and how many none
  tells now (`left_out`, else `null`). Each chapter says how many of its
  steps show code changed since they were told (`changed_steps`), so the
  page counts nothing; the round is the story's alone. The page reads the
  story again with the diff, and holds neither until both are read,
  keeping what was read of it: its lines are the code under review, and
  take comments. A
  story it could not read with the diff is drawn no more until the next is
  read, and the panel says why; one read of a take the page has not taken
  in yet is drawn once that take's diff is.
  A step whose code changed
  shows it as it now stands under a number and reason that step back, and
  is named "Step 2.2, changed after it was told"; its chapter says first,
  in the frame of its doubt, "Changed after it was told. 3 steps in this
  chapter changed. The code below is current; the reasons
  beside it may not be."; and its node in the contents rings its number
  in the warning's colour, in place of the check of a chapter read
  through, which it still is. The round the story was told in is a tag
  beside its title, "Round 1" and a green dot with "current" on the
  agent's colour, and once a later round moved the code on, "Round 1 the
  code moved on in round 2" on the warning's; the contents then say
  beside "Not in the story" how many changed lines no step told when it
  was told, and how many none tells now, "2 → 5", where the two differ,
  said in words to a screen reader. Where the reader turned stories on, the
  review asks for a story itself, whatever pages are open: as it opens,
  as stories are turned on, and again once a retake leaves the story held
  stale, never over one the reader stopped; the agent is handed it once
  nothing the reader said is left for it. While the files are read the
  header says "Story · writing", the warning ends "The agent is updating
  them." while
  it is so, and turning stories off in the gear stops it. The agent's
  `story_request` carries `stale`, `null` for a first story: the round,
  each changed step's chapter, file and lines as they now stand
  ("104-131"), and how many changed lines no step tells, read as the agent
  takes the request.
- **A thread is one card under what it is about.** It hangs right under
  its line, as wide as the line less a little at each side, lifted off it
  and pointing up at it with a tail; one at the head of a file, the diff or
  the story has nothing above it to point at, and no tail. Its edge says
  where it stands: in the reader's colour while it is theirs, faint once
  what it was written on is gone, quieter once it went out with a round,
  and in the agent's colour when the agent raised it. Inside, it reads as
  a conversation, a turn to a row: the avatar of who said it, "You" or
  "Agent", and how long ago, "2m ago" or "answered 40s ago", the avatars
  joined down the card by a thin line. A comment nobody has answered says
  who wrote it too; an answer still awaited is the agent's turn; the last
  turn is the field to reply in, "Reply…". The head of the first turn
  says, after who and when, the place the thread hangs on, quietly, what
  it asks for, whether it is outdated, resolved or has a new reply, and
  "sent · round N" or "from the agent"; at its far end, always at full
  strength, Resolve with a tick, then a pencil to edit, a bin to delete in
  the colour of what destroys, as Delete is in the question it asks, and
  a chevron to fold, which stays where it was on the folded line, as wide
  as the card. Whatever folds on the page — a thread, a file's lines, a
  folder of the tree, what more a story's overview lists, housekeeping —
  folds under one chevron at the far end of its line, pointing up while
  open and down while folded away. A comment being written is that card already, where it
  will stand and as wide, and "Ask about this" looks the same in a card
  as over the story's words. Under that head an outdated thread shows what it
  was written against, then its words. While a thread is open, the lines
  it is about are drawn marked, and a block of the story's words it hangs
  on banded stronger; folded away, it leaves them as they were. A thread
  on the story's words, or a comment being written there, hangs under
  their band as one hangs under a line, as far in from each side, its
  tail pointing up at what the block is headed with.
- **A story's chapter goes by an id a thread can name.** `story` refuses a
  chapter's id that holds anything but letters, digits, dots, dashes and
  underscores, or runs past 200 of them, at `chapters.N.id`, and `story
  --help` says so: a question about what a chapter says names it by its id.
- **Every menu is one kind of pane, with an arrow pointing at what opened
  it**: the list of bases, the settings, the replies, the pane the review
  is finished from, and the @-picker in the agent panel. Opened, it takes
  the keyboard; Escape closes it and gives the keyboard back to its button;
  a press anywhere else closes it and still lands where it was aimed. The
  pane the review is finished from no longer lays an invisible layer over
  the page that swallowed the click closing it. Every pane — these, Help,
  Story's introduction and the notes under the switch, the modals and the
  guide's card — stands on one ground, edge, corner and lift, at one of
  four widths, and one with a name is headed alike: the name at one size,
  the way to put it away at the far end. A pane that asks a question —
  before a comment is deleted or put away, before stories are turned on —
  is headed by it, at that size. A pane stands whole where the
  reader sees it: moved in from the window's edges, never under a file's
  header or a chapter's bar kept in sight over what is read, nor past the
  foot of the area it is drawn in, where it opens the other way; what it
  holds scrolls inside it, the finish pane keeping Send at its foot. It
  takes the keyboard without moving what is read.
- **Help is a pane under its button, as Settings is**: headed "Help", with
  the tour, the news and the list of keys, the keyboard in it while it is
  open and the review's keys its own. Escape, a press outside, its ×, or
  `?` again closes it, and the keyboard goes back to where it was; opened
  from inside another pane, it takes that pane's place. Every key it lists
  is the key the review answers, from one table.
- **How long ago is said one way everywhere**: "12s ago", "3m ago", "1h
  ago", "2d ago". A question waited on for an hour said "asked 3600s ago",
  and a base taken a moment ago "0m ago". One clock ticks for the whole
  review, and only while something on screen says how long ago.
- **Colours keep to one meaning each.** Blue is the reader's: what they
  marked, and the controls they act with. Violet is the agent's: what it
  raised, said or brought the reader to, and what of it is not read yet —
  an answer arriving, a thread it raised, a file it showed, the branches of
  its work, which used to wear the reader's blue. Green and red are what the diff added and
  removed, and green also what is done; a warning — the tree moved on, a
  blocker — is yellow; orange is a modified file's letter alone; a moved
  file's R is quiet grey. A chip saying the reader sees less than the whole
  diff — a narrower base, whitespace hidden — takes their mark's tint and
  reads plainly. Every word on the page reads at 4.5:1 or better, in both
  themes, code on the band that marks a changed word too: the band is
  fainter, the light theme's code colours a shade darker, and the dark
  theme's comments a shade lighter.
- **The @-picker is a list to a screen reader**, which hears which thread
  or file is highlighted as the arrow keys move; the comment fields and the
  file filter say what they are.
- **In two columns a thread on an unchanged line sits on the right**, under
  the side it is about, where its field opened; before, it moved to the left
  once written.
- **Under a narrower base, j and k move through every line.** A removed line,
  which belongs to that base and takes no comment, used to stop them for
  good; it is passed over like any other line now, and still takes no
  comment. A comment being written on such a line waits, out of sight, until
  the whole review is shown again.
- **`claude-review progress --done` is sent on its own.** Given a text, a
  file, a step or a message beside it, it used to drop them unseen; it now
  refuses, naming `--done`, as `status` with nothing to report does.
- **A side of a hunk with no lines starts where its first line would be.**
  Git writes the line before it — 0 for an added file's old side — and the
  page counted the lines hidden above such a hunk from there, one short. A
  hunk's `old_start` and `new_start` are now always the number its first
  line has, or would have, on that side; the hunk is read by the counts in
  its header, so a blank line of context git writes without its space is
  still a line.
- **Commands and routes renamed, so each name says one thing.** `claude-review
  round` is now `claude-review retake` (`POST /api/retake`), and `claude-review
  context` is now `claude-review catch-up` (`GET /api/catch-up`, a thread at
  `/api/catch-up/threads/{id}`). "Context" is left to the agent's context
  window and git's context lines. An installed skill from 1.5.0 uses the old
  names and must be updated with the release.
- **The diff and the reader's records on the wire.** A diff line says its
  `kind`, `old_number` and `new_number` (were `type`, `old_no`, `new_no`).
  `GET /api/settings` and `GET /api/guide` answer `{record, stored}` (were
  `{settings, stored}` and `{guide, stored}`). `/api/diff` names the base it
  was taken against in one field, `base: {key, phrase, narrowed}` — null in a
  review that is compared against nothing — and a retake names the key that
  shows what changed since its round.
- **What the review is, apart from its diff.** `GET /api/review` says the
  title, mode, round, whether an agent is attached and what it last said of
  itself, the limits and the release; `/api/diff` carries only the diff
  against a base (files, base, moved). The `diff` push says how many
  files the review now holds, so a page reading a narrower base counts the
  review rather than its screen.
- **A thread's `where` is plain text for the agent**: `src/a.py:42-47`,
  where it was `` `src/a.py`:42-47 ``. The events, `catch-up` and its index
  carry no Markdown any more; the round, which is Markdown, still sets the
  path as code, and a path with a backtick in it no longer breaks it.
- **The agent counts as there for ten minutes after it last called**, and
  the review stops offering rounds once it has gone quiet for longer.
- **A page that stops reading is let go** instead of being held in memory;
  the server's websockets now run on wsproto, and the `websockets` package
  is no longer a dependency.
- **A page whose socket drops is handed what it missed.** Every
  connection to `/api/session` begins with a `welcome` naming the run of
  the review and how far its telling has got, and every push now arrives
  in a numbered `delivery` (`{type: "delivery", sequence, push}`) rather
  than on its own. A page connects with `?instance=…&after=…` and is handed
  the pushes it missed, up to the last 512. One that cannot be handed them
  all — the review was restarted, or the page was away too long — is told
  so (`resumed: false`), reads `GET /api/review` again, follows its threads
  onto the diff as it stands, and says in the panel that answers given
  meanwhile may be missing. `GET /api/review` says the work under way
  (`work`, no longer pushed to a page as it opens) and how far the telling
  had got when it was read (`instance`, `sequence`), so a page opening
  continues from there; a reloaded page continues from where its draft
  left off, so answers given during the reload arrive too.
- **Taking the diff stages the working tree once**, starting from a copy of
  the repository's own index: much faster on large trees. Like `git diff`, it
  leaves out edits to files marked assume-unchanged or skip-worktree.

- **Requests are read as the API's schema says, and refused as it says.**
  A yes or a no in a JSON body is `true` or `false`: `0`, `1` and the like
  are refused. A round's key is `round:` and the number in plain digits.
  Every refusal is `{detail}`, in words or field by field, and each route
  documents only the refusals it can give, those for what it takes in
  marked `x-refused-for-its-input` — the origin guard's `403`,
  which was plain text, on every route. `POST /api/images` describes the
  image it takes as its body, and an image's id in a path is bounded as
  every other id is. A method a route does not take is answered `405` with
  an `Allow` naming every method taken at that path, and a path no route
  serves `404`, rather than by the page's file server: the page is served at
  `/` and its files under `/assets` only, so `/index.html` and `HEAD /` are
  no longer answered.
- **The review's base is the commit it opened on.** An agent's commit during
  a review of uncommitted changes used to empty the diff and mark every
  thread outdated; under `--base HEAD~1` the commit under review left the
  screen as more were made. The base is now read once, as the review opens,
  and every later diff is taken against that commit. A tag on anything but
  a commit is no longer offered as a base, and a base that names no commit
  is refused in one line.
- **Each review keeps its own draft, and which files were read and folded.**
  The draft is kept under the review's own name — its repository and base —
  so a second review on the same port no longer overwrites the first's
  unsent work, and a reload no longer un-ticks every file. The draft 1.5.0
  kept is picked up once, by the first review of its title. A draft that
  cannot be brought up to date is set aside as it was kept, never written
  over, and the review opens without it, saying so under the header.
- **Ending a review sends what was not sent yet as the final review**, and
  a comment still open in its field goes with any round or review, listed
  in the finishing pane. A round marks sent only what it carried, and a
  summary rewritten while it was on its way is kept.
- **A thread the agent raised stays the agent's**: it offers no Edit and no
  Delete, and the server refuses a round, a question or a message that
  changes its opening (`422`).
- **The agent's two takes are `POST`**: `POST /api/events` and `POST
  /api/catch-up/threads/{id}`; a `GET` there is answered `405`. The agent's
  commands are unchanged.
- **What the agent names twice is named once.** A file or a step named
  twice in `say` or `progress` is refused (`422`, naming it). The command
  line sends a file typed twice once, refuses a step both done and under
  way, and says a list longer than the review takes as a usage error naming
  the option rather than a traceback.
- **An answer to a thread, or a jump to a file, the review does not hold is
  refused** (`404`, one line from the command) rather than taken.
- **A file the agent names that the diff does not hold yet is a chip that
  says so.** `say --file` and `progress --file` take any file — one the
  agent is about to make among them — and its chip in the panel reads "not
  in the diff yet" and takes the reader nowhere. Under a narrower base a
  file the review holds takes the reader back to the whole review, then to
  the file.
- **`progress` with nothing to show is refused**: it needs words or a
  branch, or `--done` on its own; a file alone used to clear the work.
- **What the reader or the repository wrote is printed to be read, never
  obeyed**: a terminal's own controls in a thread, a file's name or a
  failure come out written, as `\u001b`.
- **A transcript's turns are named by their entries' own ids** — "user
  f260656f" — the same in every time zone; the name no longer says the time.
- **A file over 4 MiB is shown without its lines**, saying "Too large to
  show" rather than calling it binary, and the diff is read off the
  server's event loop, so the review answers its pages while a large one
  is read.
- **A file whose name holds a control character is shown, read-only**: a
  thread on it would have had its whole round refused.
- **The diff keeps a width it can be read at.** The panel, and on a narrower
  screen the tree, lie over the diff rather than squeezing it; the header
  and each file's header wrap. Where a column would lie over the diff, it
  waits to be asked for: the tree starts put away, and the panel no longer
  opens itself when the agent attaches (the dot in the header says the
  agent is there). A column the reader opened or shut stays as they left
  it.
- **Links in rendered Markdown open in a tab of their own**, and a relative
  one is text: a click used to take the tab away, and the review ended
  three seconds later. The page asks before it is left with something
  unsent. An image in Markdown is named in its line and never fetched; an
  absolute one is a link.
- **Only the answers not yet read are drawn new**, not every answer of a
  thread with one unread.
- **A reader who asked for less motion gets none**: no animation, no
  transition, no smooth scroll.
- **The page takes you where it sends you at once.** A file the agent
  shows and a thread you are taken to, by `n`, a chip or the finishing
  pane, were glided to: on the look's long change a file shown far down
  took a second and a half, built the 37 files it passed, and ended as much
  as 709 pixels short, to be put in place at once at the end; one a screen
  down took 0.6 seconds. The page now scrolls there at once, and once more
  three frames later, when the files beside it are built: a thread's card
  in the file above, which the browser does not always make room for, no
  longer pushes the file below from where it was sent. Every jump the look's
  long change was measured on stood still within 80 milliseconds, a file
  shown far down building 2 files. A turn of the wheel, a touch, a press or
  a key of yours in those frames is left alone: the page does not scroll
  there again.
- **The review serves no description of its API** (`/docs`, `/redoc`,
  `/openapi.json`); the page is asked for again whenever it is opened, so
  an upgrade serves the new one, and its built files are kept for good. The
  page's inline script is allowed by its hash, not by `'unsafe-inline'`.
- **A request found wrong is refused field by field**, without what was
  sent echoed back; the page knows the longest text the server takes, and
  its fields stop there.
- **The columns beside what is read keep their heads in sight.** The tree
  of files and a story's contents are headed by one bar with the agent
  panel's, as tall: their name and the way to put the column away stay
  where they are as what is under them scrolls, where the tree's heading
  scrolled away with its files.
- **Words set apart by an edge are framed one way**: the agent's voice in
  a story and its broken edge where it read the change out of the code, a
  warning, a thread folded away and the lines a thread lost. One edge and one corner, the words 16 pixels in from
  the edge and from the far side, as far as a card's, and 8 above and below. A chapter's
  "Changed after it was told" and its Doubt are both warnings, headed
  alike, and what a story costs is said in one. A block of the story
  pointed at is banded inside its frame's edge; one a thread of the
  reader's hangs under stands on their tint with their edge beside the
  frame's, so a doubt still shows the warning's yellow. What hangs under a
  block hangs 8 pixels below its band, as under a line of code, also where
  the block has a frame of its own, below which it hung 16. The light
  theme's warning is a shade darker, to read on that tint.
- **A thread, every turn of the panel — what the reader asks, the agent's
  answer and its work — and a story on its way stand on one kind of
  card**: on the raised ground, edged in the colour of whose it is, at one
  corner — 6 pixels, where a thread's was 8 — with one room round what it
  holds, 16 pixels on every side, so the panel's turns line their words up. Code set apart, the commands to attach an
  agent and the source of a diagram that did not draw, stands on a quiet
  card at the code's size. A hanging card points up at what it is about
  with the arrow a pane points with. The agent's violet moves a shade,
  lighter in the dark theme and darker in the light, so its chip reads at
  4.5:1 on a card, under the pointer too.
- **Every notice is one bar**: the code moved on, the diff taken again,
  what was not sent brought back, the review out of reach or over, a part
  that could not be drawn, a file's notes. Each is as tall as one with a
  button, its words at one size and as far in from its edges, and says
  what it is by its ground and its mark. The bar saying the review is over
  is no longer larger, bolder and centred.
- **A tag and a count stand in one box**, 18 pixels tall wherever they
  stand — a thread, the panel, a file's header, a row of the tree or of a
  story's contents, the list a round is sent from, a story — at a field's
  corner, never as a pill. A tag shows its words as written, so a measure
  says "1M", not "1m". What a question the agent raised asks for is in the
  agent's colour in the finish list too, and a count of threads stands on
  the reader's mark. A thread or a file
  named in what is said is a chip in the same box, in the colour of who
  named it; the cross that takes one out of a message being written is
  the chip's own. The release the news card is of is a quiet tag beside
  its heading.
- **Every row of a list is one row, 32 pixels tall at the least**: the
  tree's files and folders, a story's contents, the bases to read against,
  the replies, the @-picker, the comments the finish pane lists, Help's
  entries and the threads a narrower base cannot draw, where rows stood
  from 24 to 48. Each is lit the same under the pointer, and the one the
  reader is at stands on their tint with an edge at its start. A story's
  contents read as the tree does: a part read through steps back in faint
  words. A chapter's title longer than the column is wide wraps onto more
  lines and reads whole, its node and its count level with its first line;
  a file's name stays one line, cut where its row ends. A list of threads
  gives one line to each: where it hangs, then what it says. A comment the
  finish pane lists is one row, its words in full under the line it hangs
  on: a press on them takes the reader to it, and one sent with a round
  steps back whole.
- **Every dot is one dot, and every key one key.** A reply not read, the
  agent there, a turn on its way, a file changed since the round, the
  overview's node in a story's contents: round, 6 pixels across. A key to
  press, in Help's list, on its button and on the welcome card: in the
  code's face, in a line round it, as tall as a tag; a key held with
  another is one key, `Ctrl+Enter`.
- **Every icon is drawn at one of four sizes**, as tall as the words it
  stands beside: the smallest marks grow from 10 to 12 pixels, and Help's
  plus is as large as the compass above it.

### Fixed
- **What the pointer is on is seen in the dark theme too.** A row of the
  tree, the contents or a pane, a chip, a segment, a line's number, a hunk
  gap's ways to show lines, a column's rail and grip, a thread's buttons:
  each is lit the same way in both themes, at about 1.16:1 against its
  ground, where the dark theme lit the tree's rows at 1.02:1 and Help's
  entries not at all. The one of a set you are at — the file you are in,
  the base the diff is read against, the option the keys lit, a segment
  pressed, Agent on, a control whose pane is open — stands on your mark's
  tint with an edge of it that reads at 3:1, where a pressed segment read
  at 1.27:1 and an open pane's control was drawn as a closed one. Words
  read at 4.5:1 on every one of these grounds: faint words, line numbers,
  the agent's colour, a warning, an error, a modified file's letter and the
  mark as words are a shade stronger, and what the page faded — a file you
  viewed (3.03:1 in the light theme), a comment sent with a round, a turn
  taken back, a step a round changed — is said in faint words instead. A
  row of code is no longer brightened under the pointer, which showed at
  1.00:1; its number is lit. The column's grip and "Started the review
  yourself?" take the focus ring.
- **A choice about Story's introduction the review could not keep is
  said.** "Don't show again", or its Undo, that the review failed to keep
  was dropped without a word, and the next review introduced Story again;
  the panel now says it could not be kept, and why.
- **A part of a story is read once you scroll past it.** The overview, and
  any part shorter than the screen, counted as read the moment the story
  opened, its head and its end both on screen before any scroll. A part is
  now read once your scrolling carries its end into view or out above the
  top; where it stands as the story is drawn counts for nothing, and
  scrolling back up away from it counts nothing either.
- **A file not drawn yet holds the room it takes.** Until the reader came
  near a file, its section held room for its rows alone; drawn, it took the
  header of each hunk and the bar for the lines left out around it too, 57
  pixels more a hunk, so what lay below moved as the files on the way were
  drawn: 7025 pixels over the 37 files of the look's long change not drawn
  as it opens, and 1808 over its story's 58 pieces. The room now counts
  those bars, the rows two columns lay a file out in, and a story's piece
  by its own smaller header: the 38 files not drawn as it opens now hold 25
  pixels too many, and the 58 pieces 17, as a row is a fraction of a pixel
  shorter than counted. A thread under a line, a comment being written and
  a line that wraps are still not counted.
- **On a phone the page is no wider than the screen.** On a screen
  narrower than the diff reads at, the diff took the whole width of the
  row beside the rail of the file tree put away, and the page scrolled
  sideways by the rail's width; it now takes what the rail leaves.
- **A line's number sent as `true` or `false` is refused.** A thread's
  lines, or the first line of a step of the story, were read as 1 or 0: a
  line nobody named.
- **A tab you come back to takes in the settings changed in another.**
  Every review keeps the reader's settings in one place, and a tab read
  them only as it opened. Now a tab shown again reads them again: the theme
  and the layout follow, the diff is taken again where whitespace stopped
  or started counting, and turning stories on asks this review for its
  story.
- **What the agent said before the page opened is in the panel when it
  opens.** A page in another browser, or a private window, draws the whole
  conversation too: the reader's messages with their screenshots and the
  threads they point at, and a message taken back as stopped. A reload
  draws each part once, with the review's own notes from the draft between
  them.
- **`n` and `p` go on from the thread you are at.** `p` before any thread
  goes to the last one; it went to the one before the last. Removing a
  thread no longer moves the place they go on from onto another thread;
  removing the one you are at, they go on to the thread after it or back to
  the one before. A thread opened from the panel, the replies or the finish
  pane is where the next step starts. They go down the diff, file by file
  and line by line, not in the order the threads were written.
- **The agent's dot goes quiet while the review cannot be reached**; it
  stayed green, as if the agent were known to be listening.
- **In two columns a removed line facing the line that replaced it takes a
  comment from the keyboard again**: Tab reaches its number, Enter opens
  the field. j and k still stop once a row. In one column j on a removed
  line puts the focus round its number; it was a flat line on the edge of
  the row above.
- **Closing a pane never leaves the keyboard nowhere.** After a round sent
  from the keyboard, or a press on a pane's own words, it goes back to the
  button the pane opened from; a pane opened by its keys from a comment
  gives it back to the comment; `?` closing the keys list gives it back to
  the line being read. Tab out of a pane closes it, so two can no longer be
  open at once, and a selection let go outside the keys list leaves it
  open.
- **Nor does putting a column away.** The file tree put away by its button,
  or by `f` with the keyboard on one of its files, hands the keyboard to
  the rail that brings it back; brought back, to the button that puts it
  away. The agent panel closed by its own button hands it to the Agent
  button in the header.
- **`j` and `k` start where you are reading.** With the keyboard outside
  the diff — on a file just picked in the tree, on a button of the header —
  or on nothing, the first `j` or `k` went to the first line of the whole
  review and scrolled back to its top. It now lands on the first line in
  sight, under the file's header, and the screen stays where it is.
- **The list of keys leaves out the keys that have nothing to act on.**
  Over a diff with no file left in it, it listed `j / k`, Enter, `] / [`,
  `v` and `u`, which did nothing there. `n / p` stay while a comment on a
  file no longer in the diff is shown above it.
- **Taking a thread out of a panel message leaves a longer one alone**:
  dropping `@a.py:1-2` used to cut into `@a.py:1-20`, losing that thread
  from the message and leaving a stray `0`.
- **A panel message on its way is not sent twice** when the panel is closed
  and opened again before it arrives.
- **A chain of folders in the file tree is one row however long**:
  `src/lib/components` read as "src/lib" and then "components".
- **Ctrl+Enter in a comment field no longer takes Ctrl+Shift+Enter**, which
  finishes the review, for its own.
- **Showing more context no longer moves what is written under a line.** A
  comment being written jumped under another line and lost its words, and a
  reply being written was dropped with the image pasted into it; asking for
  the same lines twice, or a round landing while they were read, drew lines
  that did not belong there.
- **A drag over removed lines that is cut short ends on a removed line**, so
  its thread is drawn; it could end on a line the change kept and be drawn
  nowhere. An image taken off an edit that is then put away stays on the
  server, since the comment still shows it.
- **The reader's own git settings no longer change the review's diff.**
  With `diff.suppressBlankEmpty` set, a blank line of context was dropped and
  every line after it in the hunk numbered one short, so threads landed on
  the wrong lines. The diff is now taken the same way whatever the reader
  has set: git's default three lines of context, whatever `diff.context` or
  `GIT_DIFF_OPTS` say (wider context is a click away, as before); a file as
  it is stored, never through a `textconv` converter of theirs; a copy as
  the new file it is, whatever `diff.renames` detects; a submodule as the
  commit it moved to, whatever `diff.submodule` asks. A review started from
  a git hook reads its own repository: the hook's `GIT_DIR`, `GIT_INDEX_FILE`
  and the like no longer point git elsewhere.
- **A path the review asks git about is that path, never a pattern.** An
  untracked file named like `[ab].py` passed for the tracked `a.py` it
  matched, so the context of a hunk could be widened into it.
- **A review that is over lets go of its page.** It tells its page so as
  it ends: sent for good, stopped, or replaced by another review on the
  same port, each with a bar that says which, and the page connects no
  more. A tab left open
  after the review used to connect to whatever review ran next on the same
  port, tell it the old review's round and threads, and hold it open after
  its own tab was closed.
- **Threads brought back from a draft follow the diff the review opens on.**
  A reload while a retake was moving them, or a move that failed, used to
  leave them on their old lines.
- **A page on another port of this machine can no longer reach the
  review.** A request that carries no Origin — a no-cors fetch, an image —
  got in: it could take what the reader handed the agent, light "agent
  attached", and hold enough connections that the review's own page could
  not load. Such a request is refused by what the browser says of where it
  came from, and the guard's own refusals carry the review's security
  headers.
- **A drag across lines the diff leaves out stops at the last line drawn.**
  The comment's heading named the whole range while it quoted only the
  lines shown, and an agent applying its suggestion deleted the rest. The
  server refuses a thread that does not quote one line for each line it
  names; one that quotes none, kept from before quotes were, is taken.
- **One broken part of the page leaves the rest on screen**, saying what
  broke and offering "Try again"; a step or a file the agent named twice
  used to blank the panel, and after a reload the whole page.
- **A file that became a link, or a link that became a file, is one file**;
  as two under one path the page drew nothing at all.
- **A diff taken again with nothing in it keeps the review around it**: the
  header, Send, End and the panel stayed away.
- **A thread whose line is not on screen is drawn at its file's head**, as
  after a retake turns its removed line back into context.
- **A new diff keeps the reader on the line they were reading**, not in the
  file above it.
- **A repository whose path holds a colon shows its changes**; every file it
  tracks read as added.
- **A reader's `core.safecrlf` no longer stops a review from opening**, and
  Ctrl+C or `kill` while it opens leaves nothing in the temporary directory.
- **Context widened in a file with a lone carriage return is numbered as git
  numbers it**, and a link in the review is never widened into the file it
  points at.
- **A transcript with U+2028 in a message is read**, rather than refused
  whole.
- **A file made runnable after the diff was taken is said to have moved.**
- **"Changed since round N" counts from where round N opens**, when the
  diff was taken more than once in it.
- **Images pasted and never sent go when the review ends**; only those the
  agent was handed stay for it.
- **Lines quoted or suggested with a run of backticks in them stay inside
  their fence**: a quoted `` ``` `` closed it, and the rest read as the
  round's own Markdown.
- **A word mark never falls inside an emoji or a wide character.**
- **Dropping a mention from a message keeps every other space in it**, code
  indentation among them.
- **The keyboard goes with the reader.** `n`, `p` and every control that
  takes the reader to a thread move the keyboard there too, and a row of
  the finishing pane leaves them where it took them. `v` and `u` act on the
  file a jump landed on. The keys list opens over a pane, which stays open
  under it. An agent arriving never takes the keyboard from a field being
  typed in, the @-picker keeps its highlighted option in view, keys an input
  method is composing a word with are never the page's, a line's number
  answers a click with no press behind it, and after a comment is saved,
  put away, resolved or deleted the keyboard lands on what remains.
- **The tour moves on once the page shows what the reader did**, and counts
  its stops one way.
- **A thread id no page could give costs only that thread**; it closed the
  page's socket.
- **A page with no draft takes the review's threads in**, and a thread the
  agent raised outlives any page; a page opened in another browser used to
  drop every thread.
- **A long line of a suggestion scrolls** instead of being cut off.

## [1.5.0] - 2026-10-05

### Added
- **A guide to the review, from a card in the bottom left.** The first review
  ever opened offers a tour: a light moves over the review while the card
  says what each part is for. It waits for you to comment on a line, shows
  the two ways a comment can go, and where it went, and tells a round from
  the end of a review. Steps with nothing on screen to show are passed over,
  so the same tour fits files and transcripts, and a review with no agent.
  A reader back from an older release is told what is new — only the
  newest entry they have not seen, with a picture (a file, or a drawing in
  the theme) and a link to the release on GitHub; nothing written since,
  nothing said. Both are a line away in the `?` list. What was seen is kept in a
  cookie, shared by every review on the machine whatever its port.
- **Screenshots in the agent panel.** Paste an image into the field with
  Ctrl+V. It goes to the server as soon as it is pasted and shows under the
  field; the message hands the agent absolute paths it can open, and
  `context` lists them too. An image can be the whole message. PNG, JPEG, GIF
  and WebP, recognised by their bytes, up to 10 MB each, ten to a message and
  200 MB to a review — limits the server tells the browser, which checks them
  before uploading. The message being written, images and all, is kept with
  the draft, so hiding the panel or reloading the page loses nothing. An
  image taken off before sending is removed from the server; one the server
  no longer has, after a restart, is taken off with a note instead of drawn
  broken.
- **Screenshots in threads too.** The same Ctrl+V works in every comment
  field: a new comment, a reply, an edit. The agent finds the paths in an
  "Ask now" question and its history, and as an `Image:` line under the
  comment or turn in a round. Cancelling a comment drops what was pasted into
  it; an image that did not survive a restart of the server drops out of the
  round instead of holding it up.

### Changed
- **What a review writes stays out of the repository under review.** The
  trees taken at every round go when the review ends. The images pasted into
  it stay in the system's temporary directory, because the last round names
  them and the agent reads it after the review has ended; the review says
  where they are on the way out.
- **The agent panel waits for the agent instead of asking for setup.** Until
  the agent's first `wait`, the panel showed the commands for attaching one
  by hand, which read as a task left to the reader — while the agent that
  opened the review was seconds from attaching. It now says it is waiting,
  and keeps the commands folded under "Started the review yourself?". The
  skill closes the gap from the other side: the loop starts in the very next
  call after the server.

## [1.4.2] - 2026-09-11

### Fixed
- **The review opens in the browser again when an agent starts it.** The
  address was printed only when the browser was *not* being opened, so
  anything starting a review for somebody else had to pass `--no-open` to
  learn where it was — and the window stopped opening for everybody. Both now
  happen: the address is said either way, and a machine with no browser to
  open loses nothing but the window.

### Changed
- **The skill says how to hold the loop open, and how to put the work line
  out.** Waiting "in a loop, in the background" had two obvious readings and
  both are wrong — one returns on the first timeout, the other blocks the
  turn — so the four lines that work are written down. And a progress line
  started without a message had nothing that would clear it: `--done` is now
  named as the way, before a round as well as at the end, so a retake does
  not land under a spinner describing the diff it replaced.

## [1.4.1] - 2026-09-11

### Changed
- **The skill tells an agent to stay attached, rather than offering it as an
  afterthought.** Running the review and waiting on its output was the
  documented default, with the conversation behind a "skip this unless
  asked" — so a reader got an "Ask now" button on every thread, a panel, and
  an offer of a round, with nothing on the other end of any of them. The
  background loop is the flow now; the one-shot run is the exception at the
  end, for a review nobody means to talk through

## [1.4.0] - 2026-09-10

A round leaves a mark, so the review can be asked what has changed since it.

### Added
- **Choose what the working tree is read against** — the second half of the
  header's title became a control: the base this review opened with, an
  earlier round of it, or any branch or tag. What it changes is what is
  drawn, never what the review holds. The right-hand side of the diff is
  always the working tree, so every thread stays anchored where it was
  written, and one this base cannot draw is hidden and counted rather than
  moved or marked outdated
- **A round leaves a mark** — the tree the diff was taken from is written as
  a real git object each time it is taken. The work under review is
  uncommitted, so between two rounds there may be no commit to go back to.
  The objects live in a store belonging to the review, which goes with it:
  the repository gains nothing, and a restarted server keeps only the refs
- **A retake says what changed** — which files moved since the last one, and
  from which round they are counted. `claude-review round` returns the same
  list, so an agent that came back to a review it left reads those files
  again rather than all of them

### Fixed
- **A file the agent rewrote kept its "viewed" tick** through the retake, so
  a reader walked past code that had changed under them. The tick now comes
  off exactly the files the round moved, and the file is unfolded with it —
  left folded, it reads as read
- **A file the agent pointed at barely said so.** The mark was a background
  behind an opaque file header and rows that paint their own, so it showed
  where nobody was looking. It is an outline now, painted after every
  descendant — and it waits for the scroll to stop, because across sixty
  files a smooth scroll outlasted the mark itself. Shown twice running, it
  flashes twice
- **The notice that the working tree had moved on was said once and lost.**
  It lived only in a push, so a review reloaded at that moment never heard
  it, and one opened later never learned the tree had moved before it
  arrived — the "Retake" it offers went with it. The diff now says how far
  the tree has drifted, so a review that has just loaded knows; what the
  reader waves away stays away until something else moves
- **Work nobody was waiting on could not be shown at all.** The progress line
  was drawn only under an unanswered message and put out by any answer, so
  what an agent did on its own account — working through a round, reading
  with subagents — left the panel looking idle. It now has a row of its own,
  and an answer ends only the work it answers
- **The box being written in and the lines it was about wore one colour.**
  Both are the reader's own mark, but a composer washed in the same tint as
  the rows directly above it read as one patch. The tint now belongs to the
  lines; the composer keeps the edge and stands on the page's own surface
- **The `@@` marker stayed in the middle of the code** once the lines it hid
  had been revealed, announcing a jump where the code ran on unbroken. It
  now belongs to the gap it marks and goes with it — including at the top of
  a file whose first hunk starts at line 1

## [1.3.0] - 2026-09-09

The review gains a second conversation: one about the change as a whole,
with the agent that wrote it.

### Added
- **The agent panel** — a panel on the right for everything a thread is not
  about: the plan, the tests, a file nobody commented on. It reaches the
  same agent that answers the threads, in the same vocabulary — the reader's
  turns on the mark's tint, an answer on the page's own ground, a waiting
  turn that holds its place. Everything typed there goes at once; there is
  one button, because "add to review" has no meaning outside a thread
- **Point at a thread with `@`** — the picker lists the threads with their
  state, and what travels with the message is the thread itself: its lines,
  the comment that opened it and every turn since. The reference is a token
  in the text, so deleting the word takes the reference with it
- **Two numbers, told apart** — what handing this review over costs is
  arithmetic over the diff and the threads, and the review does it. How much
  context the agent has left cannot be measured from here at all, so it is
  quoted with who said it and when, and shown as nothing until it is said
- **Stop a message** the agent is still working on — a request on the same
  queue, not a kill: nothing here can reach into another process
- **A notice when the working tree moves on** — the server polls
  `git status --porcelain` and says how many files have changed since the
  diff was taken. It never swaps the diff by itself: doing that under a
  half-written comment orphans it. After a retake, the bar says what became
  of the threads and offers a way to the one that lost its lines
- **The author can point at a line** — `claude-review point --file --lines`
  raises a thread on the code, for what a paragraph elsewhere would bury:
  where the agent did something other than what was asked, and why. It is an
  ordinary thread from there on, drawn in its own colour because the marks in
  a review are the reader's, and it never counts as their unsent work
- **Progress, while the work is happening** — `claude-review progress` puts a
  live line under the waiting turn: what is being done and which files are in
  hand, replaced as it changes and gone when the answer lands. `--did` and
  `--step` are drawn as branches of the work, so three subagents read as
  three branches rather than as a sentence about three subagents; the files
  are chips the reader can jump by
- **The agent can speak first** — `claude-review say` without `--message` is
  an unprompted message, so work finished while the reader was reading
  arrives on its own, with the dot, the tab count and the optional tick that
  answers already have
- **Jump to a file, or be taken to one** — `say --file` offers the jump;
  `claude-review show --file` takes the reader there and marks the file for a
  moment. The only thing here that moves somebody else's screen, and only
  when they asked
- **Catching up** — `claude-review context` says what a review already
  holds: the round, a line per thread, the panel in short. `wait` hands over
  what happens next and never what already happened, so an agent restarted
  mid-review used to know nothing. An index on purpose; `--thread <id>` gets
  one thread in full
- **The round survives a restarted server** — the review on screen says where
  it had got to when it connects, and never downwards, so a server that came
  back believing it was round one stops numbering the next round wrongly
- **A thread raised on a line that is not in the diff is refused**, with what
  the review does have. It used to be accepted and shown hanging on nothing
- **`@` points at any file**, not only at what already has a thread
- **`c` talks to the agent, `f` shows or hides the tree** — the panel was the
  one thing in the review that needed a mouse
- **The file tree can be dragged narrower or put away**, and the panel's
  width is the reader's in the same way
- **`claude-review say`** answers a panel message by name, and
  **`claude-review status --model --context`** reports what only the agent
  can know. `claude-review wait` now also yields `message` and `cancel`

### Changed
- The panel's conversation, its width and whether it is open live in the
  draft and the reader's preferences, so a reload keeps all three
- "Diff retaken" takes itself away after twelve seconds: it reports something
  that has already happened and wants no answer

## [1.2.0] - 2026-09-09

A comment becomes a thread, and sending stops having to be the end of the
review.

### Added
- **Threads** — a comment carries turns with speakers and a composer under
  the last one, an answer hangs off the question it answers, and asking
  twice no longer overwrites the first exchange
- **Ask from the composer** — "Add to review" keeps the comment with the
  rest and sends it when the review does; "Ask now" hands it over
  immediately and marks it a question. The severity chip stops looking like
  a control that asks
- **Rounds** — with an agent waiting on the review, sending sends a round and
  leaves the review open: the agent answers, makes the changes and retakes
  the diff with `claude-review round`, and the reading carries on. "End
  review" is the separate act that finishes it. A round carries what is new
  since the last one, not the whole review again
- **Threads survive a retaken diff** — a thread whose lines moved follows
  them, and one whose lines are gone is marked outdated and keeps a copy of
  what it was written against. Both travel into the submitted markdown
- **Resolve a thread**, which collapses it to a line and goes out marked
  resolved — the state belongs to the comment, not to the tab
- **A "Replies" list in the header** — answers you have not read, with a
  count, a jump to the thread, `a` for the next one, and an optional tick
  when one lands while the review is in a background tab
- **The tab says so** — the title carries the unread count and the icon takes
  a dot, so an answer is visible from a tab strip
- **An answer lands under the question it answers.** Every question carries
  an id: `wait` hands it over, `reply --question` gives it back, and two
  questions asked before either is answered still read straight. A question
  also carries the whole thread, starting with the comment that opened it
- **Comments and answers are markdown** — code blocks with highlighting,
  lists, inline code, through the renderer that already draws md previews
- **Fold a thread away** with the same control that folds a file, and read a
  folded or settled one by opening it. Resolving folds a thread rather than
  hiding it: settling something no longer means it cannot be read
- **A suggestion is shown as the change it asks for** — the lines it replaces
  above the lines it puts there, marked the way the diff marks them
- **What has already gone out is marked** — a thread sent with a round carries
  a `sent · round N` stamp and gives up the mark colour, and the header counts
  what the answering side has not seen
- `claude-review round`, and `claude-review wait` now also hands over rounds

### Changed
- **A review reopened on the same repository comes back on the same port**,
  derived from the repository and the base ref, so the draft left in the
  browser's storage is still there. `--port` still wins, and a derived port
  someone else holds falls back to a free one
- **Nothing in the interface is named Claude** — whoever answers is whatever
  agent is driving the review, and the wording now says so
- **A comment sits under the side it is about** in the two-column layout, and
  says which side that is in the diff's own signs — the same line number
  exists on both, and a box in the wrong half named neither
- **A comment is measured for reading, not pinched into a column** — the
  measure went from 72 to 96 characters
- **Asking belongs to what it asks about** — the control sits under the last
  thing said in the thread and hands over everything since, while the
  composer's own "Ask now" is about what has just been typed
- **The reader's choices are remembered** — layout, how a markdown file is
  shown, and whether whitespace counts, kept beside the theme. They belong to
  the reader, not to one review, so they survive both
- **A draft written by an older version is brought up to the current shape**
  rather than dropped. The version is there so work can be carried forward —
  losing an hour of reading to a version number is the worse failure

## [1.1.0] - 2026-09-09

A pass over how a review reads and how it is written, plus the beginnings of
a conversation with Claude inside it.

### Added
- **The whole diff as one stream** — every file is on screen at once and the
  sidebar navigates by scrolling to one, so find-in-page, selection across
  files and the reading position all survive moving around
- **Split layout** — the old version faced against the new one, chosen once
  for the review from the header
- **Word-level marking** inside a replaced line, so a renamed identifier or a
  changed constant is visible without comparing two long lines by eye
- **Show the lines a hunk left out**, a screenful at a time or the whole gap
- **Ignore whitespace** — retakes the diff with `-w`, so a reindented block
  stops burying the one line that changed
- **Ask Claude about a comment thread** — the question waits for whoever is
  answering, the reader carries on, and the answer is pushed into the thread.
  `claude-review wait` and `claude-review reply` are the answering half
- **Suggest a replacement** — a comment can carry the code it should become
- **Comment severity** — a question wants an answer before anything changes;
  a blocker has to be dealt with
- **Keyboard** — `j`/`k` between lines, `Enter` to comment, `]`/`[` between
  files, `n`/`p` between comments, `v` viewed, `u` fold, `?` for the list
- **Fold a file, mark it viewed**, filter the tree by path, and see progress
  through a long review in the sidebar heading
- **Comments survive a reload** — an unsent review is picked up where it
  stopped, tied to what was being reviewed
- `--version`

### Changed
- **The server holds the review open on a socket** rather than a heartbeat.
  Browsers throttle timers in a background tab to about once a minute, so
  switching away used to look like an abandoned review: the server exited and
  took the unsent comments with it
- **One palette** for chrome, diff and syntax, replacing a stylesheet that
  imported both highlight.js themes and re-stated forty token colours by hand.
  No syntax colour uses green or red, which belong to the diff
- **A changed row is marked at its edge** over a faint tint, rather than
  washed with colour that dragged every syntax token towards it
- **A comment reads as a note**, not a warning: the mark colour, the reading
  face, one step larger than the code, at a capped measure
- **The header carries the review's identity and actions** — which repository
  and against what — and the bottom strip is gone
- Contrast holds in both themes: every muted token now sits above 4.5:1, where
  light used to lose about a fifth of its contrast to dark
- A hunk is highlighted as a document, so a docstring stays a docstring on
  every one of its lines, and it costs two highlighter calls instead of one
  per line
- A file's rows are built when it comes within reach. A 60-file review of
  3,500 changed lines went from 4.3s to 0.27s before it could be read, and
  from 2.0s to 0.19s to add a comment
- Adds `websockets`, which uvicorn needs to serve a socket at all

### Security
- **The server answers its own page and nothing else.** It had no `Host`
  check, so a page on any domain could point that domain at 127.0.0.1 and
  read the whole working tree and any file in the repository; and the
  same-origin policy never applies to WebSockets, so any page the developer
  had open could connect to the session socket, read what the server pushed,
  and throw away an unsent review by connecting and disconnecting once
- **A previewed markdown file is read, not run.** The preview rendered raw
  HTML out of the repository under review, so `<img onerror>` in a
  contributor's file ran script with the review's own origin — able to read
  the diff, read repository files, and submit comments of its own for an
  agent to act on
- **Expanding context is scoped to the files in the review**, rather than to
  anything in the repository, and no longer names the checkout's location in
  its errors
- **A filename can no longer write its own heading in the review.** Git
  quotes odd paths and the parser decodes them faithfully, so a name
  containing a newline could forge a whole section — a fabricated blocker in
  what the agent reads
- The page states what it may load and refuses to be framed

### Fixed
- **Files with non-ASCII names vanished from the review.** Git quotes such
  paths and the header parser did not expect it, so the file was dropped with
  no warning
- **A renamed file was reported under its old path**, sending the agent to a
  file git had already moved
- **A comment on a removed line appeared twice** and its number was
  ambiguous — `file.py:42` meant either side. Comments now carry the side
- Binary files and permission-only changes said why they had no lines to show
  instead of rendering an empty panel
- A busy port explains itself instead of printing a traceback
- Code no longer breaks mid-identifier when a line is too long for its column
- The composer opens in view when commenting near the bottom of the window
- Reading the diff no longer leaves a git object in the repository for every
  untracked file — 200 files used to leave 1.4 MB behind
- Expanding a hunk's context works from a subdirectory, not only from the
  repository root, and reading a window no longer loads the whole file: a
  134 MB file cost 454 MB of memory and stalled the server for two seconds
- Ignoring whitespace can be turned back off
- A comment appeared twice in the split layout when it sat on an unchanged
  line, and one click on a checkbox killed every keyboard shortcut
- A restored draft could hand out a comment id twice, which made two
  comments edit and delete as one
- Comment navigation reaches a comment in a file whose rows are not built yet
- A summary with no inline comments can be sent from the header, as it always
  could from the dialog
- `wait` and `reply` explain a missing or refusing server instead of printing
  a traceback, and `wait` is told when the review ends
- With `--no-open`, the review's URL is printed rather than left unsaid
- A copied file is shown as a new one, not as a modified one with no lines
- In files mode a file is named the way the reader names it, not by its full
  path

## [1.0.1] - 2026-07-12

### Changed
- **PyPI distribution** — releases are published to PyPI as a prebuilt wheel; installing no longer requires Node/pnpm (`uv tool install claude-review`)
- Skill and plugin install the CLI from PyPI instead of building from the git repo
- Sdist ships prebuilt frontend assets and excludes `frontend/`, so building from sdist needs no JS toolchain
- Release workflow (`release.yml`) publishes on tag push via PyPI trusted publishing (OIDC, no tokens), gated on the full CI suite passing on the tagged commit; publish re-runs are idempotent (`--check-url`)
- `scripts/verify_artifacts.py` — shared artifact verification (self-contained wheel/sdist, version sync across `pyproject.toml`/`plugin.json`, no source maps) used by both CI and release
- Frontend production build no longer emits source maps — cuts the wheel from ~308 KB to ~90 KB

### Fixed
- Build hook now fails loudly when pnpm is missing during a distribution build — previously it silently produced a package with no UI
- Build hook creates `static/dist/` itself when skipping the frontend build on editable installs — CI jobs no longer need the `mkdir` workaround

## [1.0.0] - 2026-04-13

### Breaking
- **CLI subcommands** — `diff`, `files`, `transcript` replace flat `--files`/`--transcript` options. Subcommand is now required (e.g. `claude-review diff` instead of `claude-review`).

### Added
- **`--base` option** — compare changes since a specific commit (`claude-review diff --base HEAD~3`)
- `/review-ui diff --base <commit>` — review changes since a specific commit from the skill

## [0.6.0] - 2026-04-13

### Added
- **Markdown preview** — three content view modes for markdown files: Raw (default), Preview (rendered), Side by side (raw + rendered)
- `ContentViewToggle` — toggle buttons in DiffView header, visible only for markdown content
- `MarkdownRenderer` — renders markdown via `marked` with highlight.js code block syntax highlighting
- `PreviewView` — full rendered markdown with comment count badge
- `SideBySideView` — split pane with synced scroll, commenting via left pane
- `RawView` — extracted from DiffView for reuse in side-by-side mode
- `@tailwindcss/typography` — prose styles for rendered markdown (headings, tables, code blocks, lists)
- 7 E2E tests for markdown view modes (toggle, preview, side-by-side, commenting, persistence, badge, non-markdown)
- 12 new frontend unit tests (store, toggle, renderer, DiffView mode switching, comment badge)

### Changed
- DiffView refactored to thin dispatcher: sticky header + mode-based component routing
- `contentViewMode` stored globally in diffStore, persists across file navigation, resets on `clear()`

## [0.5.0] - 2026-04-13

### Added
- **Transcript mode** — review Claude Code conversation transcripts (`claude-review --transcript conv.jsonl`)
- `/review-ui transcript` — review the current session's conversation
- `TranscriptService` — parses Claude Code JSONL files, merges consecutive turns, filters tool calls and thinking blocks
- `TranscriptReviewService` — formats transcript comments as self-contained blockquote markdown
- Messages shown newest-first with timestamps in sidebar labels
- 28 new tests (unit, integration, E2E, frontend) for transcript mode

### Changed
- Services instantiated in route handlers instead of stored on `app.state`
- `ServerState` moved from `schemas.py` to dedicated `state.py` module
- CLI uses single `asyncio.run()` instead of two separate event loops
- Heartbeat timeout extracted to `HEARTBEAT_TIMEOUT` module constant

## [0.4.2] - 2026-04-12

### Added
- Component tests for CommentBox, ReviewModal, DiffView, FileList, SubmitBar (19 tests)
- Frontend pre-commit hooks — ESLint, svelte-check, Prettier (skip gracefully if pnpm not installed)
- `svelteTesting()` plugin for client-side component mounting in vitest
- `data-testid` on comment count, cancel buttons, and all remaining interactive elements

### Changed
- Clarified test selector convention in AGENTS.md: testids for interaction, getByText for visible content assertions

## [0.4.1] - 2026-04-12

### Added
- Review mode badge in bottom bar (Diff / Files / Transcript)
- `data-testid` attributes on key interactive elements for stable E2E selectors

### Changed
- Browser opens in new window (`webbrowser.open_new`) instead of reusing existing tab
- Replaced argparse with click for CLI argument parsing
- E2E tests use `page.get_by_test_id()` instead of brittle text selectors

## [0.4.0] - 2026-04-12

### Added
- **Review summary** — general feedback not tied to a specific line (like GitHub PR review body)
- **Review modal** — "Finish review" button opens a modal with comment recap and summary textarea
- **Quick submit** — green button for immediate inline-comment-only submission (Ctrl+Shift+Enter)
- ReviewModal component with ARIA attributes (`role="dialog"`, `aria-modal`, `aria-labelledby`)
- Keyboard shortcut guard — Ctrl+Shift+Enter respects disabled button state
- E2E tests: modal submit, keyboard bypass prevention, Esc-close-and-preserve-body
- Self-review principles documented in AGENTS.md

### Changed
- Centralized Playwright page fixture with 5s timeout in conftest.py
- E2E tests refactored to use shared `page` fixture instead of manual browser management

## [0.3.1] - 2026-04-12

### Fixed
- Skill always upgrades CLI to latest on each run (no stale versions)
- Updated CONTRIBUTING.md with releasing steps and distribution channels

## [0.3.0] - 2026-04-12

### Added
- **Files mode** — review plain text files instead of git diffs (`claude-review --files plan.md`)
- `/review-ui plan` — review the current plan file before approving
- `ReviewMode` enum (diff, files) with mode-aware frontend rendering
- `TextFileService` — converts text files into reviewable content
- Flat file list sidebar for files mode (no tree structure, no diff badges)
- Simplified DiffView for non-diff modes (single line number column, no +/- prefixes)
- 20 new tests (unit, integration, E2E) for files mode

### Changed
- `create_app()` now requires explicit `mode` parameter (no silent default)
- `run()` accepts pre-loaded data instead of loading internally
- All `StrEnum` values use `auto()` instead of hardcoded strings
- Sidebar title derived from mode via lookup map (extensible for future modes)
- Diff-specific styling (row coloring, gutter classes) guarded by `isDiffMode`

## [0.2.0] - 2026-04-10

### Fixed
- Python 2 `except` syntax bug in git_repository.py (`except A, B:` → `except (A, B):`)
- Deprecated `asyncio.get_event_loop()` → `get_running_loop()`
- svelte-check warning in CommentBox (initialBody capture)

### Changed
- Replaced `xdg-open` subprocess with cross-platform `webbrowser.open()`
- Replaced closure-based DI with FastAPI `Depends()` pattern (presentation layer)
- Replaced fragile list holders with `ServerState` dataclass
- Made `diffStore.selectedFile` a `$derived` for proper reactivity

### Added
- structlog logging (silent by default, `--verbose` flag to enable)
- Pydantic field validators on `CommentInput` (positive lines, non-empty body, start ≤ end)
- 30s timeout on all git subprocess operations
- ESLint flat config for Svelte 5 + TypeScript (`eslint.config.js`)
- `diffStore.clear()` for test isolation
- Tests for heartbeat endpoint, state.result storage, and input validation (32 Python tests, 15 frontend tests)

### Removed
- Unused `pydantic-settings` dependency

## [0.1.0] - 2026-04-04

### Added
- Browser-based diff viewer with GitHub-style UI
- Syntax highlighting (Python, TypeScript, JS, CSS, HTML, Rust, Go, SQL, YAML, Markdown, Bash)
- Inline comments on single lines or drag-to-select ranges
- File tree sidebar with change stats (+/- per file)
- Comment navigation (prev/next)
- Light/dark theme toggle (auto-detects system preference)
- Auto-shutdown when browser tab is closed (heartbeat)
- Double-submit protection (409)
- Supports tracked, staged, and untracked files
- `/review-ui` slash command via `npx skills add`
- Claude Code plugin marketplace (`/plugin marketplace add vrppaul/claude-review`)
- CI: GitHub Actions (lint, Python tests, frontend tests, e2e, build verification)
- Pre-commit hooks: ruff, ty, bandit, conventional commits
- Auto-build frontend via hatch build hook (`uv build` builds both BE and FE)
- DDD-lite architecture: domain, services, repositories, presentation
- 29 Python tests (unit/integration/e2e with Playwright)
- 15 frontend tests (vitest)
