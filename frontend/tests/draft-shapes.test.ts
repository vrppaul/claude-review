import { describe, it, expect } from 'vitest';
import { DRAFT_SHAPE, type Draft } from '$lib/drafts/draft-shapes';
import { keepDraft, readDraft } from '$lib/drafts/draft-storage';
import { lineAnchor } from '$lib/anchors/line';
import type { AwaitedQuestion, Thread } from '$lib/types';
import { REVIEW_TITLE } from './diff';
import { THIS_RUN } from './fake-socket';
import { newComment } from './new-comment';
import { openReview } from './review';
import { storeDraft } from './stored-draft';

/** The last shape a draft had before its threads hung on anchors. */
const BEFORE_ANCHORS = 7;
/** The last shape a draft had before every turn carried an id. */
const BEFORE_TURN_IDS = 8;
/** The shape every turn carries an id in, and the draft counts the ids handed out. */
const SHAPE_WITH_TURN_IDS = 9;
/** A shape between the last one released and this one, which no release ever kept. */
const NEVER_RELEASED = 13;

/** Put a draft in storage as an older release of the review left it. */
function keptByAnOlderRelease(draft: object) {
	storeDraft({ title: REVIEW_TITLE, reviewBody: '', ...draft });
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

describe('a draft this release kept', () => {
	it('comes back as it was kept', () => {
		const kept: Draft = {
			version: DRAFT_SHAPE,
			title: REVIEW_TITLE,
			threads: [fullThread()],
			read: { folded: ['comment-1'], unread: [], awaiting: { 'comment-1': [{ id: 'comment-1', at: 40 }] } },
			writing: [
				{ at: { kind: 'reply', thread: 'comment-1' }, text: 'and another thing', severity: 'note', images: [] },
				{
					at: {
						kind: 'new',
						file: 'a.py',
						lines: { side: 'new', startLine: 3, endLine: 4, opensBelow: { side: 'new', number: 4 } }
					},
					text: 'half a comment',
					severity: 'question',
					images: ['pasted.png']
				}
			],
			reviewBody: 'Overall fine',
			sent: { 'comment-1': 2 },
			panel: [{ id: 'message-1', author: 'reader', body: 'Run the tests', at: 60, images: [] }],
			composer: { text: 'half a thought', images: ['pasted.png'] },
			issued: { comments: 3, turns: 5 },
			told: { instance: THIS_RUN, sequence: 4 }
		};

		keepDraft(kept);

		expect(readDraft(REVIEW_TITLE)).toEqual(kept);
	});
});

describe('a draft of a shape no release kept', () => {
	it('is not read, rather than read as something it is not', () => {
		keptByAnOlderRelease({
			version: NEVER_RELEASED,
			threads: [fullThread()],
			read: { folded: [], unread: [], awaiting: [] },
			sent: [['comment-1', 2]]
		});

		expect(readDraft(REVIEW_TITLE)).toBeNull();
	});
});

describe('a draft written by an older release', () => {
	it('is brought up to the current shape rather than thrown away', () => {
		keptByAnOlderRelease({ comments: [flatThread({ body: 'written before threads existed' })] });

		const draft = readDraft(REVIEW_TITLE);

		expect(draft?.threads[0].body).toBe('written before threads existed');
		expect(draft?.threads[0].turns).toEqual([]);
		expect(draft?.read).toEqual({ folded: [], unread: [], awaiting: {} });
		expect(draft?.sent).toEqual({});
	});

	it('keeps how each thread was being read, apart from what it says', () => {
		keptByAnOlderRelease({ version: SHAPE_WITH_TURN_IDS, comments: [keptComment()], sent: [] });

		const draft = readDraft(REVIEW_TITLE);

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

		const [comment] = readDraft(REVIEW_TITLE)?.threads ?? [];

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

	it('counts a thread sent before rounds were numbered as sent in the first', () => {
		keptByAnOlderRelease({ comments: [flatThread()], sent: ['comment-1'] });

		expect(readDraft(REVIEW_TITLE)?.sent).toEqual({ 'comment-1': 1 });
	});

	it('gives a turn written before images could be pasted no images', () => {
		keptByAnOlderRelease({
			comments: [flatThread({ turns: [{ author: 'author', body: 'Done', round: 1 }] })]
		});

		expect(readDraft(REVIEW_TITLE)?.threads[0].turns).toEqual([
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

		const ids = readDraft(REVIEW_TITLE)?.threads[0].turns.map((turn) => turn.id);

		expect(ids).toEqual(['turn-5', 'turn-4']);
	});

	it('starts the agent panel empty when the draft predates it', () => {
		keptByAnOlderRelease({ comments: [flatThread()] });

		const draft = readDraft(REVIEW_TITLE);

		expect(draft?.panel).toEqual([]);
		expect(draft?.composer).toEqual({ text: '', images: [] });
	});

	it('keeps what was said in the panel when the draft predates the composer', () => {
		const said = { id: 'message-1', author: 'reader', body: 'Run the tests', at: 60 };
		keptByAnOlderRelease({ comments: [flatThread()], panel: [said] });

		const draft = readDraft(REVIEW_TITLE);

		expect(draft?.panel).toEqual([said]);
		expect(draft?.composer).toEqual({ text: '', images: [] });
	});
});
