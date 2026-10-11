/**
 * What a kept draft looks like, in every shape it has ever been kept in,
 * and how an older one is brought up to the current shape.
 *
 * A comment has grown turns, a resolved mark, the lines it was written
 * against, the questions still waiting for an answer, and who raised it;
 * the review has grown a conversation in the agent panel, and the message
 * being written there; what a thread hangs on has moved into an anchor of
 * its own, and every turn carries an id a question can name; how a thread
 * is read — folded, unread, waited on — has moved out of the thread; the
 * draft says how far the server's telling had got for it; it keeps what
 * was being written in the threads and not said yet, which pasted images
 * each field uploaded itself, and which files were read and folded away;
 * and it is kept under the name the review gives itself rather than under
 * its title, which another review on the same port may share. A draft a
 * release kept is brought up to date — never thrown away: it is an hour of
 * somebody's reading. The shapes between the last released one and this
 * were never released, and are not read.
 */

import type {
	AwaitedQuestion,
	CommentSeverity,
	Composer,
	LineSide,
	PanelTurn,
	TellingPosition,
	Thread,
	Turn,
	WrittenAt
} from '$lib/types';
import { COMMENT_ID_PREFIX, IdSequence, TURN_ID_PREFIX } from '$lib/utils/ids';
import { READER } from '$lib/utils/speakers';

/** The shape drafts are kept in now. */
export const DRAFT_SHAPE = 16;

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

/** A comment being written when the draft was kept: where, and what it held. */
export interface KeptField {
	at: WrittenAt;
	text: string;
	severity: CommentSeverity;
	images: string[];
	/** Which of the images the field uploaded itself: the only ones it may let the server drop. */
	uploaded: string[];
}

/** The threads as a draft keeps them: what they say, how they were read, which went out, and what was being written. */
export interface KeptThreads {
	threads: Thread[];
	read: ThreadsRead;
	/** Comments, replies and edits being written, not said yet. */
	writing: KeptField[];
	/** The round each thread already sent went out in, by thread. */
	sent: Record<string, number>;
	/** How many thread and turn ids have been handed out, deleted ones included. */
	issued: IssuedIds;
}

/** How far the reader has got through the files, by path: those marked read, and those folded away. */
export interface FilesRead {
	viewed: string[];
	folded: string[];
}

/** An unsent review, as it is kept between reloads. */
export interface Draft extends KeptThreads {
	version: typeof DRAFT_SHAPE;
	reviewBody: string;
	/** What was said in the agent panel, which outlives a reload like the rest. */
	panel: PanelTurn[];
	/** What is being written in the panel, not yet sent. */
	composer: Composer;
	/**
	 * The last push the draft heard; none when nobody can tell. What each push
	 * up to it adds is in the draft — not the threads a retake moves, which
	 * follow a moment after its push is heard, and which a review opened from
	 * the draft follows again.
	 */
	told: TellingPosition | null;
	/** Which files the reader had read and folded away, which a reload used to undo. */
	files: FilesRead;
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
 * One draft was kept for every review on a port, told apart by the title.
 */
interface ReleasedDraft {
	version?: number;
	/** What the review was of, so a draft is not restored onto a different one. */
	title: string;
	comments: KeptComment[];
	reviewBody?: string;
	// Before rounds were numbered a sent thread was only an id
	sent?: (string | [string, number])[];
	panel?: PanelTurn[];
	composer?: Omit<Composer, 'uploaded'>;
	issued?: IssuedIds;
}

/**
 * Whether what was read from storage is a draft of the current shape.
 * Threads kept as threads in any other shape were never released.
 */
export function isCurrentDraft(value: unknown): value is Draft {
	return (
		typeof value === 'object' &&
		value !== null &&
		'version' in value &&
		value.version === DRAFT_SHAPE &&
		'threads' in value &&
		Array.isArray(value.threads)
	);
}

/** Whether what was read from storage is a draft a release kept, threads kept as comments. */
export function isReleasedDraft(value: unknown): value is ReleasedDraft {
	return (
		typeof value === 'object' &&
		value !== null &&
		'title' in value &&
		typeof value.title === 'string' &&
		'comments' in value &&
		Array.isArray(value.comments)
	);
}

function emptyComposer(): Composer {
	return { text: '', images: [], uploaded: [] };
}

/** The draft of a review nothing has been written in yet. */
export function emptyDraft(): Draft {
	return {
		version: DRAFT_SHAPE,
		threads: [],
		read: { folded: [], unread: [], awaiting: {} },
		writing: [],
		reviewBody: '',
		sent: {},
		panel: [],
		composer: emptyComposer(),
		issued: { comments: 0, turns: 0 },
		told: null,
		files: emptyFilesRead()
	};
}

function emptyFilesRead(): FilesRead {
	return { viewed: [], folded: [] };
}

/** A draft of the current shape, out of one a release kept, its threads as comments. */
export function upToDate(kept: ReleasedDraft): Draft {
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
		threads: comments.map(threadOf),
		read: {
			folded: comments.filter((comment) => comment.collapsed).map(idOf),
			unread: comments.filter((comment) => comment.unread).map(idOf),
			awaiting: Object.fromEntries(
				comments.filter((comment) => comment.awaiting.length > 0).map((comment) => [comment.id, comment.awaiting])
			)
		},
		// Nothing being written was kept until the fields were held by the review
		writing: [],
		reviewBody: kept.reviewBody ?? '',
		sent: Object.fromEntries((kept.sent ?? []).map((entry) => (typeof entry === 'string' ? [entry, 1] : entry))),
		// The panel came after threads did; an older draft simply has nothing said
		panel: kept.panel ?? [],
		// The panel kept nothing half-written until it could hold images
		// A composer kept before it said what it uploaded: its images count as handed in
		composer: kept.composer ? { ...kept.composer, uploaded: [] } : emptyComposer(),
		issued,
		told: null,
		// Which files were read was never kept before
		files: emptyFilesRead()
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
		raised_by: kept.raised_by ?? READER,
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
