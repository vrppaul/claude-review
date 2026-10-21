import type { components as HttpComponents } from './generated/http';
import type { components as SocketComponents } from './generated/socket';

/**
 * What the server sends and takes, generated from its own schemas by
 * `pnpm api:types`: one file for the routes, one for the session socket.
 * Named here once, so the rest of the browser imports a word rather than a
 * path into a generated file. What only the socket carries comes from
 * `socket.ts`; what the routes carry too comes from `http.ts`, the shape
 * being the same in both.
 */
type Schemas = HttpComponents['schemas'];
type SocketSchemas = SocketComponents['schemas'];

/** Which version of the file a line belongs to. Removed lines are "old". */
export type LineSide = Schemas['LineSide'];
/** How the reader means a comment to be taken. */
export type CommentSeverity = Schemas['CommentSeverity'];
export type FileStatus = Schemas['FileStatus'];
/**
 * Where the change under review is, one kind to each kind of review: a repository's change, with the
 * repository; or files or a conversation read once, called by the review's title.
 */
export type WhereTheChangeIs = Schemas['WhereTheChangeIs'];
/** What kind of review it is: the kind of where its change is. */
export type ReviewMode = WhereTheChangeIs['kind'];
/** Whether a diff reads down one column or across two. */
export type DiffLayout = Schemas['DiffLayout'];
/** How the review is coloured: as the system says, or always light or dark. */
export type Theme = Schemas['Theme'];

/** How this reader reads a review, kept by the server for every review. */
export type ReaderSettings = Schemas['ReaderSettings'];
/** What the review remembers of having shown this reader around. */
export type GuideState = Schemas['GuideState'];

export type DiffLine = Schemas['DiffLine'];
export type DiffHunk = Schemas['DiffHunk'];
export type DiffFile = Schemas['DiffFile'];
/** Why a file whose content changed shows none of its lines: not text, or too large to read. */
export type Unshown = Schemas['Unshown'];
/** What the review is and where it stands, read as the page opens. */
export type ReviewResponse = Schemas['ReviewResponse'];
/** What the repository of the change under review had checked out: a branch, or a commit on none. */
export type Checkout = Schemas['Checkout'];
export type DiffResponse = Schemas['DiffResponse'];
/** The story the review holds, if the agent told one. */
export type StoryResponse = Schemas['StoryResponse'];
/** The reader asking the agent for a story: when they asked, when an agent took the request, whether they stopped it. */
export type StoryAsking = Schemas['StoryAsking'];
/** A story as the review holds it: as told, and the round it was told in. */
export type StoryHeld = Schemas['StoryHeld'];
/** A story on the change it is told of: each step with the piece of its file it shows, and what no step tells. */
export type ToldStory = Schemas['ToldStory'];
export type FollowedChapter = Schemas['FollowedChapter'];
/** The change drawn, as Mermaid writes one, and the chapter each part of the drawing leads to, by the part's name. */
export type Diagram = Schemas['Diagram'];
export type FollowedStep = Schemas['FollowedStep'];
/** What a story leaves out of one file: the piece of it no step tells, and how many of its lines changed. */
export type LeftOut = Schemas['LeftOut'];
/** The base a diff was taken against: its key, what the header says, and whether it is narrower than the review's own. */
export type ShownBase = Schemas['ShownBase'];
/** What the server takes — images, the lines one comment covers, the length of what is written — so the browser checks before sending; and the largest file it shows line by line. */
export type SendLimits = Schemas['SendLimits'];

/** Where a base came from, so a menu can group them. */
export type VersionKind = Schemas['VersionKind'];
/**
 * One base the working tree can be compared against: `label` is what a menu
 * row calls it, `phrase` what the header says while it is the one in force.
 */
export type ReviewVersion = Schemas['ReviewVersion'];

/**
 * What the agent has said about itself.
 *
 * None of it can be measured from this side, so every field is empty until
 * the agent reports, and the panel says when it last did.
 */
export type AgentStatus = Schemas['AgentStatus'];

/** Who wrote a turn: the reader, or whoever answers for the change. */
export type TurnAuthor = Schemas['TurnAuthor'];

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
export type NewTurn = Pick<Turn, 'author' | 'body' | 'images'>;

/**
 * Everything a thread can hang on; `$lib/anchors` names and finds each kind.
 * Held as the server writes it, quote and all; one sent back may leave the
 * quote out, and the server fills it in.
 */
export type Anchor = Schemas['Anchor-Output'];
/** What a thread can hang on. */
export type AnchorKind = Anchor['kind'];
/** Lines of one side of a file in the review's own diff. */
export type LineAnchor = Extract<Anchor, { kind: 'line' }>;
/** A block of the words of the story told of the change. */
export type StoryAnchor = Extract<Anchor, { kind: 'story' }>;
/**
 * A block of the story's words, by a place that stays when the story is told
 * again: one of the overview's lines by its name, an item by where it stands
 * in its list, what a chapter says of itself by the chapter's id, a step's
 * reason by the step's file and first line.
 */
export type StoryBlock = StoryAnchor['block'];
/** One of the overview's three lines. */
export type OverviewText = Schemas['OverviewText'];
/** One of the overview's lists. */
export type OverviewList = Schemas['OverviewList'];
/** What a chapter says of itself under its title. */
export type ChapterText = Schemas['ChapterText'];

/**
 * Where a line of a diff is: the side it belongs to, and its number there.
 * A removed line is on the old side; every other line is on the new one.
 */
export interface LinePlace {
	side: LineSide;
	number: number;
}

/** Lines of one side picked to comment on, and the line the comment field opens under. */
export interface PickedLines {
	side: LineSide;
	startLine: number;
	endLine: number;
	/** Where the drag ended, so the field opens beside the pointer rather than at the far end of a long range. */
	opensBelow: LinePlace;
}

/**
 * Where a comment is being written: on lines of a file, on a block of the
 * story's words, as a reply in a thread, or over the comment that opened a
 * thread.
 */
export type WrittenAt =
	| {
			kind: 'new';
			file: string;
			lines: PickedLines;
			/** What the lines said when they were picked: the comment quotes them, and a suggestion starts from them. */
			quote: string[];
	  }
	| {
			kind: 'story';
			block: StoryBlock;
			/** What the block said when the reader asked about it: the comment quotes it. */
			words: string;
	  }
	| { kind: 'reply'; thread: string }
	| { kind: 'edit'; thread: string };

/** A comment being written on lines of a file. */
export type WrittenOnLines = Extract<WrittenAt, { kind: 'new' }>;
/** A comment being written on a block of the story's words. */
export type WrittenOnTheStory = Extract<WrittenAt, { kind: 'story' }>;

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
	/**
	 * When it was written. Read in the thread, never sent with the review —
	 * so one taken in from what the review holds does not say.
	 */
	at?: number;
}

/**
 * A thread as the other side is told about it: what was said, not how it
 * was read. One shape wherever a thread travels — a round, a question, a
 * panel message, the review saying what it holds.
 */
export type ThreadDraft = Schemas['ThreadDraft-Input'];
/** A turn as it goes back: what was said, with the images as ids. */
export type TurnDraft = Schemas['TurnDraft'];
/**
 * A thread the review holds, as a page last said it — every field there:
 * what a page that opens with no draft of the review takes in.
 */
export type HeldThread = Schemas['ThreadDraft-Output'];
/** The threads the review holds. */
export type ThreadsResponse = Schemas['ThreadsResponse'];
/**
 * Something said in the panel, as the review holds it: the reader's message
 * or the agent's words, under the id every page knows it by — what a page
 * opening draws, whatever its draft holds.
 */
export type SaidInPanel = Schemas['SaidInPanel'];
/** What was said in the panel, oldest first. */
export type ConversationResponse = Schemas['ConversationResponse'];
export type SubmitRequest = Schemas['SubmitRequest'];
/**
 * A question asked in a thread. The whole thread goes, and the server
 * works out what is asked: the reader's last word, or the opening comment.
 */
export type AskRequest = Schemas['AskRequest'];
export type SubmitResponse = Schemas['SubmitResponse'];
export type MessageRequest = Schemas['MessageRequest'];
export type CancelRequest = Schemas['CancelRequest'];
/** Where each anchor asked about now hangs on the diff, in the order asked. */
export type FollowRequest = Schemas['FollowRequest'];
export type FollowResponse = Schemas['FollowResponse'];
export type FileWindowResponse = Schemas['FileWindowResponse'];
export type VersionsResponse = Schemas['VersionsResponse'];
/** The diff taken again: how many files, which round, and what changed since it began. */
export type RetakeResponse = Schemas['RetakeResponse'];
export type ImageResponse = Schemas['ImageResponse'];
/** Why the server refused a request: in words, or field by field. */
export type Refusal = Schemas['Refusal'];
/** One field a refused request had wrong: its place in what was sent, and why. */
export type FieldRefusal = Schemas['FieldRefusal'];
/** The reader's choices, and whether any were kept yet: the server's `KeptRecord[ReaderSettings]`. */
export type KeptSettings = Schemas['KeptRecord_ReaderSettings_'];
/** The choices being changed, and only those. */
export type SettingsChange = Schemas['SettingsChange'];
/** How far the reader has been shown around, and whether that was kept yet: `KeptRecord[GuideState]`. */
export type KeptGuide = Schemas['KeptRecord_GuideState_'];
export type GuideChange = Schemas['GuideChange'];
/** What the review says over its socket, on connecting and whenever its threads change. */
export type SessionHello = SocketSchemas['SessionHello'];
/** Where a page coming back had got to, named in the socket's address as it opens it. */
export type Resume = SocketSchemas['Resume'];
/**
 * What the server says down the socket: a welcome on every connection, then
 * each push in a delivery numbered across the run of the review.
 */
export type SessionMessage = SocketSchemas['SessionMessage'];
export type Welcome = SocketSchemas['Welcome'];
export type Delivery = SocketSchemas['Delivery'];
/** What the server pushes down the socket, told apart by `type`. */
export type ServerPush = SocketSchemas['ServerPush'];
export type PointPush = SocketSchemas['PointPush'];
export type DiffPush = SocketSchemas['DiffPush'];
export type ChatPush = SocketSchemas['ChatPush'];

/**
 * How far the review's telling has got, as a page holds it: which run of the
 * review, and the number of the last push it covers. Numbers start again
 * with each run, so they mean nothing without it.
 */
export interface TellingPosition {
	instance: string;
	sequence: number;
}

/** Which files changed since a round began, and which round that was. */
export type ChangesSince = Schemas['ChangesSince'];

/**
 * What the agent is doing right now, as the server last said it.
 *
 * Not a turn and not kept: the state of work in progress, replaced whenever
 * it changes. The server alone decides when it is over, and says so.
 */
export type AgentWork = Schemas['AgentWork'];

/** What moving the threads onto a retaken diff did: how many followed their lines, how many lost them. */
export interface FollowOutcome {
	followed: number;
	outdated: number;
}

/** Who speaks in the panel. An event is the review itself saying so. */
export type PanelSpeaker = TurnAuthor | 'event';

/**
 * One turn of the panel conversation.
 *
 * The reader's turns keep the id the message was sent under, so an answer
 * that names it lands under the right one — several can be in flight, and
 * the reader goes on reading while the agent writes. The agent's keep the id
 * the review holds its words under, so a page that heard them and reads
 * them again as it opens draws them once.
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

/** What happened to a comment field, for whoever follows along. */
export interface CommentFieldEvent {
	type: 'opened' | 'added' | 'asked' | 'closed';
	/** Which field: one on lines, a reply in a thread, or an edit. */
	kind: WrittenAt['kind'];
}

/** The panel message being written: its words and the images pasted into it. */
export interface Composer {
	text: string;
	/** Ids the server kept the images under. */
	images: string[];
	/** Which of them were uploaded here, so a reload does not stop them being let go. */
	uploaded: string[];
}
