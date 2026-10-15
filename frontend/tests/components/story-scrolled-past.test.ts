import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import type { Review } from '$lib/review/review.svelte';
import { addedLine, diffFile, hunk } from '../diff';
import { openReview } from '../review';
import { scriptTheScroll, scrollTo } from '../scripted-scroll';
import { gainedPiece, storyHeld, toldChapter, toldStep } from '../story';

// The change under review, and the story told of it: two chapters of a step each, and a line of a.py no step tells
const files = [
	diffFile({ path: 'a.py', hunks: [hunk([addedLine(1, 'one'), addedLine(5, 'five')])] }),
	diffFile({ path: 'b.py', hunks: [hunk([addedLine(1, 'in b.py')])] })
];
const TOLD = storyHeld({
	chapters: [
		toldChapter('ch-1', [toldStep('a.py', 1)], { title: 'The beginnings' }),
		toldChapter('ch-2', [toldStep('b.py', 1)], { title: 'The end' })
	],
	left_out: [{ piece: gainedPiece('a.py', 5, 5), changed_lines: 1 }]
});

let review: Review;
// How to take the page drawn off the screen, as a reload does before it draws the next
let closePage: () => void;

/** Open the review as the page does, and draw it read as its story. */
function readAsStory(): void {
	review = openReview({ files, story: TOLD });
	review.views.choose('story');
	closePage = render(ReviewScreen, { props: { review } }).unmount;
}

/** The reader scrolls until a part of the story is the one at the top of what they read. */
function readIn(part: HTMLElement): void {
	scrollTo(part);
	flushSync();
}

/** The chapters of the story, as the page draws them. */
function chapters(): { theBeginnings: HTMLElement; theEnd: HTMLElement } {
	const [theBeginnings, theEnd] = screen.getAllByTestId('story-chapter');
	return { theBeginnings, theEnd };
}

/** The contents' entry of the first chapter: the overview's comes before it. */
function entryOfTheBeginnings(): HTMLElement {
	const [, ofTheBeginnings] = screen.getAllByTestId('contents-entry');
	return ofTheBeginnings;
}

/** What the head of the contents says of the story's chapters. */
function countSaid(): string {
	return screen.getByTestId('contents-count').textContent.trim();
}

/** What every entry of the contents is called, down its axis. */
function entriesCalled(): (string | null)[] {
	return screen.getAllByTestId('go-to-part').map((entry) => entry.getAttribute('aria-label'));
}

beforeEach(() => {
	scriptTheScroll();
	readAsStory();
});

describe('the parts of a story ticked in its contents', () => {
	it('are none while the reader is in no part of it', () => {
		expect(entriesCalled()).toEqual(['Overview', 'Chapter 1: The beginnings', 'Chapter 2: The end']);
		expect(countSaid()).toBe('2 chapters');
	});

	it('are none while the reader is in the part the story begins with', () => {
		readIn(screen.getByTestId('story-overview'));

		expect(entriesCalled()).toEqual(['Overview', 'Chapter 1: The beginnings', 'Chapter 2: The end']);
	});

	it('are the parts above the one the reader is in, and not that one', () => {
		readIn(chapters().theBeginnings);

		expect(entriesCalled()).toEqual(['Overview, read', 'Chapter 1: The beginnings', 'Chapter 2: The end']);
	});

	it('are every part above, however the reader came where they are: one they jumped over too', () => {
		readIn(chapters().theEnd);

		expect(entriesCalled()).toEqual(['Overview, read', 'Chapter 1: The beginnings, read', 'Chapter 2: The end']);
	});

	it('are counted among the chapters in the head of the contents, the overview being no chapter', () => {
		readIn(chapters().theEnd);

		expect(countSaid()).toBe('1 of 2 read');
	});

	it('show a check where a number stood', () => {
		readIn(chapters().theEnd);

		const ofTheBeginnings = within(entryOfTheBeginnings());
		expect(ofTheBeginnings.getByTestId('part-read-mark')).toBeTruthy();
		expect(ofTheBeginnings.getByTestId('go-to-part').textContent.trim()).toBe('The beginnings');
	});

	it('lose their tick once the reader scrolls back up into them', () => {
		readIn(chapters().theEnd);

		readIn(chapters().theBeginnings);

		expect(entriesCalled()).toEqual(['Overview, read', 'Chapter 1: The beginnings', 'Chapter 2: The end']);
		expect(countSaid()).toBe('2 chapters');
	});

	it('are every chapter while the reader is in what the story leaves out, which the contents tick nowhere', () => {
		readIn(screen.getByTestId('story-left-out'));

		expect(countSaid()).toBe('2 of 2 read');
		expect(screen.getByTestId('contents-left-out').textContent.trim()).toBe('Not in the story');
	});

	it('are none once the page is opened again before the reader is anywhere: where they were is not kept', () => {
		readIn(chapters().theEnd);

		closePage();
		readAsStory();

		expect(countSaid()).toBe('2 chapters');
	});
});
