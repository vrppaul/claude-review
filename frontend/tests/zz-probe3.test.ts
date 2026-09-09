import { describe, expect, it, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { diffStore } from '$lib/stores/diff.svelte';
import { commentStore } from '$lib/stores/comments.svelte';
import { expansionStore } from '$lib/stores/expansions.svelte';
import { withRevealed } from '$lib/utils/expansions';
import { createLineSelection } from '$lib/utils/line-selection.svelte';
import type { DiffFile, DiffLine } from '$lib/types';
import DiffView from '$lib/components/DiffView.svelte';

const L = (type: DiffLine['type'], o: number | null, n: number | null, c: string): DiffLine => ({ type, old_no: o, new_no: n, content: c });

function mk(path: string, hunks: DiffFile['hunks']): DiffFile {
	return { path, status: 'modified', hunks, is_binary: false, old_mode: null, new_mode: null };
}

describe('revealed lines survive a diff refetch', () => {
	beforeEach(() => {
		expansionStore.clear();
		diffStore.clear();
	});

	it('grafts stale context onto whatever hunk now sits at that index', async () => {
		globalThis.fetch = (async () => ({
			ok: true,
			json: async () => ({ start: 90, lines: ['ninety', 'ninetyone'], total: 500 })
		})) as unknown as typeof fetch;

		await expansionStore.reveal('a.ts', 0, 90, 91);

		// Now the diff is retaken with ignore_whitespace: the file's first hunk
		// is a different region of the file entirely.
		const after = mk('a.ts', [
			{ header: '@@ -300,2 +300,2 @@', old_start: 300, new_start: 300, lines: [L('context', 300, 300, 'x'), L('add', null, 301, 'y')] }
		]);
		const shown = withRevealed(after, expansionStore.forFile('a.ts'));
		console.log('hunk 0 line numbers after refetch:', JSON.stringify(shown.hunks[0].lines.map((l) => [l.new_no, l.content])));
		expect(shown.hunks[0].lines[0].new_no).toBe(300); // will fail: stale line 90 is grafted on
	});
});

describe('line selection anchor', () => {
	it('drag down then back up leaves the box outside the range', () => {
		const s = createLineSelection();
		s.handleMouseDown(L('context', 10, 10, 'a'), 0);
		s.handleMouseEnter(L('context', 20, 20, 'b'), 10);
		s.handleMouseEnter(L('context', 5, 5, 'c'), 5); // back up (a different, earlier row)
		s.handleMouseUp();
		console.log('commentingAt:', JSON.stringify(s.commentingAt));
	});

	it('mouseup with no mousedown is a no-op', () => {
		const s = createLineSelection();
		s.handleMouseUp();
		expect(s.commentingAt).toBeNull();
	});

	it('keyboard comment during a drag then mouseup', () => {
		const s = createLineSelection();
		s.handleMouseDown(L('context', 10, 10, 'a'), 0);
		s.commentOnLine(L('context', 50, 50, 'z'), 40);
		s.handleMouseUp();
		console.log('after keyboard-then-mouseup:', JSON.stringify(s.commentingAt));
	});

	it('a second drag after a keyboard comment still works', () => {
		const s = createLineSelection();
		s.handleMouseDown(L('context', 10, 10, 'a'), 0);
		s.commentOnLine(L('context', 50, 50, 'z'), 40);
		s.handleMouseDown(L('context', 12, 12, 'b'), 2);
		s.handleMouseUp();
		console.log('second drag:', JSON.stringify(s.commentingAt));
	});

	it('isHighlighted during a drag also lights the old commentingAt range', () => {
		const s = createLineSelection();
		s.commentOnLine(L('context', 50, 50, 'z'), 40);
		s.handleMouseDown(L('context', 10, 10, 'a'), 0);
		console.log('drag 10..10, old range 50; isHighlighted(new,50) =', s.isHighlighted('new', 50));
	});
});

describe('DiffView observer', () => {
	beforeEach(() => {
		diffStore.clear();
		commentStore.clear();
	});

	it('does not rebuild the observer when markInView fires', async () => {
		let constructed = 0;
		const real = globalThis.IntersectionObserver;
		class Counting {
			cb: IntersectionObserverCallback;
			static targets: Element[] = [];
			constructor(cb: IntersectionObserverCallback) {
				constructed += 1;
				this.cb = cb;
			}
			observe = (t: Element) => {
				Counting.targets.push(t);
				this.cb([{ target: t, isIntersecting: true } as IntersectionObserverEntry], this as unknown as IntersectionObserver);
			};
			unobserve = vi.fn();
			disconnect = vi.fn();
			takeRecords = vi.fn(() => []);
		}
		globalThis.IntersectionObserver = Counting as unknown as typeof IntersectionObserver;

		diffStore.setFiles(
			[mk('a.ts', [{ header: '@@', old_start: 1, new_start: 1, lines: [L('add', null, 1, 'a')] }]),
			 mk('b.ts', [{ header: '@@', old_start: 1, new_start: 1, lines: [L('add', null, 1, 'b')] }])],
			'diff', 't');
		render(DiffView);
		await waitFor(() => expect(screen.getAllByTestId('file-section').length).toBe(2));
		const afterMount = constructed;
		diffStore.markInView('b.ts');
		flushSync();
		await Promise.resolve();
		console.log('observers constructed at mount:', afterMount, 'after markInView:', constructed);
		expect(constructed).toBe(afterMount);

		// Same length, different paths
		Counting.targets = [];
		diffStore.setFiles(
			[mk('c.ts', [{ header: '@@', old_start: 1, new_start: 1, lines: [L('add', null, 1, 'c')] }]),
			 mk('d.ts', [{ header: '@@', old_start: 1, new_start: 1, lines: [L('add', null, 1, 'd')] }])],
			'diff', 't');
		flushSync();
		await waitFor(() => expect(screen.getAllByTestId('file-section')[0].dataset.path).toBe('c.ts'));
		console.log('observers after same-length swap:', constructed,
			'observed paths:', JSON.stringify(Counting.targets.map((t) => (t as HTMLElement).dataset.path)));
		globalThis.IntersectionObserver = real;
	});
});
