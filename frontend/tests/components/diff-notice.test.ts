import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import DiffNotice from '$lib/components/DiffNotice.svelte';
import { commentStore } from '$lib/stores/comments.svelte';
import { diffStore } from '$lib/stores/diff.svelte';

/** The rendered sentence, without the template's line breaks. */
function text(element: HTMLElement): string {
	return element.textContent?.replace(/\s+/g, ' ').trim() ?? '';
}

describe('when the tree moves under the review', () => {
	beforeEach(() => {
		localStorage.clear();
		diffStore.clear();
		commentStore.clear();
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('says so, and leaves the taking to the reader', () => {
		diffStore.noteTreeMoved(3);

		const { getByTestId } = render(DiffNotice);

		expect(text(getByTestId('tree-moved'))).toContain('3 files have changed');
		expect(getByTestId('retake-diff')).toBeTruthy();
	});

	it('says nothing while nothing has moved', () => {
		const { queryByTestId } = render(DiffNotice);

		expect(queryByTestId('tree-moved')).toBeNull();
	});

	it('takes the diff again when the reader asks for it', async () => {
		const user = userEvent.setup({ delay: null });
		const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
		vi.stubGlobal('fetch', fetchMock);
		diffStore.noteTreeMoved(1);

		const { getByTestId } = render(DiffNotice);
		await user.click(getByTestId('retake-diff'));

		expect(fetchMock.mock.calls[0][0]).toBe('/api/round');
	});

	it('stays dismissed until something moves again', async () => {
		const user = userEvent.setup({ delay: null });
		diffStore.noteTreeMoved(2);

		const { getByTestId, queryByTestId } = render(DiffNotice);
		await user.click(getByTestId('dismiss-moved'));

		expect(queryByTestId('tree-moved')).toBeNull();
	});

	it('says what a retake did to the threads', () => {
		diffStore.noteRetaken({ followed: 2, outdated: 1 });

		const { getByTestId } = render(DiffNotice);

		expect(text(getByTestId('diff-retaken'))).toContain('2 threads followed their lines');
		expect(text(getByTestId('diff-retaken'))).toContain('1 is outdated');
	});

	it('offers a way to the thread that lost its lines', () => {
		commentStore.add('a.py', 'new', 1, 1, 'this one');
		commentStore.comments[0].outdated = true;
		diffStore.noteRetaken({ followed: 0, outdated: 1 });

		const { getByTestId } = render(DiffNotice);

		expect(getByTestId('show-outdated')).toBeTruthy();
	});
});
