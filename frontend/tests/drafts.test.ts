import { describe, it, expect, vi } from 'vitest';
import { commentStore } from '$lib/stores/comments.svelte';
import { loadDraft, saveDraft, clearDraft, type Draft } from '$lib/utils/drafts';
import { lineAnchor } from '$lib/anchors/line';
import type { Comment } from '$lib/types';
import { fakeServer } from './fake-server';
import { newComment } from './new-comment';

const TITLE = 'repo: uncommitted changes';
/** Where the page keeps the draft between reloads. */
const DRAFT_KEY = 'claude-review:draft';
/** The last shape a draft had before its threads hung on anchors. */
const BEFORE_ANCHORS = 7;
/** The last shape a draft had before every turn carried an id. */
const BEFORE_TURN_IDS = 8;

/** Put a draft in storage as an older release of the review left it. */
function keptByAnOlderRelease(draft: object) {
	localStorage.setItem(DRAFT_KEY, JSON.stringify({ title: TITLE, reviewBody: '', ...draft }));
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

/** A thread with every field this release keeps filled in. */
function fullThread(): Comment {
	return {
		id: 'comment-1',
		anchor: lineAnchor('a.py', 'new', 3, 4, ['x = 1', 'y = 2']),
		severity: 'question',
		body: 'Why both?',
		images: ['opening.png'],
		turns: [
			{ id: 'turn-1', author: 'author', body: 'History', round: 2, at: 50, images: [] }
		],
		raised_by: 'reader',
		resolved: false,
		awaiting: [{ id: 'comment-1', at: 40 }],
		collapsed: true,
		unread: true,
		round: 2,
		at: 30
	};
}

/** The reload of a page: whatever it held is gone, and the draft is read again. */
function reload() {
	commentStore.clear();
	commentStore.restore(TITLE);
}

describe('an unsent review', () => {
	it('survives a reload of the same review', () => {
		commentStore.restore(TITLE);
		commentStore.add(newComment({ file: 'a.py', body: 'tighten this' }));
		commentStore.setReviewBody('Overall fine');

		commentStore.clear();
		const count = commentStore.restore(TITLE);

		expect(count).toBe(1);
		expect(commentStore.comments[0].body).toBe('tighten this');
		expect(commentStore.reviewBody).toBe('Overall fine');
	});

	it('is not handed to a different review', () => {
		commentStore.restore(TITLE);
		commentStore.add(newComment({ file: 'a.py', body: 'tighten this' }));

		commentStore.clear();
		const count = commentStore.restore('other-repo: changes since v1');

		expect(count).toBe(0);
		expect(commentStore.comments).toEqual([]);
	});

	it('does not come back after it has been sent', async () => {
		const server = fakeServer();
		server.answer('POST /api/submit', { markdown: '## x', comment_count: 1, round: 1, ended: true });
		commentStore.restore(TITLE);
		commentStore.add(newComment({ file: 'a.py', body: 'tighten this' }));

		await commentStore.submit();
		commentStore.clear();

		expect(commentStore.restore(TITLE)).toBe(0);
	});

	it('never hands out a comment id a restored comment already has, even after a deletion', () => {
		commentStore.restore(TITLE);
		const first = commentStore.add(newComment({ startLine: 1, body: 'one' }));
		commentStore.add(newComment({ startLine: 2, body: 'two' }));
		commentStore.remove(first);

		reload();
		commentStore.add(newComment({ startLine: 3, body: 'three' }));

		const ids = commentStore.comments.map((comment) => comment.id);
		expect(new Set(ids).size).toBe(ids.length);
	});

	it('never hands out again the ids of a thread deleted just before the reload', () => {
		commentStore.restore(TITLE);
		commentStore.add(newComment({ startLine: 1, body: 'kept' }));
		const deleted = commentStore.add(newComment({ startLine: 2, body: 'deleted' }));
		commentStore.addTurn(deleted, { author: 'reader', body: 'Asked', images: [] });
		const deletedTurn = commentStore.comments[1].turns[0].id;
		commentStore.remove(deleted);

		reload();
		const added = commentStore.add(newComment({ startLine: 3, body: 'new' }));
		commentStore.addTurn(added, { author: 'reader', body: 'Asked anew', images: [] });

		// The agent may still know the deleted ones, and would answer the new under them
		expect(added).not.toBe(deleted);
		expect(commentStore.comments[1].turns[0].id).not.toBe(deletedTurn);
	});

	it('never hands out a turn id a restored turn already has', () => {
		commentStore.restore(TITLE);
		const id = commentStore.add(newComment({ body: 'Why?' }));
		commentStore.addTurn(id, { author: 'reader', body: 'Still asking', images: [] });
		commentStore.receiveReply(id, 'Because');

		reload();
		commentStore.addTurn(id, { author: 'reader', body: 'Thanks', images: [] });

		const ids = commentStore.comments[0].turns.map((turn) => turn.id);
		expect(ids).toHaveLength(3);
		expect(new Set(ids).size).toBe(ids.length);
	});

	it('leaves the review working when site data is blocked', () => {
		vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
			throw new Error('blocked');
		});

		commentStore.restore(TITLE);
		expect(() => commentStore.add(newComment({ body: 'still fine' }))).not.toThrow();
		expect(commentStore.count).toBe(1);
	});

	it('ignores a draft that is not what it should be', () => {
		localStorage.setItem(DRAFT_KEY, 'not json at all');

		expect(loadDraft(TITLE)).toBeNull();
	});

	it('is forgotten when asked', () => {
		saveDraft({ title: 'repo', comments: [], sent: [], reviewBody: 'x' });
		clearDraft();

		expect(loadDraft('repo')).toBeNull();
	});
});

describe('a draft this release kept', () => {
	it('comes back as it was kept', () => {
		const kept: Omit<Draft, 'version'> = {
			title: TITLE,
			comments: [fullThread()],
			reviewBody: 'Overall fine',
			sent: [['comment-1', 2]],
			panel: [{ id: 'message-1', author: 'reader', body: 'Run the tests', at: 60, images: [] }],
			composer: { text: 'half a thought', images: ['pasted.png'] },
			issued: { comments: 3, turns: 5 }
		};

		saveDraft(kept);

		expect(loadDraft(TITLE)).toEqual({ ...kept, version: expect.any(Number) });
	});
});

describe('a draft written by an older release', () => {
	it('is brought up to the current shape rather than thrown away', () => {
		keptByAnOlderRelease({ comments: [flatThread({ body: 'written before threads existed' })] });

		const draft = loadDraft(TITLE);

		expect(draft?.comments[0].body).toBe('written before threads existed');
		expect(draft?.comments[0].turns).toEqual([]);
		expect(draft?.comments[0].awaiting).toEqual([]);
		expect(draft?.sent).toEqual([]);
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

		const [comment] = loadDraft(TITLE)?.comments ?? [];

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

		expect(loadDraft(TITLE)?.sent).toEqual([['comment-1', 1]]);
	});

	it('gives a turn written before images could be pasted no images', () => {
		keptByAnOlderRelease({
			comments: [flatThread({ turns: [{ author: 'author', body: 'Done', round: 1 }] })]
		});

		expect(loadDraft(TITLE)?.comments[0].turns).toEqual([
			{ id: 'turn-1', author: 'author', body: 'Done', round: 1, images: [] }
		]);
	});

	it('gives each turn written before turns had ids one of its own, never one a turn already has', () => {
		keptByAnOlderRelease({
			version: BEFORE_TURN_IDS,
			comments: [
				{
					...fullThread(),
					turns: [
						{ author: 'reader', body: 'Why?', round: 1, images: [] },
						{ id: 'turn-4', author: 'author', body: 'Because', round: 1, images: [] }
					]
				}
			]
		});

		const ids = loadDraft(TITLE)?.comments[0].turns.map((turn) => turn.id);

		expect(ids).toEqual(['turn-5', 'turn-4']);
	});

	it('starts the agent panel empty when the draft predates it', () => {
		keptByAnOlderRelease({ comments: [flatThread()] });

		const draft = loadDraft(TITLE);

		expect(draft?.panel).toEqual([]);
		expect(draft?.composer).toEqual({ text: '', images: [] });
	});

	it('keeps what was said in the panel when the draft predates the composer', () => {
		const said = { id: 'message-1', author: 'reader', body: 'Run the tests', at: 60 };
		keptByAnOlderRelease({ comments: [flatThread()], panel: [said] });

		const draft = loadDraft(TITLE);

		expect(draft?.panel).toEqual([said]);
		expect(draft?.composer).toEqual({ text: '', images: [] });
	});
});
