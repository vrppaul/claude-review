/**
 * Where each file sits in the stream, and bringing one into view.
 *
 * The sidebar and the comment navigator move the reader by scrolling rather
 * than by swapping what is rendered, so find-in-page, text selection across
 * files and the browser's own history all keep working. Sections announce
 * themselves here instead of being looked up by selector, which keeps path
 * characters out of a query string.
 */

// Long enough to find what was pointed at, short enough not to become part
// of how the file looks
const MARKED_FOR = 2000;
// A smooth scroll that never ends — a scroll container that cannot reach the
// file, a tab put in the background mid-flight — must not swallow the mark
const SETTLE_WITHIN = 2000;
// How many frames in a row an element has to stay put to count as arrived
const STILL_FRAMES = 2;
// The class that draws the mark on a section somebody else pointed at
const MARKED_CLASS = "cr-marked";

/** A section marked as the one pointed at, and the timer that takes the mark off. */
interface Mark {
  element: HTMLElement;
  timer: ReturnType<typeof setTimeout>;
}

/**
 * Call back once an element has stopped moving.
 *
 * Where the element actually is, rather than which element is doing the
 * scrolling: a section sits inside whatever container the layout gives it,
 * and asking the element itself works wherever it ends up.
 */
class SettleWatch {
  readonly #element: HTMLElement;
  readonly #then: () => void;
  readonly #startedAt = performance.now();
  #previousTop = Number.NaN;
  #stillFor = 0;

  constructor(element: HTMLElement, then: () => void) {
    this.#element = element;
    this.#then = then;
  }

  /** Start looking, once a frame, until the element is still. */
  start(): void {
    requestAnimationFrame(() => this.#look());
  }

  #look(): void {
    const top = this.#element.getBoundingClientRect().top;
    this.#stillFor = top === this.#previousTop ? this.#stillFor + 1 : 0;
    this.#previousTop = top;

    const settled = this.#stillFor >= STILL_FRAMES;
    if (settled || performance.now() - this.#startedAt > SETTLE_WITHIN) {
      this.#then();
      return;
    }
    requestAnimationFrame(() => this.#look());
  }
}

export class FileSections {
  readonly #sections = new Map<string, HTMLElement>();
  // What is marked, so a second showing can take the mark off the first
  // rather than leave it lit, and so the first one's timer cannot put it out
  #marked: Mark | null = null;
  // Which showing is the current one: an earlier scroll may still be
  // settling when another arrives, and only the last one asked for is worth
  // marking
  #showing = 0;

  /** Say where a file's section is; returns how to take it back. */
  register(path: string, element: HTMLElement): () => void {
    this.#sections.set(path, element);
    return () => {
      if (this.#sections.get(path) === element) this.#sections.delete(path);
    };
  }

  scrollToFile(path: string): void {
    this.#sections.get(path)?.scrollIntoView({ block: "start" });
  }

  /**
   * Bring a file into view and mark it once it gets there.
   *
   * Somebody else moved this screen, so the file has to say "here" when it
   * arrives: a page that has jumped somewhere without a word leaves the
   * reader working out what they are looking at. The mark waits for the
   * scroll to stop — across sixty files a smooth scroll outlasts the mark
   * itself, and the reader would arrive to a file that had already finished
   * saying so.
   */
  showFile(path: string): void {
    const section = this.#sections.get(path);
    if (!section) return;

    const mine = ++this.#showing;
    this.#unmark();
    section.scrollIntoView({ behavior: "smooth", block: "start" });
    new SettleWatch(section, () => {
      if (mine === this.#showing) this.#mark(section);
    }).start();
  }

  /**
   * Bring a thread into view, building its file first if need be.
   *
   * A file's rows are only built once it has been near the viewport, so a
   * thread further down the review — restored from a draft, say — has no
   * element yet. Scrolling to the file makes one appear, and the thread can
   * be reached on the next frame.
   */
  scrollToThread(threadId: string, file: string): void {
    const found = document.getElementById(threadId);
    if (found) {
      found.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    this.scrollToFile(file);
    requestAnimationFrame(() =>
      document
        .getElementById(threadId)
        ?.scrollIntoView({ behavior: "smooth", block: "center" }),
    );
  }

  #mark(section: HTMLElement): void {
    // The class draws the mark; the attribute says it is there to whatever
    // reads the page rather than its styles
    section.classList.add(MARKED_CLASS);
    section.dataset.marked = "";
    this.#marked = {
      element: section,
      timer: setTimeout(() => this.#unmark(), MARKED_FOR),
    };
  }

  #unmark(): void {
    if (!this.#marked) return;
    clearTimeout(this.#marked.timer);
    this.#marked.element.classList.remove(MARKED_CLASS);
    delete this.#marked.element.dataset.marked;
    this.#marked = null;
  }
}
