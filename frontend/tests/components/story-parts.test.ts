import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import type { Review } from '$lib/review/review.svelte';
import { LEFT_OUT_PART, OVERVIEW_PART } from '$lib/review/story-keys';
import { addedLine, diffFile, hunk } from '../diff';
import { broughtIntoView } from '../elements';
import { fakeServer } from '../fake-server';
import { frames } from '../frames';
import { handOverNext } from '../pushes';
import { openReview } from '../review';
import { areasWatching, scriptTheScroll, scrollTo } from '../scripted-scroll';
import { settled } from '../settled';
import { storyHeld, toldChapter, toldStep } from '../story';

// The change under review, and the story told of it: two chapters of a step each, and a line of a.py no step tells
const files = [
	diffFile({ path: 'a.py', hunks: [hunk([addedLine(1, 'one'), addedLine(5, 'five')])] }),
	diffFile({ path: 'b.py', hunks: [hunk([addedLine(1, 'in b.py')])] })
];
const stepOfTheBeginnings = toldStep('a.py', 1);
const TOLD = storyHeld({
	chapters: [
		toldChapter('ch-1', [stepOfTheBeginnings], { title: 'The beginnings' }),
		toldChapter('ch-2', [toldStep('b.py', 1)], { title: 'The end' })
	],
	left_out: [{ piece: toldStep('a.py', 5).piece, changed_lines: 1 }]
});

let review: Review;

beforeEach(() => {
	scriptTheScroll();
	review = openReview({ files, story: TOLD });
	review.views.choose('story');
	render(ReviewScreen, { props: { review } });
});

describe('the part of a story being read', () => {
	it('is none while none of them is at the top of what is read', () => {
		expect(review.parts.beingRead).toBeNull();
	});

	it('is the overview while the head of the story is at the top', () => {
		scrollTo(screen.getByTestId('story-overview'));

		expect(review.parts.beingRead).toBe(OVERVIEW_PART);
	});

	it('is the chapter the reader has scrolled to, though no step of it is at the top', () => {
		const [, theEnd] = screen.getAllByTestId('story-chapter');
		const [, ofTheEnd] = review.story.contents.chapters;

		scrollTo(theEnd);

		expect(review.parts.beingRead).toBe(ofTheEnd.part);
	});

	it('is what the story leaves out, once the reader is there', () => {
		scrollTo(screen.getByTestId('story-left-out'));

		expect(review.parts.beingRead).toBe(LEFT_OUT_PART);
	});

	it('is followed within the area the story scrolls in, not within the page', () => {
		const [theBeginnings] = screen.getAllByTestId('story-chapter');

		expect(areasWatching(theBeginnings)).toEqual([screen.getByTestId('story-view')]);
	});

	it('is no longer a chapter the story, told again, has dropped', async () => {
		const [, theEnd] = screen.getAllByTestId('story-chapter');
		const [onlyTheBeginnings] = TOLD.story.chapters;
		scrollTo(theEnd);
		fakeServer().answer('GET /api/story', { held: storyHeld({ chapters: [onlyTheBeginnings] }) });

		handOverNext(review, { type: 'story' });
		await settled();

		expect(review.parts.beingRead).toBeNull();
	});

	it('is watched for no longer in a chapter the story, told again, has dropped: neither the chapter nor its head', async () => {
		const [, theEnd] = screen.getAllByTestId('story-chapter');
		const itsHead = within(theEnd).getByTestId('part-head');
		const [onlyTheBeginnings] = TOLD.story.chapters;
		fakeServer().answer('GET /api/story', { held: storyHeld({ chapters: [onlyTheBeginnings] }) });

		handOverNext(review, { type: 'story' });
		await settled();

		expect(areasWatching(theEnd)).toEqual([]);
		expect(areasWatching(itsHead)).toEqual([]);
	});
});

describe('the parts of a story, to whoever goes through the page by its parts', () => {
	it('are each a part of the page with a name: the overview, every chapter by its number and title, and what is left out', () => {
		expect(screen.getByRole('region', { name: 'Overview' })).toBe(screen.getByTestId('story-overview'));
		expect(screen.getByRole('region', { name: 'Chapter 2: The end' })).toBe(screen.getAllByTestId('story-chapter')[1]);
		expect(screen.getByRole('region', { name: 'Not in the story' })).toBe(screen.getByTestId('story-left-out'));
	});
});

describe('the head of a part of a story, which holds the keyboard a bar that goes hands on', () => {
	it('says what it is to whoever cannot see it: a group, named as its part is', () => {
		const [, theEnd] = screen.getAllByTestId('story-chapter');

		expect(screen.getByRole('group', { name: 'Chapter 2: The end' })).toBe(within(theEnd).getByTestId('part-head'));
	});
});

describe('a part of a story the reader is taken to', () => {
	it('is brought to the top of what is read at once, from its head', () => {
		const [, theEnd] = screen.getAllByTestId('story-chapter');
		const [, ofTheEnd] = review.story.contents.chapters;
		const toTheEnd = broughtIntoView(theEnd);

		review.parts.goTo(ofTheEnd.part);

		expect(toTheEnd).toHaveBeenCalledWith({ block: 'start', behavior: 'instant' });
	});

	it('is the one being read from then on, whatever is at the top while the page takes them there', () => {
		const [theBeginnings] = screen.getAllByTestId('story-chapter');
		const [, ofTheEnd] = review.story.contents.chapters;

		review.parts.goTo(ofTheEnd.part);
		scrollTo(theBeginnings);

		expect(review.parts.beingRead).toBe(ofTheEnd.part);
	});

	it('is let go of once they have come to rest and scroll on to another', async () => {
		const [theBeginnings] = screen.getAllByTestId('story-chapter');
		const [ofTheBeginnings, ofTheEnd] = review.story.contents.chapters;

		review.parts.goTo(ofTheEnd.part);
		await frames();
		scrollTo(theBeginnings);

		expect(review.parts.beingRead).toBe(ofTheBeginnings.part);
	});

	it('is let go of all the same when the page took them on to a step before it had come to rest', async () => {
		const [theBeginnings] = screen.getAllByTestId('story-chapter');
		const [ofTheBeginnings, ofTheEnd] = review.story.contents.chapters;
		const [toTheStep] = ofTheBeginnings.steps;

		review.parts.goTo(ofTheEnd.part);
		review.sections.scrollTo(toTheStep.section);
		await frames();
		scrollTo(theBeginnings);

		expect(review.parts.beingRead).toBe(ofTheBeginnings.part);
	});

	it('is nowhere for a part the story does not draw: the reader stays where they are', () => {
		review.parts.goTo('a part of another story');

		expect(review.parts.beingRead).toBeNull();
	});
});
