import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import { flushSync } from 'svelte';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import type { Review } from '$lib/review/review.svelte';
import { addedLine, diffFile, hunk } from '../diff';
import { broughtIntoView, said } from '../elements';
import { fakeServer } from '../fake-server';
import { handOverNext } from '../pushes';
import { openReview } from '../review';
import { scriptTheScroll, scrollTo } from '../scripted-scroll';
import { settled } from '../settled';
import { gainedPiece, storyHeld, storyResponse, toldChapter, toldStep } from '../story';

// The change under review, and the story told of it: a first chapter of two steps, then two chapters
// of a step each, and a line of a.py no step tells
const files = [
	diffFile({ path: 'a.py', hunks: [hunk([addedLine(1, 'one'), addedLine(5, 'five'), addedLine(9, 'nine')])] }),
	diffFile({ path: 'b.py', hunks: [hunk([addedLine(1, 'in b.py')])] }),
	diffFile({ path: 'c.py', hunks: [hunk([addedLine(1, 'in c.py')])] })
];
const TOLD = storyHeld({
	chapters: [
		toldChapter('ch-1', [toldStep('a.py', 1), toldStep('a.py', 5)], { title: 'The beginnings' }),
		toldChapter('ch-2', [toldStep('b.py', 1)], { title: 'The middle' }),
		toldChapter('ch-3', [toldStep('c.py', 1)], { title: 'The end' })
	],
	left_out: [{ piece: gainedPiece('a.py', 9, 9), changed_lines: 1 }]
});

let review: Review;

/** The reader scrolled until these, and only these, are in view, and the page has drawn what follows from it. */
function readerAt(...shown: HTMLElement[]): void {
	scrollTo(...shown);
	flushSync();
}

beforeEach(() => {
	scriptTheScroll();
	review = openReview({ files, story: TOLD });
	review.views.choose('story');
	render(ReviewScreen, { props: { review } });
});

describe('the bar a chapter of a story is read under', () => {
	it('is not drawn while no part of the story is being read', () => {
		expect(screen.queryByTestId('chapter-bar')).toBeNull();
	});

	it('says the number and the title of the chapter the reader is deep in: its head has left what is read', () => {
		const [, theMiddle] = screen.getAllByTestId('story-chapter');

		readerAt(theMiddle);

		const bar = within(screen.getByTestId('chapter-bar'));
		expect(bar.getByTestId('chapter-bar-number').textContent).toBe('2');
		expect(bar.getByTestId('chapter-bar-title').textContent).toBe('The middle');
	});

	it('is not drawn while the head of the chapter being read is in view', () => {
		const [, theMiddle] = screen.getAllByTestId('story-chapter');

		readerAt(theMiddle, within(theMiddle).getByTestId('part-head'));

		expect(screen.queryByTestId('chapter-bar')).toBeNull();
	});

	it('goes once the reader is back at the head of the chapter', () => {
		const [, theMiddle] = screen.getAllByTestId('story-chapter');
		readerAt(theMiddle);

		readerAt(theMiddle, within(theMiddle).getByTestId('part-head'));

		expect(screen.queryByTestId('chapter-bar')).toBeNull();
	});

	it('is not drawn at the head of a chapter the story gained when it was told again, with its area watched already', async () => {
		const withAnAfterword = [
			...TOLD.story.chapters,
			toldChapter('ch-4', [toldStep('a.py', 9)], { title: 'The afterword' })
		];
		fakeServer().answer('GET /api/story', storyResponse({ held: storyHeld({ chapters: withAnAfterword }) }));
		handOverNext(review, { type: 'story' });
		await settled();
		const [, , , theAfterword] = screen.getAllByTestId('story-chapter');

		readerAt(theAfterword, within(theAfterword).getByTestId('part-head'));

		expect(screen.queryByTestId('chapter-bar')).toBeNull();
	});

	it('is not drawn deep in the overview, which is no chapter', () => {
		readerAt(screen.getByTestId('story-overview'));

		expect(screen.queryByTestId('chapter-bar')).toBeNull();
	});

	it('is not drawn deep in what the story leaves out, which is no chapter', () => {
		readerAt(screen.getByTestId('story-left-out'));

		expect(screen.queryByTestId('chapter-bar')).toBeNull();
	});
});

describe('the step the bar of a chapter says is being read', () => {
	it('is the one being read, by its place among the steps of the chapter', () => {
		const [theBeginnings] = screen.getAllByTestId('story-chapter');
		const [, ofLineFive] = screen.getAllByTestId('story-piece');

		readerAt(theBeginnings, ofLineFive);

		expect(screen.getByTestId('chapter-bar-step').textContent).toBe('step 2 of 2');
	});

	it('is none while no step is being read: the reader is in why the changes belong together', () => {
		const [theBeginnings] = screen.getAllByTestId('story-chapter');

		readerAt(theBeginnings);

		expect(screen.getByTestId('chapter-bar')).toBeTruthy();
		expect(screen.queryByTestId('chapter-bar-step')).toBeNull();
	});

	it('is never a step of another chapter', () => {
		const [theBeginnings] = screen.getAllByTestId('story-chapter');
		const [, , ofTheMiddle] = screen.getAllByTestId('story-piece');

		readerAt(theBeginnings, ofTheMiddle);

		expect(screen.getByTestId('chapter-bar')).toBeTruthy();
		expect(screen.queryByTestId('chapter-bar-step')).toBeNull();
	});
});

describe('the ways the bar of a chapter leads to its neighbours', () => {
	it('are the chapter before and the chapter after, each by its number', () => {
		const [, theMiddle] = screen.getAllByTestId('story-chapter');

		readerAt(theMiddle);

		expect(said(screen.getByTestId('go-to-chapter-before'))).toBe('Chapter 1');
		expect(said(screen.getByTestId('go-to-chapter-after'))).toBe('Chapter 3');
	});

	it('are the chapter after alone in the first chapter', () => {
		const [theBeginnings] = screen.getAllByTestId('story-chapter');

		readerAt(theBeginnings);

		expect(screen.queryByTestId('go-to-chapter-before')).toBeNull();
		expect(said(screen.getByTestId('go-to-chapter-after'))).toBe('Chapter 2');
	});

	it('are the chapter before alone in the last chapter', () => {
		const [, , theEnd] = screen.getAllByTestId('story-chapter');

		readerAt(theEnd);

		expect(said(screen.getByTestId('go-to-chapter-before'))).toBe('Chapter 2');
		expect(screen.queryByTestId('go-to-chapter-after')).toBeNull();
	});

	it('take the reader to the head of the chapter after, at once', async () => {
		const user = userEvent.setup();
		const [, theMiddle, theEnd] = screen.getAllByTestId('story-chapter');
		const toTheEnd = broughtIntoView(theEnd);
		readerAt(theMiddle);

		await user.click(screen.getByTestId('go-to-chapter-after'));

		expect(toTheEnd).toHaveBeenCalledWith({ block: 'start', behavior: 'instant' });
	});

	it('leave no bar over the head they took the reader to, before the page has looked where it stands', async () => {
		const user = userEvent.setup();
		const [, theMiddle] = screen.getAllByTestId('story-chapter');
		readerAt(theMiddle);

		await user.click(screen.getByTestId('go-to-chapter-after'));

		expect(screen.queryByTestId('chapter-bar')).toBeNull();
	});

	it('take the reader to the head of the chapter before, at once', async () => {
		const user = userEvent.setup();
		const [theBeginnings, theMiddle] = screen.getAllByTestId('story-chapter');
		const toTheBeginnings = broughtIntoView(theBeginnings);
		readerAt(theMiddle);

		await user.click(screen.getByTestId('go-to-chapter-before'));

		expect(toTheBeginnings).toHaveBeenCalledWith({ block: 'start', behavior: 'instant' });
	});
});
