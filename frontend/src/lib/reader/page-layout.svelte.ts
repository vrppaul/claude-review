/**
 * How this reader lays the page out: the file tree, the agent panel, and
 * how a renderable file is shown.
 *
 * None of these belong to a review — they are how this person reads this
 * page — so they are kept in this port's storage, not with the review and
 * not on the server.
 */

import {
  readChoice,
  readFlag,
  readNumber,
  writeChoice,
} from "$lib/utils/preferences";

/** How narrow and how wide a column may be, and how wide it starts. */
interface WidthBounds {
  min: number;
  max: number;
  fallback: number;
}

// Narrower than this and a path is unreadable; wider and the tree takes the
// room from the code it is a table of contents for
const FILE_TREE_WIDTH: WidthBounds = { min: 160, max: 560, fallback: 240 };
// Below this there is no room for a sentence; above it the diff — which the
// conversation is about — stops being readable
const AGENT_PANEL_WIDTH: WidthBounds = { min: 280, max: 720, fallback: 380 };

// The names each choice is kept under in this port's storage
const FILE_TREE_OPEN_KEY = "sidebar-open";
const FILE_TREE_WIDTH_KEY = "sidebar-width";
const AGENT_PANEL_OPEN_KEY = "panel-open";
const AGENT_PANEL_WIDTH_KEY = "panel-width";
const CONTENT_VIEW_KEY = "content-view";

/** Every way a renderable file can be shown: as text, rendered, or both side by side. */
export const CONTENT_VIEW_MODES = ["raw", "preview", "side-by-side"] as const;
export type ContentViewMode = (typeof CONTENT_VIEW_MODES)[number];
const FIRST_CONTENT_VIEW: ContentViewMode = "raw";

// Whether the reader has said if they want the agent panel: "unset" until
// they open or shut it themselves
const PANEL_CHOICES = ["on", "off"] as const;
type PanelChoice = (typeof PANEL_CHOICES)[number] | "unset";

/**
 * A column's width, held to its bounds and kept in this port's storage.
 *
 * A width saved on a wide screen must not leave a narrow one with no room
 * for the diff, so the bounds hold on the way in as well as on the way out.
 */
class StoredWidth {
  readonly #key: string;
  readonly #bounds: WidthBounds;
  #value: number;

  constructor(key: string, bounds: WidthBounds) {
    this.#key = key;
    this.#bounds = bounds;
    this.#value = $state(readNumber(key, bounds));
  }

  get value(): number {
    return this.#value;
  }

  set(next: number): void {
    const { min, max } = this.#bounds;
    this.#value = Math.min(max, Math.max(min, Math.round(next)));
    writeChoice(this.#key, this.#value);
  }
}

/** The file tree: on screen or put away, and how wide. */
export class FileTreeLayout {
  #open = $state(readFlag(FILE_TREE_OPEN_KEY, true));
  readonly #width = new StoredWidth(FILE_TREE_WIDTH_KEY, FILE_TREE_WIDTH);

  /** Whether the tree is on screen. Put away, it gives its room back. */
  get open(): boolean {
    return this.#open;
  }

  get width(): number {
    return this.#width.value;
  }

  toggle(): void {
    this.#open = !this.#open;
    writeChoice(FILE_TREE_OPEN_KEY, this.#open);
  }

  setWidth(next: number): void {
    this.#width.set(next);
  }
}

/**
 * The agent panel: open or shut, how wide, and how many answers landed
 * while it was shut, so the header can say so.
 */
export class AgentPanelLayout {
  #open: boolean;
  // Until the reader has said whether they want the panel, it opens itself
  // when an agent turns up and stays out of the way otherwise: an empty
  // panel beside a review nobody is answering is a column of nothing
  #chosen: boolean;
  #unread = $state(0);
  readonly #width = new StoredWidth(AGENT_PANEL_WIDTH_KEY, AGENT_PANEL_WIDTH);

  constructor() {
    const stored = readChoice<PanelChoice>(
      AGENT_PANEL_OPEN_KEY,
      PANEL_CHOICES,
      "unset",
    );
    this.#open = $state(stored === "on");
    this.#chosen = stored !== "unset";
  }

  get open(): boolean {
    return this.#open;
  }

  get width(): number {
    return this.#width.value;
  }

  /** Answers that landed while the panel was shut. */
  get unread(): number {
    return this.#unread;
  }

  setOpen(next: boolean): void {
    this.#open = next;
    this.#chosen = true;
    writeChoice(AGENT_PANEL_OPEN_KEY, next);
    if (next) this.#unread = 0;
  }

  toggle(): void {
    this.setOpen(!this.#open);
  }

  /** An agent has turned up; show the panel unless the reader shut it. */
  offer(): void {
    if (!this.#chosen) this.#open = true;
  }

  /** An answer landed in the conversation; count it if nobody can see it. */
  noteAnswer(): void {
    if (!this.#open) this.#unread += 1;
  }

  setWidth(next: number): void {
    this.#width.set(next);
  }
}

/** How a file that can be rendered is shown. */
export class ContentViewChoice {
  #mode = $state(
    readChoice(CONTENT_VIEW_KEY, CONTENT_VIEW_MODES, FIRST_CONTENT_VIEW),
  );

  get mode(): ContentViewMode {
    return this.#mode;
  }

  set(mode: ContentViewMode): void {
    this.#mode = mode;
    writeChoice(CONTENT_VIEW_KEY, mode);
  }
}

/** Everything about how the page is laid out, as this reader left it. */
export class PageLayout {
  readonly fileTree = new FileTreeLayout();
  readonly agentPanel = new AgentPanelLayout();
  readonly contentView = new ContentViewChoice();
}
