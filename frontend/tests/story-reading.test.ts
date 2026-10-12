import { beforeEach, describe, it, expect } from 'vitest';
import { threadsNotDrawnIn } from '$lib/review/reading-view';
import type { Review } from '$lib/review/review.svelte';
import { leftOutSectionKey, stepSectionKey } from '$lib/review/story-reading';
import { A_LATER_TAKE, addedLine, diffFile, hunk, removedLine } from './diff';
import { newComment } from './new-comment';
import { openReview } from './review';
import { settled } from './settled';
import { storyHeld, toldChapter, toldStep } from './story';

// A story of two chapters: a.py is told in both, line 1 in the first and line 9 in the second, with
// b.py between them; what no step tells of c.py is left out
const LEFT_OUT_OF_C = diffFile({
	path: 'c.py',
	hunks: [hunk([removedLine(4, 'gone'), addedLine(4, 'here')], { header: '', old_start: 4, new_start: 4 })]
});
const TOLD = storyHeld({
	chapters: [
		toldChapter('ch-1', [toldStep('a.py', 1), toldStep('b.py', 5)]),
		toldChapter('ch-2', [toldStep('a.py', 9)])
	],
	left_out: [{ piece: LEFT_OUT_OF_C, changed_lines: 2 }]
});

let review: Review;

describe('a review read as its story', () => {
	beforeEach(() => {
		review = openReview({ story: TOLD });
		review.views.choose('story');
	});

	it('draws a section for every step, in the order the story tells them, then what it leaves out', () => {
		expect(review.views.onScreen.sectionKeys()).toEqual([
			stepSectionKey(0, 0),
			stepSectionKey(0, 1),
			stepSectionKey(1, 0),
			leftOutSectionKey(0)
		]);
	});

	it('draws a thread in the piece that shows its line, whichever chapter tells that piece of the file', () => {
		const onLineNine = newComment({ file: 'a.py', startLine: 9 }).anchor;

		expect(review.views.onScreen.sectionOf(onLineNine)).toBe(stepSectionKey(1, 0));
	});

	it('draws a thread on a removed line in the piece that shows the line removed', () => {
		const onTheLineRemoved = newComment({ file: 'c.py', side: 'old', startLine: 4 }).anchor;

		expect(review.views.onScreen.sectionOf(onTheLineRemoved)).toBe(leftOutSectionKey(0));
	});

	it('draws no thread on a line no piece shows', () => {
		const onLineFive = newComment({ file: 'a.py', startLine: 5 }).anchor;

		expect(review.views.onScreen.sectionOf(onLineFive)).toBeNull();
	});

	it('takes the reader to a file where the story first tells it', () => {
		expect(review.views.onScreen.sectionOfFile('a.py')).toBe(stepSectionKey(0, 0));
	});

	it('draws nothing of a file it neither tells nor leaves out', () => {
		expect(review.views.onScreen.sectionOfFile('housekeeping.lock')).toBeNull();
	});

	it('walks the threads down the story, not down the files, and only those it draws', () => {
		review.threads.add(newComment({ file: 'c.py', startLine: 4, body: 'on what was left out' }));
		review.threads.add(newComment({ file: 'a.py', startLine: 9, body: 'in chapter two' }));
		review.threads.add(newComment({ file: 'a.py', startLine: 5, body: 'on a line the story does not show' }));
		review.threads.add(newComment({ file: 'b.py', startLine: 5, body: 'in chapter one' }));

		expect(review.views.onScreen.threadsInOrder().map((thread) => thread.body)).toEqual([
			'in chapter one',
			'in chapter two',
			'on what was left out'
		]);
	});

	it('takes a removed line before the line that replaced it, as a piece draws them', () => {
		review.threads.add(newComment({ file: 'c.py', startLine: 4, body: 'on the line added' }));
		review.threads.add(newComment({ file: 'c.py', side: 'old', startLine: 4, body: 'on the line removed' }));

		expect(review.views.onScreen.threadsInOrder().map((thread) => thread.body)).toEqual([
			'on the line removed',
			'on the line added'
		]);
	});

	it('says which threads it draws none of', () => {
		review.threads.add(newComment({ file: 'a.py', startLine: 9, body: 'in chapter two' }));
		review.threads.add(newComment({ file: 'a.py', startLine: 5, body: 'on a line no piece shows' }));
		review.threads.add(newComment({ file: 'housekeeping.lock', startLine: 1, body: 'on a file it does not tell' }));

		const notDrawn = threadsNotDrawnIn(review.views.onScreen, review.threads);

		expect(notDrawn.map((thread) => thread.body)).toEqual(['on a line no piece shows', 'on a file it does not tell']);
	});
});

describe('a story told of another take of the change than the page reads', () => {
	beforeEach(() => {
		review = openReview({ story: TOLD, diff: { take: A_LATER_TAKE } });
		review.views.choose('story');
	});

	it('is still read piece by piece, as it was told', () => {
		expect(review.views.onScreen.sectionKeys()).toEqual([
			stepSectionKey(0, 0),
			stepSectionKey(0, 1),
			stepSectionKey(1, 0),
			leftOutSectionKey(0)
		]);
	});

	it('draws no thread, though a piece shows a line of the number the thread hangs on: it is numbered as that take', () => {
		const onLineNine = newComment({ file: 'a.py', startLine: 9 }).anchor;

		expect(review.views.onScreen.sectionOf(onLineNine)).toBeNull();
	});

	it('walks no thread', () => {
		review.threads.add(newComment({ file: 'a.py', startLine: 9, body: 'in chapter two' }));

		expect(review.views.onScreen.threadsInOrder()).toEqual([]);
	});
});

describe('which way a review is read', () => {
	it('is by its files until the reader chooses its story', () => {
		review = openReview({ story: TOLD });

		expect(review.views.onScreen.name).toBe('files');
	});

	it('is as its story once the reader chooses that', () => {
		review = openReview({ story: TOLD });

		review.views.choose('story');

		expect(review.views.onScreen.name).toBe('story');
	});

	it('is as the reader chose last, in the next review opened on this page', () => {
		openReview({ story: TOLD }).views.choose('story');

		expect(openReview({ story: TOLD }).views.onScreen.name).toBe('story');
	});

	it('is by its files where no story can be told of it, though the reader chose the story last', () => {
		openReview({ story: TOLD }).views.choose('story');

		review = openReview({ facts: { takes_a_story: false } });

		expect(review.views.onScreen.name).toBe('files');
	});

	it('is by its files once they are brought on screen for something only they show', () => {
		review = openReview({ story: TOLD });
		review.views.choose('story');

		review.views.showFiles();

		expect(review.views.onScreen.name).toBe('files');
	});

	it('is still as the reader chose, in the next review opened, though the files were brought on screen in this one', () => {
		review = openReview({ story: TOLD });
		review.views.choose('story');

		review.views.showFiles();

		expect(openReview({ story: TOLD }).views.onScreen.name).toBe('story');
	});

	it('is still as the reader chose, in the next review, though one that takes no story took them to a file meanwhile', async () => {
		openReview({ story: TOLD }).views.choose('story');
		review = openReview({ facts: { takes_a_story: false } });

		review.navigator.showFile('not-in-the-diff.py');
		await settled();

		expect(openReview({ story: TOLD }).views.onScreen.name).toBe('story');
	});

	it('draws no section while no story is held, though the story is the view chosen', () => {
		review = openReview();
		review.views.choose('story');

		expect(review.views.onScreen.sectionKeys()).toEqual([]);
	});
});
