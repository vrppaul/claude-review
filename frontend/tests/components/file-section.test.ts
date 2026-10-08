import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import FileSection from '$lib/components/FileSection.svelte';
import { diffStore } from '$lib/stores/diff.svelte';
import { commentStore } from '$lib/stores/comments.svelte';
import { addedLine, contextLine, diffFile, diffResponse, hunk, removedLine } from '../diff';
import { BAD_REQUEST, fakeServer } from '../fake-server';
import { newComment } from '../new-comment';

const file = diffFile({
	path: 'src/core/session.py',
	hunks: [hunk([contextLine(1, 1, 'import os'), removedLine(2, 'x = 1'), addedLine(2, 'x = 2')])]
});

describe('a file in the review', () => {
	beforeEach(() => {
		diffStore.setFiles([file], 'diff');
	});

	it('names the file and how much it changed', () => {
		const { getByText } = render(FileSection, { props: { file } });

		expect(getByText('src/core/session.py')).toBeTruthy();
		expect(getByText('+1')).toBeTruthy();
		expect(getByText('−1')).toBeTruthy();
	});

	it('folds the body away and brings it back', async () => {
		const user = userEvent.setup();
		const { getByTestId, queryByTestId } = render(FileSection, { props: { file } });

		expect(queryByTestId('raw-view')).toBeTruthy();

		await user.click(getByTestId('collapse-file'));
		expect(queryByTestId('raw-view')).toBeNull();

		await user.click(getByTestId('collapse-file'));
		expect(queryByTestId('raw-view')).toBeTruthy();
	});

	it('folds the file when it is marked viewed', async () => {
		const user = userEvent.setup();
		const { getByTestId, queryByTestId } = render(FileSection, { props: { file } });

		await user.click(getByTestId('viewed-toggle'));

		expect(diffStore.isViewed('src/core/session.py')).toBe(true);
		expect(queryByTestId('raw-view')).toBeNull();
	});

	it('brings the file back when it is unmarked', async () => {
		const user = userEvent.setup();
		const { getByTestId, queryByTestId } = render(FileSection, { props: { file } });

		await user.click(getByTestId('viewed-toggle'));
		await user.click(getByTestId('viewed-toggle'));

		expect(diffStore.isViewed('src/core/session.py')).toBe(false);
		expect(queryByTestId('raw-view')).toBeTruthy();
	});

	it('can be reopened after being marked viewed, without unmarking it', async () => {
		const user = userEvent.setup();
		const { getByTestId, queryByTestId } = render(FileSection, { props: { file } });

		await user.click(getByTestId('viewed-toggle'));
		await user.click(getByTestId('collapse-file'));

		expect(queryByTestId('raw-view')).toBeTruthy();
		expect(diffStore.isViewed('src/core/session.py')).toBe(true);
	});

	it('shows how many comments the file carries', () => {
		commentStore.add(newComment({ file: 'src/core/session.py', startLine: 2, body: 'rename this' }));

		const { getByTestId } = render(FileSection, { props: { file } });

		expect(getByTestId('section-comment-count').textContent?.trim()).toBe('1');
	});

	it('leaves the comment count off a file with none', () => {
		const { queryByTestId } = render(FileSection, { props: { file } });

		expect(queryByTestId('section-comment-count')).toBeNull();
	});
});

describe('a file the last round rewrote', () => {
	beforeEach(() => {
		diffStore.setFiles([file], 'diff');
		diffStore.noteRetaken({ followed: 0, outdated: 0 }, { since_round: 2, paths: ['src/core/session.py'] });
	});

	it('shows only what changed since that round when asked', async () => {
		const user = userEvent.setup({ delay: null });
		const server = fakeServer();
		server.answer('GET /api/diff', diffResponse({ files: [file], phrase: 'changes since round 2' }));
		const { getByTestId } = render(FileSection, { props: { file } });

		await user.click(getByTestId('file-changed-since'));

		expect(server.requests).toMatchObject([{ path: '/api/diff', query: { base: 'round:2' } }]);
		await vi.waitFor(() => expect(diffStore.base).toBe('round:2'));
	});

	it('says so when that round cannot be shown', async () => {
		const user = userEvent.setup({ delay: null });
		fakeServer().refuse('GET /api/diff', BAD_REQUEST);
		const { getByTestId, findByTestId } = render(FileSection, { props: { file } });

		await user.click(getByTestId('file-changed-since'));

		expect((await findByTestId('changed-since-error')).textContent).toContain(String(BAD_REQUEST));
	});
});
