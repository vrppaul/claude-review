import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import { flushSync } from 'svelte';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import type { Review } from '$lib/review/review.svelte';
import { addedLine, diffFile, hunk } from '../diff';
import { broughtIntoView, said } from '../elements';
import { newComment, storyComment } from '../new-comment';
import { openReview } from '../review';
import { scriptTheScroll, scrollTo } from '../scripted-scroll';
import { storyHeld, toldChapter, toldStep } from '../story';

// The change under review: a.py gained lines 1, 5 and 9, b.py a line, and so did a lock file
const files = [
	diffFile({ path: 'src/a.py', hunks: [hunk([addedLine(1, 'one'), addedLine(5, 'five'), addedLine(9, 'nine')])] }),
	diffFile({ path: 'src/b.py', hunks: [hunk([addedLine(5, 'in b.py')])] }),
	diffFile({ path: 'uv.lock', hunks: [hunk([addedLine(1, 'locked')])] })
];
// The story told of it: line 1 of a.py and b.py in a first chapter, line 9 of a.py in a second; line 5
// of a.py is told by no step, and the lock file is housekeeping
const TOLD = storyHeld({
	chapters: [
		toldChapter('ch-1', [toldStep('src/a.py', 1), toldStep('src/b.py', 5)], { title: 'The beginnings' }),
		toldChapter('ch-2', [toldStep('src/a.py', 9)], { title: 'The end' })
	],
	left_out: [{ piece: toldStep('src/a.py', 5).piece, changed_lines: 1 }],
	housekeeping: ['uv.lock']
});

let review: Review;

/** The contents' entries, in the order they stand down its axis: the overview, then the chapters. */
function entries(): HTMLElement[] {
	return screen.getAllByTestId('contents-entry');
}

/** The rows of the files the contents lists, down the column: each chapter's, then what is left out. */
function fileRows(): HTMLElement[] {
	return screen.getAllByTestId('contents-file');
}

describe('the contents beside a story', () => {
	beforeEach(() => {
		// A story nobody has scrolled yet: with everything on screen at once, all of it would be read through as it is drawn
		scriptTheScroll();
		review = openReview({ files, story: TOLD });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });
	});

	it('is a way through the story, named as one', () => {
		expect(screen.getByRole('navigation', { name: 'Story contents' })).toBe(screen.getByTestId('contents'));
	});

	it('counts the chapters in its head', () => {
		expect(screen.getByTestId('contents-count').textContent).toBe('2 chapters');
	});

	it('lists the overview, then every chapter by its number and its title', () => {
		expect(entries().map((entry) => said(within(entry).getByTestId('go-to-part')))).toEqual([
			'Overview',
			'1 The beginnings',
			'2 The end'
		]);
	});

	it('marks the overview and each chapter that draw a thread, and says how many', () => {
		review.threads.add(storyComment({ at: 'overview', text: 'task' }, 'on the task'));
		review.threads.add(newComment({ file: 'src/a.py', startLine: 9, body: 'in the end' }));
		review.threads.add(newComment({ file: 'src/a.py', startLine: 9, body: 'in the end again' }));
		flushSync();

		const marked = entries().map((entry) => within(entry).queryAllByTestId('part-threads').length);
		const contents = within(screen.getByTestId('contents'));

		expect(marked).toEqual([1, 0, 1]);
		expect(contents.getByRole('button', { name: 'Overview, 1 thread' })).toBeTruthy();
		expect(contents.getByRole('button', { name: 'Chapter 2: The end, 2 threads' })).toBeTruthy();
	});

	it('names each entry in full to whoever cannot see its node', () => {
		const contents = within(screen.getByTestId('contents'));

		expect(contents.getByRole('button', { name: 'Overview' })).toBeTruthy();
		expect(contents.getByRole('button', { name: 'Chapter 2: The end' })).toBeTruthy();
	});

	it('lists under each chapter the files it tells, by their names without their folders', () => {
		const [overview, beginnings, end] = entries();

		expect(within(overview).queryAllByTestId('contents-file')).toEqual([]);
		expect(
			within(beginnings)
				.getAllByText(/\.py$/)
				.map((name) => name.textContent)
		).toEqual(['a.py', 'b.py']);
		expect(
			within(end)
				.getAllByText(/\.py$/)
				.map((name) => name.textContent)
		).toEqual(['a.py']);
	});

	it('says what became of each file, and how much the whole story changes it', () => {
		const [ofAInTheBeginnings] = fileRows();

		// Three lines of a.py in all: two told by steps, one by none
		expect(within(ofAInTheBeginnings).getByText('modified')).toBeTruthy();
		expect(within(ofAInTheBeginnings).getByText('+3')).toBeTruthy();
	});

	it('says where else a file is told, in place of its change, in a chapter that is not the first to tell it', () => {
		const [, , ofAInTheEnd] = fileRows();

		expect(within(ofAInTheEnd).getByText('also in 1')).toBeTruthy();
		expect(within(ofAInTheEnd).queryByText('+3')).toBeNull();
	});

	it('takes the reader to a part of the story when its entry is pressed', async () => {
		const user = userEvent.setup();
		const [, theEnd] = screen.getAllByTestId('story-chapter');
		const toTheEnd = broughtIntoView(theEnd);

		await user.click(within(entries()[2]).getByTestId('go-to-part'));

		expect(toTheEnd).toHaveBeenCalledWith({ block: 'start', behavior: 'instant' });
	});

	it('takes the reader to the step that tells a file in that chapter when the file is pressed', async () => {
		const user = userEvent.setup();
		const [, , ofLineNine] = screen.getAllByTestId('story-piece');
		const toLineNine = broughtIntoView(ofLineNine);
		const [, , ofAInTheEnd] = fileRows();

		await user.click(ofAInTheEnd);

		expect(toLineNine).toHaveBeenCalled();
	});

	it('lists what the story leaves out under what says so, by how many hunks of each file no step tells', () => {
		const [, , , leftOutOfA] = fileRows();

		expect(screen.getByTestId('contents-left-out').textContent.trim()).toBe('Not in the story');
		expect(within(leftOutOfA).getByText('a.py')).toBeTruthy();
		expect(within(leftOutOfA).getByText('1 hunk')).toBeTruthy();
	});

	it('takes the reader to what the story leaves out', async () => {
		const user = userEvent.setup();
		const toWhatIsLeftOut = broughtIntoView(screen.getByTestId('story-left-out'));

		await user.click(screen.getByTestId('contents-left-out'));

		expect(toWhatIsLeftOut).toHaveBeenCalledWith({ block: 'start', behavior: 'instant' });
	});

	it('names the files the agent called housekeeping', () => {
		const housekeeping = screen.getByTestId('contents-housekeeping');

		expect(within(housekeeping).getByText('Housekeeping · 1 file')).toBeTruthy();
		expect(housekeeping.textContent).toContain('uv.lock');
	});

	it('is put away to a rail and brought back by itself: the tree of files is left as it was', async () => {
		const user = userEvent.setup();
		const treeOpen = review.layout.fileTree.open;

		await user.click(screen.getByTestId('hide-contents'));
		expect(screen.queryByTestId('contents')).toBeNull();
		expect(review.layout.fileTree.open).toBe(treeOpen);

		await user.click(screen.getByTestId('show-contents'));
		expect(screen.getByTestId('contents')).toBeTruthy();
	});
});

describe('the contents beside a story, as the reader scrolls', () => {
	beforeEach(() => {
		scriptTheScroll();
		review = openReview({ files, story: TOLD });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });
	});

	it('marks no entry while no part of the story is at the top of what is read', () => {
		expect(screen.getAllByTestId('go-to-part').map((entry) => entry.getAttribute('aria-current'))).toEqual([
			null,
			null,
			null
		]);
	});

	it('marks the entry of the part being read', () => {
		const [, theEnd] = screen.getAllByTestId('story-chapter');

		scrollTo(theEnd);
		flushSync();

		expect(screen.getAllByTestId('go-to-part').map((entry) => entry.getAttribute('aria-current'))).toEqual([
			null,
			null,
			'location'
		]);
	});

	it('marks the file of the step being read, in the chapter that tells that step and in no other', () => {
		const [theBeginnings] = screen.getAllByTestId('story-chapter');
		const [ofLineOne] = screen.getAllByTestId('story-piece');

		scrollTo(theBeginnings, ofLineOne);
		flushSync();

		// a.py in the beginnings, b.py, a.py in the end, and what is left out of a.py
		expect(fileRows().map((row) => row.getAttribute('aria-current'))).toEqual(['true', null, null, null]);
	});

	it('marks the file left out while what no step tells of it is read', () => {
		const [, , , leftOutOfLineFive] = screen.getAllByTestId('story-piece');

		scrollTo(leftOutOfLineFive);
		flushSync();

		expect(fileRows().map((row) => row.getAttribute('aria-current'))).toEqual([null, null, null, 'true']);
	});

	it('marks what the story leaves out while the reader is in it', () => {
		scrollTo(screen.getByTestId('story-left-out'));
		flushSync();

		expect(screen.getByTestId('contents-left-out').getAttribute('aria-current')).toBe('location');
	});
});

describe('the contents of a story that tells every change, and names no housekeeping', () => {
	it('says nothing of what is left out, nor of housekeeping', () => {
		review = openReview({ files, story: storyHeld() });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		expect(screen.queryByTestId('contents-left-out')).toBeNull();
		expect(screen.queryByTestId('contents-housekeeping')).toBeNull();
	});
});

describe('a file a story leaves out whole, which shows no line', () => {
	it('is listed with no count of hunks: it has none', () => {
		const picture = diffFile({ path: 'docs/logo.png', status: 'added', unshown: 'binary' });
		review = openReview({ files, story: storyHeld({ left_out: [{ piece: picture, changed_lines: 0 }] }) });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		// The one file the story's one chapter tells, then the picture
		const [, ofThePicture] = fileRows();

		expect(said(ofThePicture)).toBe('A added logo.png');
	});
});

describe('a review nobody has told a story of yet', () => {
	it('draws no contents where its story would be, nor a rail to bring one back', () => {
		review = openReview({ files });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		expect(screen.queryByTestId('contents')).toBeNull();
		expect(screen.queryByTestId('show-contents')).toBeNull();
	});
});
