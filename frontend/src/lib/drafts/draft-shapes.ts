/**
 * What a kept draft looks like, in every shape it has ever been kept in,
 * and how an older one is brought up to the current shape.
 *
 * A comment has grown turns, a resolved mark, the lines it was written
 * against, the questions still waiting for an answer, and who raised it;
 * the review has grown a conversation in the agent panel, and the message
 * being written there; what a thread hangs on has moved into an anchor of
 * its own, and every turn carries an id a question can name; how a thread
 * is read — folded, unread, waited on — has moved out of the thread; and
 * the draft says how far the server's telling had got for it. A draft is
 * brought up to date — never thrown away: it is an hour of somebody's
 * reading.
 */

import type { AwaitedQuestion, Composer, LineSide, PanelTurn, TellingPosition, Thread, Turn } from '$lib/types';
import { COMMENT_ID_PREFIX, IdSequence, TURN_ID_PREFIX } from '$lib/utils/ids';

/** The shape drafts are kept in now. */
export const DRAFT_SHAPE = 13;
// The shapes that kept threads as threads, but sends and waits as pairs and
// the telling not at all or not as now. None was ever released; what they
// kept of the telling is not trusted.
const FIRST_SHAPE_OF_THREADS = 10;
const LAST_SHAPE_OF_PAIRS = 12;

/** How many ids of each kind the review has handed out. */
export interface IssuedIds {
	comments: number;
	turns: number;
}

/** How the page was reading the threads: folded, unread, and waiting on an answer. */
export interface ThreadsRead {
	folded: string[];
	unread: string[];
	/** Questions with the agent, oldest first, by the thread they were asked in. */
	awaiting: Record<string, AwaitedQuestion[]>;
}

/** The threads as a draft keeps them: what they say, how they were read, and which went out. */
export interface KeptThreads {
	threads: Thread[];
	read: ThreadsRead;
	/** The round each thread already sent went out in, by thread. */
	sent: Record<string, number>;
	/** How many thread and turn ids have been handed out, deleted ones included. */
	issued: IssuedIds;
}

/** An unsent review, as it is kept between reloads. */
export interface Draft extends KeptThreads {
	version: typeof DRAFT_SHAPE;
	/** What the review was of, so a draft is not restored onto a different one. */
	title: string;
	reviewBody: string;
	/** What was said in the agent panel, which outlives a reload like the rest. */
	panel: PanelTurn[];
	/** What is being written in the panel, not yet sent. */
	composer: Composer;
	/** The last push whose effect the draft holds; none when nobody can tell. */
	told: TellingPosition | null;
}

/** A draft as shapes 10 to 12 kept it: sends and waits as pairs, and the telling not trusted. */
interface PairedDraft extends Omit<Draft, 'version' | 'read' | 'sent' | 'told'> {
	version: number;
	read: { folded: string[]; unread: string[]; awaiting: [string, AwaitedQuestion[]][] };
	sent: [string, number][];
}

/** A thread as drafts kept it until how it was read moved out of it. */
interface ReadComment extends Thread {
	awaiting: AwaitedQuestion[];
	collapsed: boolean;
	unread: boolean;
}

/** A thread as drafts kept it before it hung on an anchor. */
interface FlatComment extends Omit<ReadComment, 'anchor'> {
	file: string;
	side: LineSide;
	start_line: number;
	end_line: number;
	// Missing from drafts written before quotes and outdated marks were kept
	quote?: string[];
	outdated?: boolean;
}

/** A turn as drafts kept it before every turn carried an id. */
type KeptTurn = Omit<Turn, 'id' | 'images'> & {
	id?: string;
	images?: string[];
};

/** Fields a thread grew after the first shape; one missing means the thread predates it. */
type GrownLater = 'images' | 'raised_by' | 'resolved' | 'awaiting' | 'collapsed' | 'unread' | 'round' | 'at';

/** A thread as a draft kept it, with any field it grew later possibly missing. */
type AsKept<Shape> = Omit<Shape, GrownLater | 'turns'> &
	Partial<Pick<ReadComment, GrownLater>> & { turns?: KeptTurn[] };

/** A thread in any shape before shape 10: on an anchor, or on lines alone. */
type KeptComment = AsKept<ReadComment> | AsKept<FlatComment>;

/**
 * A draft of a shape before 10, when threads were kept as comments with how
 * they were read inside them — one of shape 9 that kept no count of the ids
 * handed out included, since what it holds is all there is to count from.
 */
interface OlderDraft {
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

/** A draft in any shape it has been kept in. */
export type KeptDraft = Draft | PairedDraft | OlderDraft;

/** Whether what was read from storage is a draft at all, in any shape. */
export function isKeptDraft(value: unknown): value is KeptDraft {
	if (typeof value !== 'object' || value === null) return false;
	if (!('title' in value) || typeof value.title !== 'string') return false;
	if ('threads' in value) return Array.isArray(value.threads);
	return 'comments' in value && Array.isArray(value.comments);
}

function isCurrent(kept: KeptDraft): kept is Draft {
	return kept.version === DRAFT_SHAPE;
}

function isPaired(kept: KeptDraft): kept is PairedDraft {
	const version = kept.version ?? 0;
	return version >= FIRST_SHAPE_OF_THREADS && version <= LAST_SHAPE_OF_PAIRS;
}

function emptyComposer(): Composer {
	return { text: '', images: [] };
}

/** The draft of a review nothing has been written in yet. */
export function emptyDraft(title: string): Draft {
	return {
		version: DRAFT_SHAPE,
		title,
		threads: [],
		read: { folded: [], unread: [], awaiting: {} },
		reviewBody: '',
		sent: {},
		panel: [],
		composer: emptyComposer(),
		issued: { comments: 0, turns: 0 },
		told: null
	};
}

/** A draft of the current shape, whichever shape it was kept in. */
export function upToDate(kept: KeptDraft): Draft {
	if (isCurrent(kept)) return kept;
	if (isPaired(kept)) return fromPairs(kept);
	return fromComments(kept);
}

/** A draft of the current shape, out of one that kept sends and waits as pairs. */
function fromPairs(kept: PairedDraft): Draft {
	return {
		...kept,
		version: DRAFT_SHAPE,
		read: { ...kept.read, awaiting: Object.fromEntries(kept.read.awaiting) },
		sent: Object.fromEntries(kept.sent),
		// What it kept of the telling, if anything, nobody can trust now
		told: null
	};
}

/** A draft of the current shape, out of one that kept its threads as comments. */
function fromComments(kept: OlderDraft): Draft {
	// A turn that came without an id gets one past every id the draft holds,
	// the way the review hands them out
	const turnIds = new IdSequence(TURN_ID_PREFIX);
	turnIds.continuePast(kept.comments.flatMap((comment) => comment.turns ?? []).map((turn) => turn.id));
	const comments = kept.comments.map((comment) => upToDateComment(comment, turnIds));
	// Where a comment kept count of the ids handed out, it is believed
	const issued = kept.issued ?? {
		comments: commentIdsPast(kept.comments),
		turns: turnIds.issued
	};
	return {
		version: DRAFT_SHAPE,
		title: kept.title,
		threads: comments.map(threadOf),
		read: {
			folded: comments.filter((comment) => comment.collapsed).map(idOf),
			unread: comments.filter((comment) => comment.unread).map(idOf),
			awaiting: Object.fromEntries(
				comments.filter((comment) => comment.awaiting.length > 0).map((comment) => [comment.id, comment.awaiting])
			)
		},
		reviewBody: kept.reviewBody ?? '',
		sent: Object.fromEntries((kept.sent ?? []).map((entry) => (typeof entry === 'string' ? [entry, 1] : entry))),
		// The panel came after threads did; an older draft simply has nothing said
		panel: kept.panel ?? [],
		// The panel kept nothing half-written until it could hold images
		composer: kept.composer ?? emptyComposer(),
		issued,
		told: null
	};
}

/**
 * How many comment ids a draft had handed out, before it kept count: the
 * ids it holds are all there is to go on.
 */
function commentIdsPast(comments: KeptComment[]): number {
	const commentIds = new IdSequence(COMMENT_ID_PREFIX);
	commentIds.continuePast(comments.map(idOf));
	return commentIds.issued;
}

function idOf(kept: { id: string }): string {
	return kept.id;
}

/** What a comment said, without how it was read. */
function threadOf(comment: ReadComment): Thread {
	return {
		id: comment.id,
		anchor: comment.anchor,
		severity: comment.severity,
		body: comment.body,
		images: comment.images,
		turns: comment.turns,
		raised_by: comment.raised_by,
		resolved: comment.resolved,
		round: comment.round,
		at: comment.at
	};
}

/** A comment of shape 9, whichever older shape it was kept in. */
function upToDateComment(kept: KeptComment, turnIds: IdSequence): ReadComment {
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
			images: turn.images ?? []
		})),
		// Threads were all the reader's before the author could raise one
		raised_by: kept.raised_by ?? 'reader',
		resolved: kept.resolved ?? false,
		awaiting: kept.awaiting ?? [],
		collapsed: kept.collapsed ?? false,
		unread: kept.unread ?? false,
		round: kept.round ?? 1,
		at: kept.at ?? 0
	};
}

/** What a kept thread hangs on, whether it kept an anchor or the lines alone. */
function anchorOf(kept: KeptComment): Thread['anchor'] {
	if ('anchor' in kept) return kept.anchor;
	return {
		kind: 'line',
		file: kept.file,
		side: kept.side,
		start_line: kept.start_line,
		end_line: kept.end_line,
		quote: kept.quote ?? [],
		outdated: kept.outdated ?? false
	};
}
