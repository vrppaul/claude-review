# TODO

Roadmap for the review-experience overhaul. Each item is one commit with its
tests. Remove items when done — don't check them off.

## Left from the overhaul

- [ ] `feat(ui)`: mark where a thread would be, in the file it belongs to.
      The bar lists the threads a narrower base cannot draw and takes the
      reader to any of them, so none is stranded — but inside a file that is
      on screen, one hanging on lines this base leaves out shows nothing at
      all. A dashed stub at the top of that file was drawn on the canvas.
- [ ] `feat(cli)`: say what is still waiting on this side. `context` prints
      the whole review as an index; what an agent actually needs between
      turns is the short list — questions asked and not answered, panel
      messages taken and not closed — so it can check itself rather than
      leave a message hanging with a Stop button on it. Found by leaving one
      hanging: answering "first" without naming the message never closes it.

- [ ] `perf(review)`: a retake stages the working tree three times — once to
      ask what changed, once for the diff itself, once to write the new mark.
      `_everything_staged` was built to serve several questions from one
      staging and this call site asks three separately, on the path the
      reader is waiting on. Startup pays it twice for the same reason.

- [ ] `test(ui)`: the base picker has no component test — the filter, the
      three sections, the loading and empty states, the error line, and
      whether a row says its size or its age. Nor do the marks it produces:
      the dot in the tree, the chip in the file header, "Show what changed".

- [ ] `feat(ui)`: let a turn be deleted. A comment can be removed and a
      thread resolved, but a reply — the reader's or the author's — stays
      whatever it says. A duplicate answer has no way out of the thread.

## Bugs

- [ ] `fix(server)`: a review nobody ever opened lives forever. The server
      winds down when the last browser leaves, and "leaves" needs one to
      have arrived: `_ever_connected` never turns true, so a `--no-open`
      review whose URL is never opened holds its port and ~35 MB until the
      machine is rebooted. Twelve of them were found running at once. Give
      an unopened review a deadline of its own.
- [ ] `fix(server)`: on SIGTERM the server releases its port but does not
      exit while a browser still holds a websocket, so a restart needs
      `kill -9`. Close the sockets as part of winding down.

## Infrastructure

- [ ] Submit to the official Claude Code plugin marketplace

## Testing

- [ ] Drop `tmp_path` from unit tests — services should accept data in memory
      so unit tests don't touch the filesystem

## Known limits

- A single generated file of ~12,000 lines takes about 2.6s to become
  readable, because a file is built as one unit. Splitting a hunk into
  separately contained blocks was measured and made it worse. Worth
  revisiting only if such files turn up in real reviews.
