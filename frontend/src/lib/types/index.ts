export type LineType = "context" | "add" | "delete";
/** Which version of the file a line belongs to. Removed lines are "old". */
export type LineSide = "old" | "new";
/** How the reader means a comment to be taken. */
export type CommentSeverity = "note" | "question" | "blocker";
export type FileStatus = "modified" | "added" | "deleted" | "renamed";
export type ReviewMode = "diff" | "files" | "transcript";
export type ContentViewMode = "raw" | "preview" | "side-by-side";
/** Whether a diff reads down one column or across two. */
export type DiffLayout = "unified" | "split";

export interface DiffLine {
  type: LineType;
  old_no: number | null;
  new_no: number | null;
  content: string;
}

export interface DiffHunk {
  header: string;
  old_start: number;
  new_start: number;
  lines: DiffLine[];
}

export interface DiffFile {
  path: string;
  status: FileStatus;
  hunks: DiffHunk[];
  is_binary: boolean;
  old_mode: string | null;
  new_mode: string | null;
}

export interface DiffResponse {
  files: DiffFile[];
  mode: ReviewMode;
  title: string;
  round: number;
  answerer_attached: boolean;
  agent: AgentStatus;
}

/**
 * What the agent has said about itself.
 *
 * None of it can be measured from this side, so every field is empty until
 * the agent reports, and the panel says when it last did.
 */
export interface AgentStatus {
  model: string | null;
  context: string | null;
  /** When it was reported, in epoch milliseconds. */
  at: number | null;
}

/** Who wrote a turn: the reader, or whoever answers for the change. */
export type TurnAuthor = "reader" | "author";

export interface Turn {
  author: TurnAuthor;
  body: string;
  round: number;
  /** When it was said. Read in the thread, never sent with the review. */
  at?: number;
  /** Identity of this turn, so an answer can name what it answers. */
  id?: string;
  /** Which question this answer belongs to. */
  answers?: string;
}

/** A question handed over and not answered yet. */
export interface Awaited {
  id: string;
  at: number;
}

/**
 * A thread hanging on a line or range.
 *
 * The comment that opened it stays in `body`; everything said afterwards is
 * a turn. The last four fields never leave the browser — they are how the
 * thread is read, not what it says.
 */
export interface Comment {
  id: string;
  file: string;
  side: LineSide;
  severity: CommentSeverity;
  start_line: number;
  end_line: number;
  body: string;
  turns: Turn[];
  /** Who opened it. The author may point at a line too. */
  raised_by: TurnAuthor;
  resolved: boolean;
  outdated: boolean;
  /** The lines it was written against, kept for when they are gone. */
  quote: string[];
  /** Questions with the author and not answered yet, oldest first. */
  awaiting: Awaited[];
  /** Folded away by the reader, to get its space back without settling it. */
  collapsed: boolean;
  /** An answer arrived that has not been looked at. */
  unread: boolean;
  /** Which round it was written in, so a thread can show where one ended. */
  round: number;
  /** When it was written. Read in the thread, never sent with the review. */
  at: number;
}

/** A thread as it goes back: what was said, not how it was read. */
export type CommentPayload = Omit<
  Comment,
  "id" | "awaiting" | "unread" | "collapsed" | "round" | "at" | "turns"
> & { turns: Omit<Turn, "at" | "id" | "answers">[] };

export interface SubmitRequest {
  comments: CommentPayload[];
  body?: string;
  end?: boolean;
}

export interface SubmitResponse {
  markdown: string;
  comment_count: number;
  round: number;
  ended: boolean;
}

/**
 * What the agent is doing right now.
 *
 * Not a turn and not kept: it is the state of work in progress, replaced
 * whenever it changes and gone when the work is.
 */
export interface Progress {
  text: string;
  files: string[];
  at: number;
}

/** Who speaks in the panel. An event is the review itself saying so. */
export type PanelSpeaker = TurnAuthor | "event";

/**
 * One turn of the panel conversation.
 *
 * The reader's turns keep the id the message was sent under, so an answer
 * that names it lands under the right one — several can be in flight, and
 * the reader goes on reading while the agent writes.
 */
export interface PanelTurn {
  id: string;
  author: PanelSpeaker;
  body: string;
  at: number;
  /** Threads this message pointed at, by id. */
  threads?: string[];
  /** Files worth opening at what was said. */
  files?: string[];
  /** Which message an answer belongs to. */
  answers?: string;
  /** Taken back before it was answered. */
  cancelled?: boolean;
}
