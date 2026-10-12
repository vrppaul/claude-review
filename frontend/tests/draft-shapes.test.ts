import { describe, it, expect, vi } from 'vitest';
import fastCheck from 'fast-check';
import { DRAFT_SHAPE, emptyDraft, isCurrentDraft, isReleasedDraft, type Draft } from '$lib/drafts/draft-shapes';
import { forgetDraft, keepDraft, readDraft } from '$lib/drafts/draft-storage';
import { lineAnchor } from '$lib/anchors/line';
import type { AwaitedQuestion, Thread } from '$lib/types';
import { REVIEW_TITLE } from './diff';
import { REVIEW_IDENTITY, THIS_RUN } from './fake-socket';
import { newComment } from './new-comment';
import { openReview } from './review';
import { DRAFT_KEY, RELEASED_DRAFT_KEY, storeDraft, storeReleasedDraft } from './stored-draft';

/** The last shape a draft had before its threads hung on anchors. */
const BEFORE_ANCHORS = 7;
/** The last shape a draft had before every turn carried an id. */
const BEFORE_TURN_IDS = 8;
/** The shape every turn carries an id in, and the draft counts the ids handed out. */
const SHAPE_WITH_TURN_IDS = 9;
/** A shape between the last one released and this one, which no release ever kept. */
const NEVER_RELEASED = 15;
/** What another review on the same port is of. */
const ANOTHER_TITLE = 'other-repo: changes since v1';

/** Fields of a comment no draft before them kept: one missing means the comment predates it. */
const GROWN_SINCE_THE_FIRST_SHAPE = [
	'images',
	'turns',
	'raised_by',
	'resolved',
	'outdated',
	'quote',
	'awaiting',
	'collapsed',
	'unread',
	'round',
	'at'
] as const;
/** Fields of a draft no draft before them kept. */
const KEPT_SINCE_THE_FIRST_SHAPE = ['version', 'reviewBody', 'sent', 'panel', 'composer'] as const;

/** A copy of what was kept, without some of its fields. */
function without(kept: object, fields: readonly string[]): object {
	return Object.fromEntries(Object.entries(kept).filter(([field]) => !fields.includes(field)));
}

/** Put a draft in storage as an older release of the review left it: the one draft of the port, under its title. */
function keptByAnOlderRelease(draft: object) {
	storeReleasedDraft({ title: REVIEW_TITLE, reviewBody: '', ...draft });
}

/** The draft of the review a test opens, as the page would read it now. */
function readKept(): Draft | null {
	return readDraft(REVIEW_IDENTITY, REVIEW_TITLE).draft;
}

/** A thread as an older release kept it, before it hung on an anchor. */
function flatThread(kept: object = {}) {
	return {
		id: 'comment-1',
		file: 'a.py',
		side: 'new',
		severity: 'note',
		start_line: 1,
		end_line: 1,
		body: 'written a while ago',
		...kept
	};
}

/** A thread as shape 9 kept it, with how it was read inside it. */
interface KeptComment extends Thread {
	awaiting: AwaitedQuestion[];
	collapsed: boolean;
	unread: boolean;
}

/** A thread with every field this release keeps filled in. */
function fullThread(): Thread {
	return {
		id: 'comment-1',
		anchor: lineAnchor('a.py', 'new', 3, 4, ['x = 1', 'y = 2']),
		severity: 'question',
		body: 'Why both?',
		images: ['opening.png'],
		turns: [{ id: 'turn-1', author: 'author', body: 'History', round: 2, at: 50, images: [] }],
		raised_by: 'reader',
		resolved: false,
		round: 2,
		at: 30
	};
}

/** The same thread as shape 9 kept it, folded, unread, and with a question waiting. */
function keptComment(): KeptComment {
	return {
		...fullThread(),
		awaiting: [{ id: 'comment-1', at: 40 }],
		collapsed: true,
		unread: true
	};
}

/**
 * A draft as v1.5.0 — the last release, the one whose drafts readers hold
 * now — wrote it with `saveDraft`, copied field for field from what that
 * release's `Draft`, `Comment`, `Turn`, `PanelTurn` and `Composer` held:
 * shape 7, the one draft of the port, told apart by title. Each comment
 * carries how it was read; a sent thread is an [id, round] pair; the panel
 * keeps what was said and the message half written there.
 */
const WRITTEN_BY_1_5_0 = {
	version: 7,
	title: REVIEW_TITLE,
	comments: [
		{
			id: 'comment-2',
			file: 'src/a.py',
			side: 'new',
			severity: 'question',
			start_line: 3,
			end_line: 4,
			body: 'Why both?',
			images: ['opening.png'],
			turns: [
				{ id: 'turn-1', author: 'reader', body: 'Still unsure', round: 1, at: 1000, images: [] },
				{ id: 'turn-2', author: 'author', body: 'History', round: 1, at: 1100, answers: 'turn-1', images: [] },
				{ id: 'turn-3', author: 'reader', body: 'And this?', round: 2, at: 1150, images: ['shot.png'] }
			],
			raised_by: 'reader',
			resolved: false,
			outdated: false,
			quote: ['x = 1', 'y = 2'],
			awaiting: [{ id: 'turn-3', at: 1150 }],
			collapsed: true,
			unread: true,
			round: 1,
			at: 900
		},
		{
			id: 'raised-1',
			file: 'src/b.py',
			side: 'old',
			severity: 'note',
			start_line: 7,
			end_line: 7,
			body: 'This went',
			images: [],
			turns: [],
			raised_by: 'author',
			resolved: true,
			outdated: true,
			quote: ['gone()'],
			awaiting: [],
			collapsed: false,
			unread: false,
			round: 2,
			at: 1120
		}
	],
	reviewBody: 'Overall fine',
	sent: [
		['comment-2', 1],
		['raised-1', 2]
	],
	panel: [
		{ id: 'message-1', author: 'reader', body: 'Run the tests', at: 1200, threads: ['comment-2'], images: ['run.png'] },
		{ id: 'message-2', author: 'author', body: 'They pass', at: 1300, files: ['src/a.py'], answers: 'message-1' },
		{ id: 'message-3', author: 'reader', body: 'Never mind', at: 1400, cancelled: true }
	],
	composer: { text: 'half a thought', images: ['pasted.png'] }
};

/** The draft v1.5.0 wrote, in the shape this release keeps: nothing it held is lost. */
const UP_TO_DATE_1_5_0: Draft = {
	version: DRAFT_SHAPE,
	threads: [
		{
			id: 'comment-2',
			anchor: lineAnchor('src/a.py', 'new', 3, 4, ['x = 1', 'y = 2']),
			severity: 'question',
			body: 'Why both?',
			images: ['opening.png'],
			turns: WRITTEN_BY_1_5_0.comments[0].turns,
			raised_by: 'reader',
			resolved: false,
			round: 1,
			at: 900
		},
		{
			id: 'raised-1',
			anchor: { ...lineAnchor('src/b.py', 'old', 7, 7, ['gone()']), outdated: true },
			severity: 'note',
			body: 'This went',
			images: [],
			turns: [],
			raised_by: 'author',
			resolved: true,
			round: 2,
			at: 1120
		}
	],
	read: { folded: ['comment-2'], unread: ['comment-2'], awaiting: { 'comment-2': [{ id: 'turn-3', at: 1150 }] } },
	writing: [],
	reviewBody: 'Overall fine',
	sent: { 'comment-2': 1, 'raised-1': 2 },
	panel: WRITTEN_BY_1_5_0.panel,
	composer: { text: 'half a thought', images: ['pasted.png'], uploaded: [] },
	// It kept no count: the comment ids and turn ids it holds are all there is
	issued: { comments: 2, turns: 3 },
	told: null,
	files: { viewed: [], folded: [] },
	// The reader's thread went out in round 1; the agent's arriving in 2 says nothing of a round sent
	round: 2
};

describe('the draft the last release kept, as it wrote it', () => {
	it('comes back in the current shape with everything it held', () => {
		storeReleasedDraft(WRITTEN_BY_1_5_0);

		expect(readKept()).toEqual(UP_TO_DATE_1_5_0);
	});

	it('is kept in the current shape once picked up, and read back as kept', () => {
		storeReleasedDraft(WRITTEN_BY_1_5_0);

		readKept();

		expect(JSON.parse(localStorage.getItem(DRAFT_KEY) ?? 'null')).toEqual(UP_TO_DATE_1_5_0);
		expect(readKept()).toEqual(UP_TO_DATE_1_5_0);
	});

	it('opens the review where the reader left it', () => {
		storeReleasedDraft(WRITTEN_BY_1_5_0);

		const review = openReview();

		expect(review.threads.all.map((thread) => thread.id)).toEqual(['comment-2', 'raised-1']);
		expect(review.threads.reading.isFolded('comment-2')).toBe(true);
		expect(review.threads.unsent).toEqual([]);
		expect(review.rounds.current).toBe(2);
		expect(review.conversation.composer.text).toBe('half a thought');
		expect(review.conversation.turns.map((turn) => turn.body)).toEqual(['Run the tests', 'They pass', 'Never mind']);
	});

	it('is brought up to date whichever of the fields grown since its first shape it lacks', () => {
		fastCheck.assert(
			fastCheck.property(
				fastCheck.subarray([...GROWN_SINCE_THE_FIRST_SHAPE]),
				fastCheck.subarray([...KEPT_SINCE_THE_FIRST_SHAPE]),
				(commentLacks, draftLacks) => {
					localStorage.clear();
					const comments = WRITTEN_BY_1_5_0.comments.map((comment) => without(comment, commentLacks));
					storeReleasedDraft(without({ ...WRITTEN_BY_1_5_0, comments }, draftLacks));

					const draft = readKept();

					expect(draft?.threads.map((thread) => thread.body)).toEqual(['Why both?', 'This went']);
					expect(isCurrentDraft(draft)).toBe(true);
				}
			)
		);
	});
});

describe('a draft this release kept', () => {
	it('comes back as it was kept', () => {
		const kept: Draft = {
			version: DRAFT_SHAPE,
			threads: [fullThread()],
			read: { folded: ['comment-1'], unread: [], awaiting: { 'comment-1': [{ id: 'comment-1', at: 40 }] } },
			writing: [
				{
					at: { kind: 'reply', thread: 'comment-1' },
					text: 'and another thing',
					severity: 'note',
					images: [],
					uploaded: []
				},
				{
					at: {
						kind: 'new',
						file: 'a.py',
						lines: { side: 'new', startLine: 3, endLine: 4, opensBelow: { side: 'new', number: 4 } }
					},
					text: 'half a comment',
					severity: 'question',
					images: ['pasted.png'],
					uploaded: ['pasted.png']
				}
			],
			reviewBody: 'Overall fine',
			sent: { 'comment-1': 2 },
			panel: [{ id: 'message-1', author: 'reader', body: 'Run the tests', at: 60, images: [] }],
			composer: { text: 'half a thought', images: ['pasted.png', 'handed.png'], uploaded: ['pasted.png'] },
			issued: { comments: 3, turns: 5 },
			told: { instance: THIS_RUN, sequence: 4 },
			files: { viewed: ['a.py'], folded: ['a.py', 'b.py'] },
			round: 3
		};

		keepDraft(REVIEW_IDENTITY, kept);

		expect(readKept()).toEqual(kept);
	});
});

describe('a draft of a shape no release kept', () => {
	it('is not read, rather than read as something it is not', () => {
		const unreleased = {
			version: NEVER_RELEASED,
			title: REVIEW_TITLE,
			threads: [fullThread()],
			read: { folded: [], unread: [], awaiting: {} },
			sent: { 'comment-1': 2 }
		};
		storeDraft(unreleased);
		storeReleasedDraft(unreleased);

		expect(isCurrentDraft(unreleased)).toBe(false);
		expect(isReleasedDraft(unreleased)).toBe(false);
		expect(readKept()).toBeNull();
	});
});

describe('the draft an older release kept, the one of its port', () => {
	it('is picked up by the review of its title, and only once', () => {
		keptByAnOlderRelease({ comments: [flatThread({ body: 'written before reviews named themselves' })] });

		const picked = readKept();
		const again = readDraft('another-review-of-the-same-title', REVIEW_TITLE).draft;

		expect(picked?.threads.map((thread) => thread.body)).toEqual(['written before reviews named themselves']);
		expect(again).toBeNull();
		expect(localStorage.getItem(RELEASED_DRAFT_KEY)).toBeNull();
	});

	it('is kept under the name of the review that picked it up', () => {
		keptByAnOlderRelease({ comments: [flatThread()] });

		readKept();

		expect(readKept()?.threads).toHaveLength(1);
	});

	it('is left for its own review by a review of another title', () => {
		keptByAnOlderRelease({ title: ANOTHER_TITLE, comments: [flatThread()] });

		expect(readKept()).toBeNull();
		expect(readDraft('the-other-review', ANOTHER_TITLE).draft?.threads).toHaveLength(1);
	});
});

/** What was set aside from a key, oldest first, as it was kept. */
function setAsideFrom(key: string): (string | null)[] {
	const keys = Array.from({ length: localStorage.length }, (_, index) => localStorage.key(index) ?? '');
	return keys
		.filter((kept) => kept.startsWith(`${key}:unreadable:`))
		.sort()
		.map((kept) => localStorage.getItem(kept));
}

describe('a kept draft that cannot be brought up to date', () => {
	it('is set aside as it was kept and told to the console, and the review opens without it', () => {
		keptByAnOlderRelease({ comments: [null] });
		const asItWasKept = localStorage.getItem(RELEASED_DRAFT_KEY);
		const told = vi.spyOn(console, 'error').mockImplementation(() => undefined);

		const kept = readDraft(REVIEW_IDENTITY, REVIEW_TITLE);

		expect(kept).toEqual({ draft: null, setAside: true });
		expect(localStorage.getItem(RELEASED_DRAFT_KEY)).toBeNull();
		expect(setAsideFrom(RELEASED_DRAFT_KEY)).toEqual([asItWasKept]);
		expect(told).toHaveBeenCalledWith(expect.any(String), expect.any(TypeError));
	});

	it('locks nobody out: the next page opens with no draft and nothing more to say', () => {
		keptByAnOlderRelease({ comments: [null] });
		vi.spyOn(console, 'error').mockImplementation(() => undefined);
		readKept();

		expect(readDraft(REVIEW_IDENTITY, REVIEW_TITLE)).toEqual({ draft: null, setAside: false });
	});

	it('is never written over, by the draft kept after it or by another set aside later', () => {
		keptByAnOlderRelease({ comments: [null] });
		const first = localStorage.getItem(RELEASED_DRAFT_KEY);
		vi.spyOn(console, 'error').mockImplementation(() => undefined);
		readKept();
		keepDraft(REVIEW_IDENTITY, emptyDraft(1));
		expect(setAsideFrom(RELEASED_DRAFT_KEY)).toEqual([first]);

		forgetDraft(REVIEW_IDENTITY);
		keptByAnOlderRelease({ comments: [null], reviewBody: 'written later' });
		const second = localStorage.getItem(RELEASED_DRAFT_KEY);
		readKept();

		expect(setAsideFrom(RELEASED_DRAFT_KEY)).toEqual([first, second]);
	});
});

describe('a draft written by an older release', () => {
	it('is brought up to the current shape rather than thrown away', () => {
		keptByAnOlderRelease({ comments: [flatThread({ body: 'written before threads existed' })] });

		const draft = readKept();

		expect(draft?.threads[0].body).toBe('written before threads existed');
		expect(draft?.threads[0].turns).toEqual([]);
		expect(draft?.read).toEqual({ folded: [], unread: [], awaiting: {} });
		expect(draft?.sent).toEqual({});
	});

	it('keeps how each thread was being read, apart from what it says', () => {
		keptByAnOlderRelease({ version: SHAPE_WITH_TURN_IDS, comments: [keptComment()], sent: [] });

		const draft = readKept();

		expect(draft?.threads).toEqual([fullThread()]);
		expect(draft?.read).toEqual({
			folded: ['comment-1'],
			unread: ['comment-1'],
			awaiting: { 'comment-1': [{ id: 'comment-1', at: 40 }] }
		});
	});

	it('keeps where each thread hung, and what it was written against', () => {
		keptByAnOlderRelease({
			version: BEFORE_ANCHORS,
			comments: [
				flatThread({
					side: 'old',
					severity: 'question',
					start_line: 4,
					end_line: 6,
					quote: ['a', 'b', 'c'],
					outdated: true
				})
			]
		});

		const [comment] = readKept()?.threads ?? [];

		expect(comment.anchor).toEqual({
			kind: 'line',
			file: 'a.py',
			side: 'old',
			start_line: 4,
			end_line: 6,
			quote: ['a', 'b', 'c'],
			outdated: true
		});
		expect(Object.keys(comment)).not.toContain('start_line');
		expect(Object.keys(comment)).not.toContain('quote');
	});

	it("has reached the round after the last one a thread of the reader's went out in, not one the agent raised", () => {
		keptByAnOlderRelease({
			comments: [flatThread(), flatThread({ id: 'raised-1', raised_by: 'author', round: 3 })],
			sent: [
				['comment-1', 2],
				['raised-1', 3]
			]
		});

		expect(readKept()?.round).toBe(3);
	});

	it('counts a thread sent before rounds were numbered as sent in the first', () => {
		keptByAnOlderRelease({ comments: [flatThread()], sent: ['comment-1'] });

		expect(readKept()?.sent).toEqual({ 'comment-1': 1 });
	});

	it('gives a turn written before images could be pasted no images', () => {
		keptByAnOlderRelease({
			comments: [flatThread({ turns: [{ author: 'author', body: 'Done', round: 1 }] })]
		});

		expect(readKept()?.threads[0].turns).toEqual([
			{ id: 'turn-1', author: 'author', body: 'Done', round: 1, images: [] }
		]);
	});

	it('is restored when it is of this shape but kept no count of the ids handed out', () => {
		keptByAnOlderRelease({ version: SHAPE_WITH_TURN_IDS, comments: [keptComment()], sent: [] });

		const review = openReview();
		const count = review.restoredCount;

		expect(count).toBe(1);
		expect(review.threads.add(newComment({ body: 'next' }))).not.toBe(fullThread().id);
	});

	it('gives each turn written before turns had ids one of its own, never one a turn already has', () => {
		keptByAnOlderRelease({
			version: BEFORE_TURN_IDS,
			comments: [
				{
					...keptComment(),
					turns: [
						{ author: 'reader', body: 'Why?', round: 1, images: [] },
						{ id: 'turn-4', author: 'author', body: 'Because', round: 1, images: [] }
					]
				}
			]
		});

		const ids = readKept()?.threads[0].turns.map((turn) => turn.id);

		expect(ids).toEqual(['turn-5', 'turn-4']);
	});

	it('starts the agent panel empty when the draft predates it', () => {
		keptByAnOlderRelease({ comments: [flatThread()] });

		const draft = readKept();

		expect(draft?.panel).toEqual([]);
		expect(draft?.composer).toEqual({ text: '', images: [], uploaded: [] });
	});

	it('keeps what was said in the panel when the draft predates the composer', () => {
		const said = { id: 'message-1', author: 'reader', body: 'Run the tests', at: 60 };
		keptByAnOlderRelease({ comments: [flatThread()], panel: [said] });

		const draft = readKept();

		expect(draft?.panel).toEqual([said]);
		expect(draft?.composer).toEqual({ text: '', images: [], uploaded: [] });
	});
});
