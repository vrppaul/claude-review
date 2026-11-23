import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import type { PlaceLeft, ReadingViewName } from '$lib/review/reading-view';
import type { Review } from '$lib/review/review.svelte';
import { OVERVIEW_PART } from '$lib/review/story-keys';
import type { CheckFailure, FileOfTakeResponse, StoryHeld } from '$lib/types';
import { flushSync } from 'svelte';
import { storyHeld, toldChapter, toldStep } from '../story';
import { failedCheck, failure } from '../checks';
import { A_LATER_TAKE, contextLine, diffFile, diffResponse, hunk } from '../diff';
import { fakeServer } from '../fake-server';
import { frames } from '../frames';
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

// A file the change did not touch, and what the take holds of it
const ELSEWHERE = 'src/elsewhere.py';
const ELSEWHERE_OF_THE_TAKE: FileOfTakeResponse = {
	path: ELSEWHERE,
	hunks: [hunk([contextLine(null, 1, 'first'), contextLine(null, 2, 'second')], { header: '' })],
	unshown: null,
	commentable: true
};
// What a failure in the file of the change is pressed by
const IN_APP_PY = /app\.py/;

/** Press where a check failed, in a file of this name, in the pane the header's chip opens. */
async function pressFailureIn(fileName: RegExp): Promise<void> {
	const user = userEvent.setup({ delay: null });
	await user.click(screen.getByTestId('checks'));
	await user.click(within(screen.getByTestId('checks-pane')).getByRole('button', { name: fileName }));
	await settled();
}

/** A place the reader left, in a view, at the top of the reading area: within a section or a part, at a line or none. */
function leftAt(view: ReadingViewName, within: string, line: string | null, called: string): PlaceLeft {
	return { view, place: { within, line, offset: 0 }, called, calledInFull: called };
}

/** Press a control and let the page take the reader where it does, until they come to rest. */
async function press(testId: string): Promise<void> {
	await userEvent.setup({ delay: null }).click(screen.getByTestId(testId));
	await settled();
	await frames();
}

describe('going to where a check failed', () => {
	it('takes the reader to the line, the keyboard on its number', async () => {
		onScreenFailing([failure({ path: 'src/app.py', line: 2 })]);

		await pressFailureIn(IN_APP_PY);

		expect(document.activeElement?.textContent?.trim()).toBe('2');
	});

	it('brings the files on screen from a story that tells nothing of the line, and goes to it there', async () => {
		const review = onScreenFailing([failure({ path: 'src/app.py', line: 2 })], storyHeld());
		review.views.show('story');
		flushSync();

		await pressFailureIn(IN_APP_PY);

		expect(review.views.onScreen.name).toBe('files');
		expect(document.activeElement?.textContent?.trim()).toBe('2');
	});

	it('goes to the line in the story where a piece of it draws the line', async () => {
		const told = storyHeld({ chapters: [toldChapter('ch-1', [toldStep('src/app.py', 2)])] });
		const review = onScreenFailing([failure({ path: 'src/app.py', line: 2 })], told);
		review.views.show('story');
		flushSync();

		await pressFailureIn(IN_APP_PY);

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

		await pressFailureIn(IN_APP_PY);

		expect(document.activeElement?.textContent?.trim()).toBe('3');
	});

	it('reads in the lines the diff left out to reach a line between its hunks', async () => {
		const server = fakeServer();
		const read = Array.from({ length: 33 }, (_, offset) => `line ${offset + 4}`);
		server.answer('GET /api/file-window', { start: 4, lines: read, total: 50 });
		onScreenFailing([failure({ path: 'src/app.py', line: 16 })]);

		await pressFailureIn(IN_APP_PY);

		expect(document.activeElement?.textContent?.trim()).toBe('16');
	});

	it('opens a file the change did not touch alone at the line, where the review’s base holds it', async () => {
		fakeServer().answer('GET /api/file-of-take', ELSEWHERE_OF_THE_TAKE);
		onScreenFailing([failure({ path: ELSEWHERE, line: 2, held_by_base: true })]);

		await pressFailureIn(/elsewhere\.py/);
		await frames();

		expect(within(screen.getByTestId('file-alone-view')).getByTestId('file-alone-heading').textContent).toBe(ELSEWHERE);
		expect(document.activeElement?.textContent?.trim()).toBe('2');
	});

	it('goes to the renamed file in the change for the path a check failed at before the change renamed it', async () => {
		const review = openReview({
			files: [file],
			diff: { own_renames: [{ former_path: 'src/old_app.py', path: file.path }] },
			facts: { checks: [failedCheck([failure({ path: 'src/old_app.py', line: 2, held_by_base: true })])] }
		});
		render(ReviewScreen, { props: { review } });

		await pressFailureIn(/old_app\.py/);
		await frames();

		expect(screen.queryByTestId('file-alone-view')).toBeNull();
		expect(document.activeElement?.textContent?.trim()).toBe('2');
	});

	it('says where a check failed in a file neither the change nor its base holds, with no way there', async () => {
		onScreenFailing([failure({ path: ELSEWHERE, line: 2, what: 'test_elsewhere' })]);
		await userEvent.setup({ delay: null }).click(screen.getByTestId('checks'));

		const pane = screen.getByTestId('checks-pane');

		expect(within(pane).getByTestId('check-failure').textContent).toContain('test_elsewhere');
		expect(within(pane).queryByRole('button', { name: /elsewhere/ })).toBeNull();
	});
});

// Where the reader read before the page took them elsewhere is read off the page as laid out, which jsdom does not
// do: the browser tests note it (tests/e2e/test_jumps.py), and these leave it on the way back by hand
describe('going back to where the reader was before going to a line', () => {
	it('offers no way back before the page took the reader anywhere', () => {
		onScreenFailing([failure({ path: 'src/app.py', line: 2 })]);

		expect(screen.queryByTestId('go-back')).toBeNull();
	});

	it('names where it goes back to', () => {
		const review = onScreenFailing([]);

		review.wayBack.note(leftAt('files', 'src/app.py', 'new:2', 'app.py:2'));
		flushSync();

		expect(screen.getByTestId('go-back').textContent?.trim()).toBe('Back to app.py:2');
	});

	it('takes the reader back to the line they read from, the keyboard on its number, with nowhere left to go back to', async () => {
		const review = onScreenFailing([]);
		review.wayBack.note(leftAt('files', 'src/app.py', 'new:2', 'app.py:2'));
		flushSync();

		await press('go-back');

		expect(document.activeElement?.textContent?.trim()).toBe('2');
		expect(screen.queryByTestId('go-back')).toBeNull();
	});

	it("puts the keyboard on the file's own toggle going back to the top of a file, where no line was read from", async () => {
		const review = onScreenFailing([]);
		review.wayBack.note(leftAt('files', 'src/app.py', null, 'app.py'));
		flushSync();

		await press('go-back');

		expect(document.activeElement?.getAttribute('aria-label')).toContain('app.py');
	});

	it('leaves a file the reader folded folded, going back to its top', async () => {
		const review = onScreenFailing([]);
		review.reading.toggleFolded('src/app.py');
		review.wayBack.note(leftAt('files', 'src/app.py', null, 'app.py'));
		flushSync();

		await press('go-back');

		expect(review.reading.isFolded('src/app.py')).toBe(true);
	});

	it('goes back through every place left, the last first', async () => {
		const review = onScreenFailing([]);
		review.wayBack.note(leftAt('files', 'src/app.py', 'new:2', 'app.py:2'));
		review.wayBack.note(leftAt('files', 'src/app.py', 'new:3', 'app.py:3'));
		flushSync();

		await press('go-back');
		const firstBack = document.activeElement?.textContent?.trim();
		await press('go-back');

		expect([firstBack, document.activeElement?.textContent?.trim()]).toEqual(['3', '2']);
	});

	it('goes back by b, which the help lists while there is a way back', async () => {
		const review = onScreenFailing([]);
		review.wayBack.note(leftAt('files', 'src/app.py', 'new:1', 'app.py:1'));
		flushSync();
		const user = userEvent.setup({ delay: null });
		await user.keyboard('?');
		const listed = within(screen.getByTestId('shortcuts-list')).getByText('Back to where you were').textContent;
		await user.keyboard('{Escape}');

		await user.keyboard('b');
		await settled();
		await frames();

		expect([listed, document.activeElement?.textContent?.trim()]).toEqual(['Back to where you were', '1']);
	});

	it('goes back from the tree put away, by the button at the foot of its rail', async () => {
		const review = onScreenFailing([]);
		review.wayBack.note(leftAt('files', 'src/app.py', 'new:1', 'app.py:1'));
		review.layout.fileTree.toggle();
		flushSync();

		await press('go-back-on-rail');

		expect(document.activeElement?.textContent?.trim()).toBe('1');
	});

	it("brings back the story where the reader read its words, the keyboard lent to the part's head", async () => {
		const review = onScreenFailing([], storyHeld());
		review.wayBack.note(leftAt('story', OVERVIEW_PART, null, 'the overview'));
		flushSync();

		await press('go-back');

		expect(review.views.onScreen.name).toBe('story');
		expect(document.activeElement?.textContent).toContain('A change, told');
	});

	it('forgets the way back once the change is taken again, which numbers its lines anew', async () => {
		const server = fakeServer();
		server.answer('GET /api/diff', diffResponse({ files: [file], take: A_LATER_TAKE }));
		const review = onScreenFailing([]);
		review.wayBack.note(leftAt('files', 'src/app.py', 'new:1', 'app.py:1'));

		await review.diff.take();
		flushSync();

		expect(screen.queryByTestId('go-back')).toBeNull();
	});
});
