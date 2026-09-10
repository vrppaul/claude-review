import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { diffStore } from '$lib/stores/diff.svelte';
import { isDrawn } from '$lib/utils/placement';
import { createLineSelection } from '$lib/utils/line-selection.svelte';
import type { Comment, DiffFile } from '$lib/types';

function file(path: string, lines: { old_no: number | null; new_no: number | null }[]): DiffFile {
	return {
		path,
		status: 'modified',
		is_binary: false,
		old_mode: null,
		new_mode: null,
		hunks: [
			{
				header: '@@ -1 +1 @@',
				old_start: 1,
				new_start: 1,
				lines: lines.map((at) => ({
					type: at.new_no === null ? 'delete' : 'context',
					old_no: at.old_no,
					new_no: at.new_no,
					content: 'x'
				}))
			}
		]
	};
}

function thread(over: Partial<Comment> = {}): Comment {
	return {
		id: 'c1',
		file: 'a.py',
		side: 'new',
		severity: 'note',
		start_line: 1,
		end_line: 1,
		body: 'reads oddly',
		turns: [],
		raised_by: 'reader',
		resolved: false,
		outdated: false,
		quote: [],
		awaiting: [],
		collapsed: false,
		unread: false,
		round: 1,
		at: 0,
		...over
	};
}

/** The diff the server hands back, whatever base it was asked for. */
function served(paths: string[], phrase = 'uncommitted changes') {
	const mock = vi.fn().mockResolvedValue({
		ok: true,
		json: () =>
			Promise.resolve({
				files: paths.map((p) => file(p, [{ old_no: 1, new_no: 1 }])),
				mode: 'diff',
				title: 'claude-review: uncommitted changes',
				subject: 'claude-review',
				phrase,
				round: 1,
				answerer_attached: false,
				agent: { model: null, context: null, at: null }
			})
	});
	vi.stubGlobal('fetch', mock);
	return mock;
}

describe('what a round changed', () => {
	beforeEach(() => {
		diffStore.clear();
		localStorage.clear();
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('takes the tick off a file the round rewrote, and leaves the others alone', () => {
		diffStore.setFiles([file('rewritten.py', []), file('untouched.py', [])], 'diff');
		diffStore.setViewed('rewritten.py', true);
		diffStore.setViewed('untouched.py', true);

		diffStore.noteRetaken({ followed: 0, outdated: 0 }, ['rewritten.py'], 2);

		expect(diffStore.isViewed('rewritten.py')).toBe(false);
		expect(diffStore.isViewed('untouched.py')).toBe(true);
		expect(diffStore.isChanged('rewritten.py')).toBe(true);
		expect(diffStore.changedSince).toBe(2);
	});

	it('brings a rewritten file back into view, or it sits folded and reads as read', () => {
		diffStore.setFiles([file('rewritten.py', [])], 'diff');
		diffStore.setViewed('rewritten.py', true);

		diffStore.noteRetaken({ followed: 0, outdated: 0 }, ['rewritten.py'], 2);

		expect(diffStore.isCollapsed('rewritten.py')).toBe(false);
	});

	it('trusts no tick when there is no way to tell what moved', () => {
		diffStore.setFiles([file('a.py', []), file('b.py', [])], 'diff');
		diffStore.setViewed('a.py', true);
		diffStore.setViewed('b.py', true);

		diffStore.noteRetaken({ followed: 0, outdated: 0 }, null, null);

		expect(diffStore.viewedCount).toBe(0);
	});
});

describe('reading the same tree against something else', () => {
	beforeEach(() => {
		diffStore.clear();
		localStorage.clear();
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('asks for the diff against the base it was given', async () => {
		const fetchMock = served(['answered.py'], 'changes since round 1');

		await diffStore.setBase('round:1');

		expect(fetchMock.mock.calls[0][0]).toBe('/api/diff?base=round%3A1');
		expect(diffStore.narrowed).toBe(true);
		expect(diffStore.phrase).toBe('changes since round 1');
	});

	it('goes back to the whole review, and stops being narrowed', async () => {
		served(['answered.py'], 'changes since round 1');
		await diffStore.setBase('round:1');

		const fetchMock = served(['answered.py', 'elsewhere.py']);
		await diffStore.setBase('review');

		expect(fetchMock.mock.calls[0][0]).toBe('/api/diff');
		expect(diffStore.narrowed).toBe(false);
	});

	it('stays where it was when the base cannot be taken', async () => {
		vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 400 }));

		await expect(diffStore.setBase('round:9')).rejects.toThrow();

		expect(diffStore.narrowed).toBe(false);
	});

	it("fetches the review's own diff for the threads when a round lands", async () => {
		served(['answered.py'], 'changes since round 1');
		await diffStore.setBase('round:1');

		const fetchMock = served(['answered.py']);
		await diffStore.takeAgain();

		expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
			'/api/diff?base=round%3A1',
			'/api/diff'
		]);
	});
});

describe('a thread the base on screen cannot draw', () => {
	it('is not drawn when its file is not shown', () => {
		expect(isDrawn(thread({ file: 'elsewhere.py' }), [file('a.py', [])])).toBe(false);
	});

	it('is not drawn when its lines are not among the ones shown', () => {
		expect(isDrawn(thread({ end_line: 40 }), [file('a.py', [{ old_no: 1, new_no: 1 }])])).toBe(
			false
		);
	});

	it('is drawn when the row it hangs on is there', () => {
		expect(isDrawn(thread({ end_line: 1 }), [file('a.py', [{ old_no: 1, new_no: 1 }])])).toBe(true);
	});

	it('leaves removed lines alone under a narrower base, whose left side is not ours', () => {
		const removed = thread({ side: 'old', end_line: 1 });
		const shown = [file('a.py', [{ old_no: 1, new_no: null }])];

		expect(isDrawn(removed, shown)).toBe(true);
		expect(isDrawn(removed, shown, { removedLines: false })).toBe(false);
	});
});

describe('a base that is not the review\'s own', () => {
	beforeEach(() => {
		diffStore.clear();
		localStorage.clear();
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('refuses a thread on a removed line, whose numbering belongs to that base', async () => {
		served(['answered.py'], 'changes since round 1');
		await diffStore.setBase('round:1');
		const selection = createLineSelection(() => !diffStore.narrowed);

		selection.handleMouseDown({ type: 'delete', old_no: 17, new_no: null, content: 'gone' }, 0);

		expect(selection.commentingAt).toBeNull();
	});

	it('takes a thread on a line of the working tree, which every base shares', async () => {
		served(['answered.py'], 'changes since round 1');
		await diffStore.setBase('round:1');
		const selection = createLineSelection(() => !diffStore.narrowed);

		selection.commentOnLine({ type: 'context', old_no: 17, new_no: 17, content: 'here' }, 0);

		expect(selection.commentingAt?.side).toBe('new');
	});

	it('unfolds every file when there is no way to tell which ones moved', () => {
		diffStore.setFiles([file('a.py', []), file('b.py', [])], 'diff');
		diffStore.setViewed('a.py', true);
		diffStore.setViewed('b.py', true);

		diffStore.noteRetaken({ followed: 0, outdated: 0 }, null, 2);

		expect(diffStore.isCollapsed('a.py')).toBe(false);
		expect(diffStore.isCollapsed('b.py')).toBe(false);
		expect(diffStore.changedKnown).toBe(false);
	});
});
