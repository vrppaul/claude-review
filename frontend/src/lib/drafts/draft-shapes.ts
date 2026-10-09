/**
 * What a kept draft looks like, in every shape it has ever been kept in,
 * and how an older one is brought up to the current shape.
 *
 * A comment has grown turns, a resolved mark, the lines it was written
 * against, the questions still waiting for an answer, and who raised it;
 * the review has grown a conversation in the agent panel, and the message
 * being written there; what a thread hangs on has moved into an anchor of
 * its own, and every turn carries an id a question can name. A draft is
 * brought up to date — never thrown away: it is an hour of somebody's
 * reading.
 */

import type { Comment, Composer, LineSide, PanelTurn, Turn } from "$lib/types";
import { COMMENT_ID_PREFIX, IdSequence, TURN_ID_PREFIX } from "$lib/utils/ids";

/** The shape drafts are kept in now. */
export const DRAFT_SHAPE = 9;

/** How many ids of each kind the review has handed out. */
export interface IssuedIds {
  comments: number;
  turns: number;
}

/** An unsent review, as it is kept between reloads. */
export interface Draft {
  version: typeof DRAFT_SHAPE;
  /** What the review was of, so a draft is not restored onto a different one. */
  title: string;
  comments: Comment[];
  reviewBody: string;
  /** Threads already sent, and the round each went out in. */
  sent: [string, number][];
  /** What was said in the agent panel, which outlives a reload like the rest. */
  panel: PanelTurn[];
  /** What is being written in the panel, not yet sent. */
  composer: Composer;
  /** How many thread and turn ids have been handed out, deleted ones included. */
  issued: IssuedIds;
}

/** A thread as drafts kept it before it hung on an anchor. */
interface FlatComment extends Omit<Comment, "anchor"> {
  file: string;
  side: LineSide;
  start_line: number;
  end_line: number;
  // Missing from drafts written before quotes and outdated marks were kept
  quote?: string[];
  outdated?: boolean;
}

/** A turn as drafts kept it before every turn carried an id. */
type KeptTurn = Omit<Turn, "id" | "images"> & {
  id?: string;
  images?: string[];
};

/** Fields a thread grew after the first shape; one missing means the thread predates it. */
type GrownLater =
  | "images"
  | "raised_by"
  | "resolved"
  | "awaiting"
  | "collapsed"
  | "unread"
  | "round"
  | "at";

/** A thread as a draft kept it, with any field it grew later possibly missing. */
type AsKept<Shape> = Omit<Shape, GrownLater | "turns"> &
  Partial<Pick<Comment, GrownLater>> & { turns?: KeptTurn[] };

/** A thread in any shape a draft has kept one in: on an anchor, or on lines alone. */
type KeptComment = AsKept<Comment> | AsKept<FlatComment>;

/**
 * A draft in any shape it has been kept in: the current one, or an older
 * one — one of the current shape that kept no count of the ids handed out
 * included, since what it holds is all there is to count from.
 */
export interface KeptDraft {
  version?: number;
  title: string;
  comments: KeptComment[];
  reviewBody?: string;
  // Before rounds were numbered a sent thread was only an id
  sent?: (string | [string, number])[];
  panel?: PanelTurn[];
  composer?: Composer;
  issued?: IssuedIds;
}

/** Whether what was read from storage is a draft at all, in any shape. */
export function isKeptDraft(value: unknown): value is KeptDraft {
  if (typeof value !== "object" || value === null) return false;
  if (!("title" in value) || !("comments" in value)) return false;
  return typeof value.title === "string" && Array.isArray(value.comments);
}

/** Whether a kept draft is already in the current shape, nothing to bring up. */
function isCurrent(kept: KeptDraft): kept is Draft {
  return kept.version === DRAFT_SHAPE && kept.issued !== undefined;
}

export function emptyComposer(): Composer {
  return { text: "", images: [] };
}

/** A draft of the current shape, whichever shape it was kept in. */
export function upToDate(kept: KeptDraft): Draft {
  if (isCurrent(kept)) return kept;
  // A turn that came without an id gets one past every id the draft holds,
  // the way the review hands them out
  const turnIds = new IdSequence(TURN_ID_PREFIX);
  turnIds.continuePast(
    kept.comments
      .flatMap((comment) => comment.turns ?? [])
      .map((turn) => turn.id),
  );
  const comments = kept.comments.map((comment) =>
    upToDateComment(comment, turnIds),
  );
  // Before the draft kept how many were handed out, the ids it holds are all
  // there is to go on
  const commentIds = new IdSequence(COMMENT_ID_PREFIX);
  commentIds.continuePast(kept.comments.map((comment) => comment.id));
  return {
    version: DRAFT_SHAPE,
    title: kept.title,
    comments,
    reviewBody: kept.reviewBody ?? "",
    sent: (kept.sent ?? []).map((entry) =>
      typeof entry === "string" ? [entry, 1] : entry,
    ),
    // The panel came after threads did; an older draft simply has nothing said
    panel: kept.panel ?? [],
    // The panel kept nothing half-written until it could hold images
    composer: kept.composer ?? emptyComposer(),
    issued: { comments: commentIds.issued, turns: turnIds.issued },
  };
}

/** A thread of the current shape, whichever shape it was kept in. */
function upToDateComment(kept: KeptComment, turnIds: IdSequence): Comment {
  return {
    id: kept.id,
    anchor: anchorOf(kept),
    severity: kept.severity,
    body: kept.body,
    // Comments were words alone until images could be pasted into them
    images: kept.images ?? [],
    turns: (kept.turns ?? []).map((turn) => ({
      ...turn,
      id: turn.id ?? turnIds.next(),
      images: turn.images ?? [],
    })),
    // Threads were all the reader's before the author could raise one
    raised_by: kept.raised_by ?? "reader",
    resolved: kept.resolved ?? false,
    awaiting: kept.awaiting ?? [],
    collapsed: kept.collapsed ?? false,
    unread: kept.unread ?? false,
    round: kept.round ?? 1,
    at: kept.at ?? 0,
  };
}

/** What a kept thread hangs on, whether it kept an anchor or the lines alone. */
function anchorOf(kept: KeptComment): Comment["anchor"] {
  if ("anchor" in kept) return kept.anchor;
  return {
    kind: "line",
    file: kept.file,
    side: kept.side,
    start_line: kept.start_line,
    end_line: kept.end_line,
    quote: kept.quote ?? [],
    outdated: kept.outdated ?? false,
  };
}
