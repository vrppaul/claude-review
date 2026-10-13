import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import { catchUp, takePush } from '$lib/page/push-handling';
import type { Review } from '$lib/review/review.svelte';
import { addedLine, diffFile, diffResponse, hunk, reviewResponse } from '../diff';
import { fakeServer } from '../fake-server';
import { THIS_RUN } from '../fake-socket';
import { handOverNext, pushedAt } from '../pushes';
import { type Opened, openReview } from '../review';
import { areasWatching, scriptTheScroll, scrollTo } from '../scripted-scroll';
import { settled } from '../settled';
import { storyHeld, toldChapter, toldStep } from '../story';

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
	left_out: [{ piece: toldStep('a.py', 5).piece, changed_lines: 1 }]
});
// A review restarted on the same port: another run of it, told its story anew
const NEXT_RUN = 'next-run';
// How far the review's telling has got once it has said one thing more than the page opened on
const ONE_PUSH_ON = 1;

let review: Review;
// How to take the page drawn off the screen, as a reload does before it draws the next
let closePage: () => void;

/** Open the review as the page does, from whatever draft was kept, and draw it read as its story. */
function readAsStory(opened: Opened = {}): void {
	review = openReview({ files, story: TOLD, ...opened });
	review.views.choose('story');
	closePage = render(ReviewScreen, { props: { review } }).unmount;
}

/** Reload the page: the one drawn goes, and the review opens again from the draft it kept. */
function reload(opened: Opened = {}): void {
	closePage();
	readAsStory(opened);
}

/** The reader scrolls through a part of the story: its head comes on screen, and later its end. */
function readThrough(part: HTMLElement): void {
	scrollTo(within(part).getByTestId('part-head'));
	scrollTo(within(part).getByTestId('part-end'));
	flushSync();
}

/** The first chapter of the story, as the page draws it. */
function theBeginnings(): HTMLElement {
	const [beginnings] = screen.getAllByTestId('story-chapter');
	return beginnings;
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
function entriesNamed(): (string | null)[] {
	return screen.getAllByTestId('go-to-part').map((entry) => entry.getAttribute('aria-label'));
}

/** A server the page can catch up from: the review as it stands, its threads where they were, and the same story. */
function serverToCatchUpFrom(): void {
	const server = fakeServer();
	server.answer('GET /api/review', reviewResponse());
	server.answer('POST /api/anchors/follow', { anchors: [] });
	server.answer('GET /api/diff', diffResponse({ files }));
	server.answer('GET /api/story', { held: TOLD });
}

beforeEach(() => {
	scriptTheScroll();
	readAsStory();
});

describe('a part of a story the reader has scrolled through', () => {
	it('is none of them while the reader has scrolled nowhere', () => {
		expect(entriesNamed()).toEqual(['Overview', 'Chapter 1: The beginnings', 'Chapter 2: The end']);
		expect(countSaid()).toBe('2 chapters');
	});

	it('is a chapter whose head and whose end have each been on screen: its entry says it is read', () => {
		readThrough(theBeginnings());

		expect(entriesNamed()).toEqual(['Overview', 'Chapter 1: The beginnings, read', 'Chapter 2: The end']);
	});

	it('is counted among the chapters, in the head of the contents', () => {
		readThrough(theBeginnings());

		expect(countSaid()).toBe('1 of 2 read');
	});

	it('shows a check where its number stood', () => {
		readThrough(theBeginnings());

		const ofTheBeginnings = within(entryOfTheBeginnings());
		expect(ofTheBeginnings.getByTestId('part-read-mark')).toBeTruthy();
		expect(ofTheBeginnings.getByTestId('go-to-part').textContent.trim()).toBe('The beginnings');
	});

	it('is not a chapter whose head alone has been on screen', () => {
		scrollTo(within(theBeginnings()).getByTestId('part-head'));
		flushSync();

		expect(countSaid()).toBe('2 chapters');
	});

	it('is not a chapter whose end alone has been on screen', () => {
		scrollTo(within(theBeginnings()).getByTestId('part-end'));
		flushSync();

		expect(countSaid()).toBe('2 chapters');
	});

	it('is the overview too, which is no chapter and is not counted as one', () => {
		readThrough(screen.getByTestId('story-overview'));

		expect(entriesNamed()).toEqual(['Overview, read', 'Chapter 1: The beginnings', 'Chapter 2: The end']);
		expect(countSaid()).toBe('2 chapters');
	});

	it('is never what the story leaves out: the contents say nothing more of it', () => {
		readThrough(screen.getByTestId('story-left-out'));

		expect(screen.getByTestId('contents-left-out').textContent.trim()).toBe('Not in the story');
		expect(within(screen.getByTestId('contents')).queryByTestId('part-read-mark')).toBeNull();
		expect(countSaid()).toBe('2 chapters');
	});

	it('is watched for within the area the story scrolls in, not within the page', () => {
		const end = within(theBeginnings()).getByTestId('part-end');

		expect(areasWatching(end)).toEqual([screen.getByTestId('story-view')]);
	});
});

describe('what the reader has read of a story, once the story is told again', () => {
	it('is nothing: what was read of the story before is no reading of this one', async () => {
		readThrough(theBeginnings());
		fakeServer().answer('GET /api/story', { held: TOLD });

		handOverNext(review, { type: 'story' });
		await settled();
		flushSync();

		expect(countSaid()).toBe('2 chapters');
	});

	it('is as much as before when the page only caught up on what it missed: the story is read again, not told again', async () => {
		readThrough(theBeginnings());
		serverToCatchUpFrom();

		await catchUp(review, { instance: THIS_RUN, sequence: 0 });
		flushSync();

		expect(countSaid()).toBe('1 of 2 read');
	});
});

describe('what the reader has read of a story, when the page is opened again', () => {
	it('is as they left it: the draft keeps it', () => {
		readThrough(theBeginnings());

		reload();

		expect(entriesNamed()).toEqual(['Overview', 'Chapter 1: The beginnings, read', 'Chapter 2: The end']);
		expect(countSaid()).toBe('1 of 2 read');
	});

	it('is nothing in another run of the review, which was told its story anew', () => {
		readThrough(theBeginnings());

		reload({ facts: { instance: NEXT_RUN } });

		expect(countSaid()).toBe('2 chapters');
	});

	it('is nothing once the page hears the story was told again while it was away, though it opened on that story', () => {
		readThrough(theBeginnings());
		reload({ facts: { sequence: ONE_PUSH_ON } });

		takePush(review, { type: 'story' }, pushedAt(ONE_PUSH_ON));
		flushSync();

		expect(countSaid()).toBe('2 chapters');
	});
});
