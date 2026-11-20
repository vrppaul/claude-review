import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import type { Review } from '$lib/review/review.svelte';
import type { CheckFailure, StoryHeld } from '$lib/types';
import { flushSync } from 'svelte';
import { storyHeld, toldChapter, toldStep } from '../story';
import { failedCheck, failure } from '../checks';
import { contextLine, diffFile, diffResponse, hunk } from '../diff';
import { fakeServer } from '../fake-server';
import { openReview } from '../review';
import { settled } from '../settled';

// A file whose lines 1 to 3 and 50 the diff holds: 4 to 49 lie between its hunks, unchanged
const file = diffFile({
	path: 'src/app.py',
	hunks: [
		hunk([contextLine(1, 1, 'one'), contextLine(2, 2, 'two'), contextLine(3, 3, 'three')]),
		hunk([contextLine(50, 50, 'fifty')], { header: '', old_start: 50, new_start: 50 })
	]
});

/** The review on screen, holding a check that failed where these say, and the story told of it, if any. */
function onScreenFailing(failures: CheckFailure[], story: StoryHeld | null = null): Review {
	const review = openReview({ files: [file], story, facts: { checks: [failedCheck(failures, { name: 'pytest' })] } });
	render(ReviewScreen, { props: { review } });
	return review;
}

/** Press where a check failed, in the pane the header's chip opens: the first failure, or the one at this place. */
async function pressFailure(where: RegExp = /app\.py/): Promise<void> {
	const user = userEvent.setup({ delay: null });
	await user.click(screen.getByTestId('checks'));
	await user.click(within(screen.getByTestId('checks-pane')).getByRole('button', { name: where }));
	await settled();
}

/** The number of a line drawn in the files, to put the keyboard on. */
function lineNumber(number: number): HTMLElement | undefined {
	return screen.getAllByTestId('line-gutter').find((gutter) => gutter.textContent?.trim() === String(number));
}

/** Press a control and let the page take the reader where it does. */
async function press(testId: string): Promise<void> {
	await userEvent.setup({ delay: null }).click(screen.getByTestId(testId));
	await settled();
}

describe('going to where a check failed', () => {
	it('takes the reader to the line, the keyboard on its number', async () => {
		onScreenFailing([failure({ path: 'src/app.py', line: 2 })]);

		await pressFailure();

		expect(document.activeElement?.textContent?.trim()).toBe('2');
	});

	it('lights the line it takes the reader to', async () => {
		const review = onScreenFailing([failure({ path: 'src/app.py', line: 2 })]);

		await pressFailure();

		expect(review.sections.arrived.lineIn('src/app.py')).toBe('new:2');
	});

	it('puts the light out once the keyboard leaves the line: a line gone to by j is not lit', async () => {
		const review = onScreenFailing([failure({ path: 'src/app.py', line: 2 })]);
		await pressFailure();

		await userEvent.setup({ delay: null }).keyboard('j');

		expect(review.sections.arrived.lineIn('src/app.py')).toBeNull();
	});

	it('keeps the line lit while the window alone loses the keyboard', async () => {
		const review = onScreenFailing([failure({ path: 'src/app.py', line: 2 })]);
		await pressFailure();

		// A window the reader leaves blurs what holds the keyboard, which holds it still for the page
		document.activeElement?.dispatchEvent(new FocusEvent('blur'));

		expect(review.sections.arrived.lineIn('src/app.py')).toBe('new:2');
	});

	it('brings the files on screen from a story that tells nothing of the line, and goes to it there', async () => {
		const review = onScreenFailing([failure({ path: 'src/app.py', line: 2 })], storyHeld());
		review.views.showStory();
		flushSync();

		await pressFailure();

		expect(review.views.onScreen.name).toBe('files');
		expect(document.activeElement?.textContent?.trim()).toBe('2');
	});

	it('goes to the line in the story where a piece of it draws the line', async () => {
		const told = storyHeld({ chapters: [toldChapter('ch-1', [toldStep('src/app.py', 2)])] });
		const review = onScreenFailing([failure({ path: 'src/app.py', line: 2 })], told);
		review.views.showStory();
		flushSync();

		await pressFailure();

		expect(review.views.onScreen.name).toBe('story');
		expect(document.activeElement?.textContent?.trim()).toBe('2');
	});

	it('puts the pane away at the press, while the lines it reads in are on their way', async () => {
		const server = fakeServer();
		server.answer('GET /api/file-window', { start: 4, lines: [], total: 50 });
		onScreenFailing([failure({ path: 'src/app.py', line: 16 })]);
		const user = userEvent.setup({ delay: null });
		await user.click(screen.getByTestId('checks'));

		await user.click(within(screen.getByTestId('checks-pane')).getByRole('button', { name: /app\.py/ }));

		expect(screen.queryByTestId('checks-pane')).toBeNull();
	});

	it('unfolds the file the line is in', async () => {
		const review = onScreenFailing([failure({ path: 'src/app.py', line: 3 })]);
		review.reading.toggleFolded('src/app.py');

		await pressFailure();

		expect(document.activeElement?.textContent?.trim()).toBe('3');
	});

	it('reads in the lines the diff left out to reach a line between its hunks', async () => {
		const server = fakeServer();
		const read = Array.from({ length: 33 }, (_, offset) => `line ${offset + 4}`);
		server.answer('GET /api/file-window', { start: 4, lines: read, total: 50 });
		onScreenFailing([failure({ path: 'src/app.py', line: 16 })]);

		await pressFailure();

		expect(document.activeElement?.textContent?.trim()).toBe('16');
	});

	it('says where a check failed in a file the review does not hold, with no way there', async () => {
		onScreenFailing([failure({ path: 'src/elsewhere.py', line: 2, what: 'test_elsewhere' })]);
		await userEvent.setup({ delay: null }).click(screen.getByTestId('checks'));

		const pane = screen.getByTestId('checks-pane');

		expect(within(pane).getByTestId('check-failure').textContent).toContain('test_elsewhere');
		expect(within(pane).queryByRole('button', { name: /elsewhere/ })).toBeNull();
	});
});

describe('going back to where the reader was before going to a line', () => {
	it('offers no way back before the page took the reader anywhere', () => {
		onScreenFailing([failure({ path: 'src/app.py', line: 2 })]);

		expect(screen.queryByTestId('go-back')).toBeNull();
	});

	it('names the line read from, the first at the top of the file being read, by its file and number', async () => {
		onScreenFailing([failure({ path: 'src/app.py', line: 50 })]);

		await pressFailure();

		expect(screen.getByTestId('go-back').textContent?.trim()).toBe('Back to app.py:1');
	});

	it('takes the reader back to that line, the keyboard on its number, with nowhere left to go back to', async () => {
		onScreenFailing([failure({ path: 'src/app.py', line: 50 })]);
		await pressFailure();

		await press('go-back');

		expect(document.activeElement?.textContent?.trim()).toBe('1');
		expect(screen.queryByTestId('go-back')).toBeNull();
	});

	it('goes back through every place left, the last first, each the line the keyboard was on', async () => {
		const review = onScreenFailing([]);
		lineNumber(3)?.focus();
		await review.navigator.goToLine('src/app.py', 2);
		await settled();
		await review.navigator.goToLine('src/app.py', 50);
		await settled();

		await press('go-back');
		const firstBack = document.activeElement?.textContent?.trim();
		await press('go-back');

		expect([firstBack, document.activeElement?.textContent?.trim()]).toEqual(['2', '3']);
	});

	it('goes back by b, which the help lists while there is a way back', async () => {
		onScreenFailing([failure({ path: 'src/app.py', line: 50 })]);
		await pressFailure();
		const user = userEvent.setup({ delay: null });
		await user.keyboard('?');
		const listed = within(screen.getByTestId('shortcuts-list')).getByText('Back to where you were').textContent;
		await user.keyboard('{Escape}');

		await user.keyboard('b');
		await settled();

		expect([listed, document.activeElement?.textContent?.trim()]).toEqual(['Back to where you were', '1']);
	});

	it('goes back from the tree put away, by the button at the foot of its rail', async () => {
		const review = onScreenFailing([failure({ path: 'src/app.py', line: 50 })]);
		await pressFailure();
		review.layout.fileTree.toggle();
		flushSync();

		await press('go-back-on-rail');

		expect(document.activeElement?.textContent?.trim()).toBe('1');
	});

	it('brings back the story the reader read in, at the line they read from in it', async () => {
		const told = storyHeld({ chapters: [toldChapter('ch-1', [toldStep('src/app.py', 1)])] });
		const review = onScreenFailing([failure({ path: 'src/app.py', line: 50 })], told);
		review.views.showStory();
		flushSync();
		await pressFailure();

		await press('go-back');

		expect(review.views.onScreen.name).toBe('story');
		expect(document.activeElement?.textContent?.trim()).toBe('1');
	});

	it('forgets the way back once the diff is taken again, which may number the lines anew', async () => {
		const server = fakeServer();
		server.answer('GET /api/diff', diffResponse({ files: [file] }));
		const review = onScreenFailing([failure({ path: 'src/app.py', line: 50 })]);
		await pressFailure();

		await review.diff.take();
		flushSync();

		expect(screen.queryByTestId('go-back')).toBeNull();
	});
});
