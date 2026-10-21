import { beforeEach, describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import { tick } from 'svelte';
import DiffView from '$lib/components/DiffView.svelte';
import FileSection from '$lib/components/FileSection.svelte';
import GuideCard from '$lib/components/GuideCard.svelte';
import ReviewHeader from '$lib/components/ReviewHeader.svelte';
import { addedLine, contextLine, diffFile, diffResponse, hunk, removedLine } from '../diff';
import { fakeServer } from '../fake-server';
import { guideServer } from '../guide-server';
import { newComment } from '../new-comment';
import type { Review } from '$lib/review/review.svelte';
import { inReview, openReview } from '../review';
import { settled } from '../settled';

/** Lines 1 to 4 of a file, the third one added. */
const file = diffFile({
	path: 'src/app.py',
	hunks: [
		hunk([
			contextLine(1, 1, 'first = 1'),
			contextLine(2, 2, 'second = 2'),
			addedLine(3, 'third = 3'),
			contextLine(3, 4, 'fourth = 4')
		])
	]
});

let review: Review;

beforeEach(() => {
	review = openReview({ files: [file] });
});

/** The number of a line, to press it by. */
function lineNumber(number: number): HTMLElement {
	const gutter = screen
		.getAllByTestId('line-gutter')
		.find((candidate) => candidate.textContent?.trim() === String(number));
	if (!gutter) throw new Error(`Line ${number} is not drawn`);
	return gutter;
}

/** The thread drawn on the page, which the keyboard is put on. */
function thread(): HTMLElement {
	return screen.getByTestId('comment-thread');
}

/** Let the page draw what an action changed, and the keyboard be handed on. */
async function drawn(): Promise<void> {
	await tick();
	await tick();
}

describe('where the keyboard is after a comment field goes', () => {
	it('is on the thread a comment became once it is added', async () => {
		const user = userEvent.setup();
		render(DiffView, inReview(review));
		await user.click(lineNumber(2));

		await user.type(screen.getByTestId('comment-input'), 'Name it');
		await user.keyboard('{Control>}{Enter}{/Control}');
		await drawn();

		expect(document.activeElement).toBe(thread());
	});

	it('is back on the line a comment was put away from', async () => {
		const user = userEvent.setup();
		render(DiffView, inReview(review));
		await user.click(lineNumber(2));

		await user.keyboard('{Escape}');
		await drawn();

		expect(document.activeElement).toBe(lineNumber(2));
	});

	it('is on the thread a reply was added to, or put away from', async () => {
		const user = userEvent.setup();
		review.threads.add(newComment({ file: file.path, startLine: 2, body: 'why two' }));
		render(DiffView, inReview(review));

		await user.click(screen.getByTestId('open-reply'));
		await user.type(screen.getByTestId('comment-input'), 'And three?');
		await user.click(screen.getByTestId('save-comment'));
		await drawn();
		expect(document.activeElement).toBe(thread());

		await user.click(screen.getByTestId('open-reply'));
		await user.click(screen.getByTestId('cancel-comment'));
		await drawn();
		expect(document.activeElement).toBe(thread());
	});

	it('is on the thread an edit was put away from', async () => {
		const user = userEvent.setup();
		review.threads.add(newComment({ file: file.path, startLine: 2, body: 'why two' }));
		render(DiffView, inReview(review));

		await user.click(screen.getByTestId('thread-menu'));
		await user.click(screen.getByTestId('edit-comment'));
		await user.click(screen.getByTestId('cancel-comment'));
		await drawn();

		expect(document.activeElement).toBe(thread());
	});
});

describe('where the keyboard is after a thread changes', () => {
	beforeEach(() => {
		review.threads.add(newComment({ file: file.path, startLine: 2, body: 'why two' }));
	});

	it('is on the thread once it is settled, and once it is taken up again', async () => {
		const user = userEvent.setup();
		render(DiffView, inReview(review));

		await user.click(screen.getByTestId('resolve-comment'));
		await drawn();
		expect(document.activeElement).toBe(thread());

		await user.click(screen.getByTestId('reopen-thread'));
		await drawn();
		expect(document.activeElement).toBe(thread());
	});

	it('is on the line the thread folded to, and on the toggle of the thread it opens again', async () => {
		const user = userEvent.setup();
		render(DiffView, inReview(review));

		await user.click(within(thread()).getByTestId('fold-comment'));
		await drawn();
		expect(document.activeElement).toBe(within(thread()).getByTestId('unfold-thread'));
		expect(screen.getByTestId('folded-thread')).toBeTruthy();

		await user.click(within(thread()).getByTestId('unfold-thread'));
		await drawn();
		expect(document.activeElement).toBe(within(thread()).getByTestId('fold-comment'));
	});

	it('is on the line the thread hung under once it is deleted', async () => {
		const user = userEvent.setup();
		render(DiffView, inReview(review));

		await user.click(screen.getByTestId('thread-menu'));
		await user.click(screen.getByTestId('delete-comment'));
		await user.click(screen.getByTestId('confirm-go-ahead'));
		await drawn();

		expect(screen.queryByTestId('comment-thread')).toBeNull();
		expect(document.activeElement).toBe(lineNumber(2));
	});
});

describe('where the keyboard is after a thread drawn at the head of its file goes', () => {
	it('is on the file, whose line the thread hung under is not drawn', async () => {
		const user = userEvent.setup();
		review.threads.add(newComment({ file: file.path, startLine: 9, body: 'a line no longer here' }));
		render(DiffView, inReview(review));

		await user.click(screen.getByTestId('thread-menu'));
		await user.click(screen.getByTestId('delete-comment'));
		await user.click(screen.getByTestId('confirm-go-ahead'));
		await drawn();

		expect(document.activeElement).toBe(screen.getByTestId('collapse-file'));
	});
});

describe('where the keyboard is after a thread on a file the diff no longer has goes', () => {
	it('is on the first file of the diff, which the thread was drawn above, however late that file came', async () => {
		const user = userEvent.setup();
		review.threads.add(newComment({ file: 'src/reverted.py', body: 'a file no longer here' }));
		render(DiffView, inReview(review));
		// A retake brings a file that is drawn before the one already there
		const first = diffFile({ path: 'src/aardvark.py', hunks: [hunk([addedLine(1, 'new = 1')])] });
		fakeServer().answer('GET /api/diff', diffResponse({ files: [first, file] }));
		await review.diff.take();
		await drawn();

		await user.click(screen.getByTestId('thread-menu'));
		await user.click(screen.getByTestId('delete-comment'));
		await user.click(screen.getByTestId('confirm-go-ahead'));
		await drawn();

		const [firstSection] = screen.getAllByTestId('file-section');
		expect(firstSection.dataset.path).toBe(first.path);
		expect(document.activeElement).toBe(within(firstSection).getByTestId('collapse-file'));
	});
});

describe('where the keyboard is after the hidden lines are shown', () => {
	it('is on the first line shown where the gap was', async () => {
		const user = userEvent.setup();
		const near = diffFile({
			path: 'src/near.py',
			hunks: [
				hunk([removedLine(5, 'x = 1'), addedLine(5, 'x = 2')], { header: '@@ -5 +5 @@', old_start: 5, new_start: 5 })
			]
		});
		review = openReview({ files: [near] });
		const server = fakeServer();
		server.answer('GET /api/file-window', { start: 1, lines: ['one', 'two', 'three', 'four'], total: 5 });
		render(FileSection, inReview(review, { file: near }));

		await user.click(screen.getByTestId('expand-all'));
		await settled();
		await drawn();

		expect(document.activeElement).toBe(lineNumber(1));
	});
});

describe('where the keyboard is after the tour', () => {
	// The card and the header drawn on their own: jsdom lays nothing out, and
	// the whole screen's tour would find nothing on the page to show
	it('is on the help button, where the tour is taken again, once it is skipped', async () => {
		const user = userEvent.setup();
		guideServer(null);
		render(ReviewHeader, inReview(review));
		render(GuideCard, inReview(review));
		review.guide.startTour();
		await drawn();

		await user.click(screen.getByTestId('guide-skip'));
		await drawn();

		expect(document.activeElement).toBe(screen.getByTestId('open-help'));
	});

	it('is on the help button once the tour is walked to its end', async () => {
		const user = userEvent.setup();
		guideServer(null);
		render(ReviewHeader, inReview(review));
		render(GuideCard, inReview(review));
		review.guide.startTour();
		while (!review.guide.isLastStep) review.guide.next();
		await drawn();

		await user.click(screen.getByTestId('guide-next'));
		await drawn();

		expect(review.guide.touring).toBe(false);
		expect(document.activeElement).toBe(screen.getByTestId('open-help'));
	});

	it('stays in the field the reader is typing in when the welcome appears', async () => {
		guideServer(null);
		const field = document.body.appendChild(document.createElement('textarea'));
		field.focus();
		render(GuideCard, inReview(review));

		await review.guide.open();
		await drawn();

		expect(screen.getByTestId('guide-welcome')).toBeTruthy();
		expect(document.activeElement).toBe(field);
		field.remove();
	});

	it('is on the help button once the welcome is put away', async () => {
		const user = userEvent.setup();
		guideServer(null);
		await review.guide.open();
		render(ReviewHeader, inReview(review));
		render(GuideCard, inReview(review));
		await drawn();

		await user.click(screen.getAllByTestId('guide-welcome-close')[0]);
		await drawn();

		expect(document.activeElement).toBe(screen.getByTestId('open-help'));
	});
});
