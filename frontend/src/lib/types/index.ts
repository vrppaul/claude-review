import type { components as HttpComponents } from "./generated/http";
import type { components as SocketComponents } from "./generated/socket";

/**
 * What the server sends and takes, generated from its own schemas by
 * `pnpm api:types`: one file for the routes, one for the session socket.
 * Named here once, so the rest of the browser imports a word rather than a
 * path into a generated file. What only the socket carries comes from
 * `socket.ts`; what the routes carry too comes from `http.ts`, the shape
 * being the same in both.
 */
type Schemas = HttpComponents["schemas"];
type SocketSchemas = SocketComponents["schemas"];

export type LineType = Schemas["LineType"];
/** Which version of the file a line belongs to. Removed lines are "old". */
export type LineSide = Schemas["LineSide"];
/** How the reader means a comment to be taken. */
export type CommentSeverity = Schemas["CommentSeverity"];
export type FileStatus = Schemas["FileStatus"];
export type ReviewMode = Schemas["ReviewMode"];
/** Whether a diff reads down one column or across two. */
export type DiffLayout = Schemas["DiffLayout"];
/** How the review is coloured: as the system says, or always light or dark. */
export type Theme = Schemas["Theme"];

/** How this reader reads a review, kept by the server for every review. */
export type ReaderSettings = Schemas["ReaderSettings"];
/** What the review remembers of having shown this reader around. */
export type GuideState = Schemas["GuideState"];

export type DiffLine = Schemas["DiffLine"];
export type DiffHunk = Schemas["DiffHunk"];
export type DiffFile = Schemas["DiffFile"];
/** What the review is and where it stands, read as the page opens. */
export type ReviewResponse = Schemas["ReviewResponse"];
export type DiffResponse = Schemas["DiffResponse"];
/** What the server takes — images, and the lines one comment covers — so the browser checks before sending. */
export type SendLimits = Schemas["SendLimits"];

/** Where a base came from, so a menu can group them. */
export type VersionKind = Schemas["VersionKind"];
/**
 * One base the working tree can be compared against: `label` is what a menu
 * row calls it, `phrase` what the header says while it is the one in force.
 */
export type ReviewVersion = Schemas["ReviewVersion"];

/**
 * What the agent has said about itself.
 *
 * None of it can be measured from this side, so every field is empty until
 * the agent reports, and the panel says when it last did.
 */
export type AgentStatus = Schemas["AgentStatus"];

/** Who wrote a turn: the reader, or whoever answers for the change. */
export type TurnAuthor = Schemas["TurnAuthor"];

export interface Turn {
  author: TurnAuthor;
  body: string;
  round: number;
  /** When it was said. Read in the thread, never sent with the review. */
  at?: number;
  /** Identity of this turn, so a question asked in it, and the answer, can name it. */
  id: string;
  /** Which question this answer belongs to. */
  answers?: string;
  /** Screenshots the reader pasted with it, by the id the server kept them under. */
  images: string[];
}

/** What is said in a thread after the comment that opened it, as it is written. */
export type NewTurn = Pick<Turn, "author" | "body" | "images">;

/**
 * Everything a thread can hang on; `$lib/anchors` names and finds each kind.
 * Held as the server writes it, quote and all; one sent back may leave the
 * quote out, and the server fills it in.
 */
export type Anchor = Schemas["Anchor-Output"];
/** What a thread can hang on. */
export type AnchorKind = Anchor["kind"];
/** Lines of one side of a file in the review's own diff. */
export type LineAnchor = Extract<Anchor, { kind: "line" }>;

/** A comment as the reader writes it, before it has an id and a place in time. */
export interface NewComment {
  anchor: Anchor;
  body: string;
  severity: CommentSeverity;
  images: string[];
}

/** A question handed over and not answered yet. */
export interface AwaitedQuestion {
  id: string;
  at: number;
}

/**
 * A thread hanging on something the reader reads: what it says.
 *
 * The comment that opened it stays in `body`; everything said afterwards is
 * a turn. How the page reads it — folded, unread, waiting on an answer — is
 * not part of it, and is kept apart.
 */
export interface Thread {
  id: string;
  anchor: Anchor;
  severity: CommentSeverity;
  body: string;
  /** Screenshots pasted with the comment, by the id the server kept them under. */
  images: string[];
  turns: Turn[];
  /** Who opened it. The author may point at a line too. */
  raised_by: TurnAuthor;
  resolved: boolean;
  /** Which round it was written in, so a thread can show where one ended. */
  round: number;
  /** When it was written. Read in the thread, never sent with the review. */
  at: number;
}

/**
 * A thread as the other side is told about it: what was said, not how it
 * was read. One shape wherever a thread travels — a round, a question, a
 * panel message, the review saying what it holds.
 */
export type ThreadInput = Schemas["ThreadInput"];
/** A turn as it goes back: what was said, with the images as ids. */
export type TurnInput = Schemas["TurnInput"];
export type SubmitRequest = Schemas["SubmitRequest"];
/**
 * A question asked in a thread. The whole thread goes, and the server
 * works out what is asked: the reader's last word, or the opening comment.
 */
export type AskRequest = Schemas["AskRequest"];
export type SubmitResponse = Schemas["SubmitResponse"];
export type MessageRequest = Schemas["MessageRequest"];
export type CancelRequest = Schemas["CancelRequest"];
/** Where each anchor asked about now hangs on the diff, in the order asked. */
export type FollowRequest = Schemas["FollowRequest"];
export type FollowResponse = Schemas["FollowResponse"];
export type FileWindowResponse = Schemas["FileWindowResponse"];
export type VersionsResponse = Schemas["VersionsResponse"];
/** The diff taken again: how many files, which round, and what changed since it began. */
export type RetakeResponse = Schemas["RetakeResponse"];
export type ImageResponse = Schemas["ImageResponse"];
/** The reader's choices, and whether any were kept yet: the server's `KeptRecord[ReaderSettings]`. */
export type KeptSettings = Schemas["KeptRecord_ReaderSettings_"];
/** The choices being changed, and only those. */
export type SettingsChange = Schemas["SettingsChange"];
/** How far the reader has been shown around, and whether that was kept yet: `KeptRecord[GuideState]`. */
export type KeptGuide = Schemas["KeptRecord_GuideState_"];
export type GuideChange = Schemas["GuideChange"];
/** What the review says over its socket, on connecting and whenever its threads change. */
export type SessionHello = SocketSchemas["SessionHello"];
/** What the server pushes down the socket, told apart by `type`. */
export type ServerPush = SocketSchemas["ServerPush"];
export type PointPush = SocketSchemas["PointPush"];
/** Which files changed since a round began, and which round that was. */
export type ChangesSince = Schemas["ChangesSince"];

/**
 * What the agent is doing right now, as the server last said it.
 *
 * Not a turn and not kept: the state of work in progress, replaced whenever
 * it changes. The server alone decides when it is over, and says so.
 */
export type AgentWork = SocketSchemas["AgentWork"];

/** One branch of the work: under way, or finished. */
export type ProgressStep = SocketSchemas["ProgressStep"];

/** What moving the threads onto a retaken diff did: how many followed their lines, how many lost them. */
export interface FollowOutcome {
  followed: number;
  outdated: number;
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
  /** Images the reader attached, by the id the server kept them under. */
  images?: string[];
  /** Which message an answer belongs to. */
  answers?: string;
  /** Taken back before it was answered. */
  cancelled?: boolean;
}

/** Which comment field: one on a line, a reply in a thread, or an edit. */
export type CommentKind = "new" | "reply" | "edit";

/** What happened to a comment field, for whoever follows along. */
export interface CommentFieldEvent {
  type: "opened" | "added" | "asked" | "closed";
  kind: CommentKind;
}

/** The panel message being written: its words and the images pasted into it. */
export interface Composer {
  text: string;
  /** Ids the server kept the images under. */
  images: string[];
}
