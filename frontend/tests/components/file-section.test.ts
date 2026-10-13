import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, within } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { userEvent } from '@testing-library/user-event';
import FileSection from '$lib/components/FileSection.svelte';
import { addedLine, contextLine, diffFile, diffResponse, hunk, removedLine, sinceRound } from '../diff';
import { BAD_REQUEST, fakeServer } from '../fake-server';
import { newComment } from '../new-comment';
import type { Review } from '$lib/review/review.svelte';
import { inReview, openReview } from '../review';
import { scriptTheScroll, scrollTo } from '../scripted-scroll';
import { lineAnchor } from '$lib/anchors/line';

const file = diffFile({
	path: 'src/core/session.py',
	hunks: [hunk([contextLine(1, 1, 'import os'), removedLine(2, 'x = 1'), addedLine(2, 'x = 2')])]
});

describe('a file in the review', () => {
	let review: Review;

	beforeEach(() => {
		review = openReview({ files: [file] });
	});

	it('names the file and how much it changed', () => {
		const { getByText } = render(FileSection, inReview(review, { file, scrollRoot: null }));

		expect(getByText('src/core/session.py')).toBeTruthy();
		expect(getByText('+1')).toBeTruthy();
		expect(getByText('−1')).toBeTruthy();
	});

	it('says which line each row is at its number, for the reader to be kept on it across a new diff', () => {
		const { getAllByTestId } = render(FileSection, inReview(review, { file, scrollRoot: null }));

		expect(getAllByTestId('line-gutter').map((number) => number.dataset.place)).toEqual(['new:1', 'old:2', 'new:2']);
	});

	it('says how many rows it draws, for the room it takes before it is drawn, and none once folded', () => {
		const { getByTestId } = render(FileSection, inReview(review, { file, scrollRoot: null }));
		const section = getByTestId('file-section');
		expect(section.style.getPropertyValue('--cr-rows')).toBe('3');

		review.reading.toggleFolded(file.path);
		flushSync();

		expect(section.style.getPropertyValue('--cr-rows')).toBe('0');
	});

	it('holds a row of room for a file it shows no line of', () => {
		const picture = diffFile({ path: 'docs/logo.png', status: 'added', unshown: 'binary' });
		review = openReview({ files: [picture] });

		const { getByTestId } = render(FileSection, inReview(review, { file: picture, scrollRoot: null }));

		expect(getByTestId('file-section').style.getPropertyValue('--cr-rows')).toBe('1');
	});

	it('is not built until the reader comes near it', () => {
		scriptTheScroll();
		const { getByTestId, queryByTestId } = render(FileSection, inReview(review, { file, scrollRoot: null }));
		expect(getByTestId('file-placeholder')).toBeTruthy();
		expect(queryByTestId('raw-view')).toBeNull();

		scrollTo(getByTestId('file-section'));
		flushSync();

		expect(queryByTestId('file-placeholder')).toBeNull();
		expect(getByTestId('raw-view')).toBeTruthy();
	});

	it('folds the body away and brings it back', async () => {
		const user = userEvent.setup();
		const { getByTestId, queryByTestId } = render(FileSection, inReview(review, { file, scrollRoot: null }));

		expect(queryByTestId('raw-view')).toBeTruthy();

		await user.click(getByTestId('collapse-file'));
		expect(queryByTestId('raw-view')).toBeNull();

		await user.click(getByTestId('collapse-file'));
		expect(queryByTestId('raw-view')).toBeTruthy();
	});

	it('folds the file when it is marked viewed', async () => {
		const user = userEvent.setup();
		const { getByTestId, queryByTestId } = render(FileSection, inReview(review, { file, scrollRoot: null }));

		await user.click(getByTestId('viewed-toggle'));

		expect(review.reading.isViewed('src/core/session.py')).toBe(true);
		expect(queryByTestId('raw-view')).toBeNull();
	});

	it('brings the file back when it is unmarked', async () => {
		const user = userEvent.setup();
		const { getByTestId, queryByTestId } = render(FileSection, inReview(review, { file, scrollRoot: null }));

		await user.click(getByTestId('viewed-toggle'));
		await user.click(getByTestId('viewed-toggle'));

		expect(review.reading.isViewed('src/core/session.py')).toBe(false);
		expect(queryByTestId('raw-view')).toBeTruthy();
	});

	it('can be reopened after being marked viewed, without unmarking it', async () => {
		const user = userEvent.setup();
		const { getByTestId, queryByTestId } = render(FileSection, inReview(review, { file, scrollRoot: null }));

		await user.click(getByTestId('viewed-toggle'));
		await user.click(getByTestId('collapse-file'));

		expect(queryByTestId('raw-view')).toBeTruthy();
		expect(review.reading.isViewed('src/core/session.py')).toBe(true);
	});

	it('shows how many comments the file carries', () => {
		review.threads.add(newComment({ file: 'src/core/session.py', startLine: 2, body: 'rename this' }));

		const { getByTestId } = render(FileSection, inReview(review, { file, scrollRoot: null }));

		expect(getByTestId('section-comment-count').textContent?.trim()).toBe('1');
	});

	it('leaves the comment count off a file with none', () => {
		const { queryByTestId } = render(FileSection, inReview(review, { file, scrollRoot: null }));

		expect(queryByTestId('section-comment-count')).toBeNull();
	});
});

describe('a file the last round rewrote', () => {
	let review: Review;

	beforeEach(() => {
		review = openReview({ files: [file] });
		review.noteRetake(
			{ followed: 0, outdated: 0 },
			{ since_round: 2, base_key: 'round:2', paths: ['src/core/session.py'] }
		);
	});

	it('shows only what changed since that round when asked', async () => {
		const user = userEvent.setup({ delay: null });
		const server = fakeServer();
		server.answer('GET /api/diff', diffResponse({ files: [file], base: sinceRound(2) }));
		const { getByTestId } = render(FileSection, inReview(review, { file, scrollRoot: null }));

		await user.click(getByTestId('file-changed-since'));

		expect(server.requests).toMatchObject([{ path: '/api/diff', query: { base: 'round:2' } }]);
		await vi.waitFor(() => expect(review.diff.base).toBe('round:2'));
	});

	it('says so when that round cannot be shown', async () => {
		const user = userEvent.setup({ delay: null });
		fakeServer().refuse('GET /api/diff', BAD_REQUEST);
		const { getByTestId, findByTestId } = render(FileSection, inReview(review, { file, scrollRoot: null }));

		await user.click(getByTestId('file-changed-since'));

		expect((await findByTestId('changed-since-error')).textContent).toContain(String(BAD_REQUEST));
	});
});

describe('a file whose name holds control characters', () => {
	const named = diffFile({ path: 'tab\there.py', commentable: false, hunks: [hunk([addedLine(1, 'x = 1')])] });

	it('says it cannot be commented on, and its lines take no comment', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: [named] });
		const { getByTestId, getAllByTestId, queryByTestId } = render(
			FileSection,
			inReview(review, { file: named, scrollRoot: null })
		);

		expect(getByTestId('not-commentable-note').textContent).toContain('This file cannot be commented on');
		const [lineNumber] = getAllByTestId('line-gutter');
		expect(lineNumber.getAttribute('aria-disabled')).toBe('true');
		expect(lineNumber.getAttribute('title')).toContain('control characters');

		await user.click(lineNumber);

		expect(queryByTestId('comment-input')).toBeNull();
	});
});

describe('a comment whose line the diff no longer shows', () => {
	// The agent put the removed line back: old line 2 is an unchanged line again
	const restored = diffFile({
		path: 'src/core/session.py',
		hunks: [hunk([contextLine(1, 1, 'import os'), contextLine(2, 2, 'x = 1'), addedLine(3, 'y = 2')])]
	});
	const onTheRemovedLine = {
		...newComment({ file: 'src/core/session.py', body: 'why did this go' }),
		anchor: { ...lineAnchor('src/core/session.py', 'old', 2, 2, ['x = 1']), outdated: true }
	};

	it('is drawn at the head of its file, whole, rather than nowhere', () => {
		const review = openReview({ files: [restored] });
		review.threads.add(onTheRemovedLine);
		review.threads.add(newComment({ file: 'src/core/session.py', startLine: 3, body: 'on a line still there' }));

		const { getByTestId } = render(FileSection, inReview(review, { file: restored, scrollRoot: null }));

		const head = getByTestId('threads-off-their-lines');
		expect(head.textContent).toContain('1 comment on a line no longer shown');
		expect(within(head).getAllByTestId('comment-thread')).toHaveLength(1);
		expect(head.textContent).toContain('why did this go');
		expect(head.textContent).not.toContain('on a line still there');
	});

	it('is drawn at the head of its file when the line it was read in on is not read in any more', () => {
		// Written on line 9, read in above the hunk before whitespace was left out and the diff taken afresh
		const review = openReview({ files: [restored] });
		review.threads.add(newComment({ file: 'src/core/session.py', startLine: 9, quote: ['z = 3'], body: 'read in' }));

		const { getByTestId } = render(FileSection, inReview(review, { file: restored, scrollRoot: null }));

		expect(getByTestId('threads-off-their-lines').textContent).toContain('read in');
	});

	it('is left to the notice above the diff under a narrower base, which names every thread it cannot draw', async () => {
		const review = openReview({ files: [restored] });
		review.threads.add({
			...onTheRemovedLine,
			anchor: { ...lineAnchor('src/core/session.py', 'new', 9, 9, ['gone']), outdated: true }
		});
		fakeServer().answer('GET /api/diff', diffResponse({ files: [restored], base: sinceRound(1) }));
		await review.diff.setBase('round:1');

		const { queryByTestId } = render(FileSection, inReview(review, { file: restored, scrollRoot: null }));

		expect(queryByTestId('threads-off-their-lines')).toBeNull();
	});
});
