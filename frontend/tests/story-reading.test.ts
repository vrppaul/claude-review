import { beforeEach, describe, it, expect } from 'vitest';
import { threadsNotDrawnIn } from '$lib/review/reading-view';
import type { Review } from '$lib/review/review.svelte';
import { leftOutSectionKey, stepSectionKey } from '$lib/review/story-keys';
import { A_LATER_TAKE, addedLine, diffFile, hunk, removedLine } from './diff';
import { fakeServer } from './fake-server';
import { newComment, storyComment } from './new-comment';
import { openReview } from './review';
import { settled } from './settled';
import { storyHeld, storyResponse, toldChapter, toldStep } from './story';

// A story of two chapters: a.py is told in both, line 1 in the first and line 9 in the second, with
// b.py between them; what no step tells of c.py is left out
const LINE_ONE_OF_A = toldStep('a.py', 1);
const LINE_FIVE_OF_B = toldStep('b.py', 5);
const LINE_NINE_OF_A = toldStep('a.py', 9);
const LEFT_OUT_OF_C = {
	piece: diffFile({
		path: 'c.py',
		hunks: [hunk([removedLine(4, 'gone'), addedLine(4, 'here')], { header: '', old_start: 4, new_start: 4 })]
	}),
	changed_lines: 2
};
const TOLD = storyHeld({
	chapters: [toldChapter('ch-1', [LINE_ONE_OF_A, LINE_FIVE_OF_B]), toldChapter('ch-2', [LINE_NINE_OF_A])],
	left_out: [LEFT_OUT_OF_C]
});
// The same story, saying everything a block of it may say: what to doubt in the overview and in its first
// chapter, a thing left for later, and why its last step is told
const TOLD_SAYING_ALL = storyHeld({
	...TOLD.story,
	overview: {
		...TOLD.story.overview,
		doubt: 'Whether a.py needed both changes.',
		later: [{ text: 'Dragging a file in.', chapter: null }]
	},
	chapters: [
		toldChapter('ch-1', [LINE_ONE_OF_A, LINE_FIVE_OF_B], { doubt: 'Whether b.py belongs here.' }),
		toldChapter('ch-2', [toldStep('a.py', 9, 'The ninth line follows from the first.')])
	]
});
// The same steps told in another order, in one chapter
const TOLD_IN_ANOTHER_ORDER = storyHeld({
	chapters: [toldChapter('ch-1', [LINE_NINE_OF_A, LINE_FIVE_OF_B, LINE_ONE_OF_A])],
	left_out: [LEFT_OUT_OF_C]
});

let review: Review;

describe('a review read as its story', () => {
	beforeEach(() => {
		review = openReview({ story: TOLD });
		review.views.choose('story');
	});

	it('draws a section for every step, in the order the story tells them, then what it leaves out', () => {
		expect(review.views.onScreen.sectionKeys()).toEqual([
			stepSectionKey(LINE_ONE_OF_A),
			stepSectionKey(LINE_FIVE_OF_B),
			stepSectionKey(LINE_NINE_OF_A),
			leftOutSectionKey(LEFT_OUT_OF_C)
		]);
	});

	it('knows every section apart: steps of one file, steps that begin at one line in two files, and what is left out of each', () => {
		const lineOneOfB = toldStep('b.py', 1);
		const leftOutOfA = { piece: toldStep('a.py', 5).piece, changed_lines: 1 };
		const chapters = [toldChapter('ch-1', [LINE_ONE_OF_A, lineOneOfB, LINE_NINE_OF_A])];
		review = openReview({ story: storyHeld({ chapters, left_out: [leftOutOfA, LEFT_OUT_OF_C] }) });
		review.views.choose('story');

		const keys = review.views.onScreen.sectionKeys();

		expect(keys).toHaveLength(5);
		expect(new Set(keys).size).toBe(5);
	});

	it('knows the section of a step by what the step tells, wherever the story puts it once it is told again', async () => {
		const onLineNine = newComment({ file: 'a.py', startLine: 9 }).anchor;
		const asFirstTold = review.views.onScreen.sectionOf(onLineNine);
		fakeServer().answer('GET /api/story', storyResponse({ held: TOLD_IN_ANOTHER_ORDER }));

		await review.story.read();

		expect(review.views.onScreen.sectionKeys()).toEqual([
			stepSectionKey(LINE_NINE_OF_A),
			stepSectionKey(LINE_FIVE_OF_B),
			stepSectionKey(LINE_ONE_OF_A),
			leftOutSectionKey(LEFT_OUT_OF_C)
		]);
		expect(review.views.onScreen.sectionOf(onLineNine)).toBe(asFirstTold);
	});

	it('draws a thread in the piece that shows its line, whichever chapter tells that piece of the file', () => {
		const onLineNine = newComment({ file: 'a.py', startLine: 9 }).anchor;

		expect(review.views.onScreen.sectionOf(onLineNine)).toBe(stepSectionKey(LINE_NINE_OF_A));
	});

	it('draws a thread on a removed line in the piece that shows the line removed', () => {
		const onTheLineRemoved = newComment({ file: 'c.py', side: 'old', startLine: 4 }).anchor;

		expect(review.views.onScreen.sectionOf(onTheLineRemoved)).toBe(leftOutSectionKey(LEFT_OUT_OF_C));
	});

	it('draws no thread on a line no piece shows', () => {
		const onLineFive = newComment({ file: 'a.py', startLine: 5 }).anchor;

		expect(review.views.onScreen.sectionOf(onLineFive)).toBeNull();
	});

	it('takes the reader to a file where the story first tells it', () => {
		expect(review.views.onScreen.sectionOfFile('a.py')).toBe(stepSectionKey(LINE_ONE_OF_A));
	});

	it('takes the reader to a file where the story first tells it, though a later line of it', () => {
		review = openReview({ story: TOLD_IN_ANOTHER_ORDER });
		review.views.choose('story');

		expect(review.views.onScreen.sectionOfFile('a.py')).toBe(stepSectionKey(LINE_NINE_OF_A));
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

	it("walks the threads on the overview's lines first, in the order it says them", () => {
		review = openReview({ story: TOLD_SAYING_ALL });
		review.views.choose('story');
		review.threads.add(newComment({ file: 'b.py', startLine: 5, body: 'in chapter one' }));
		review.threads.add(storyComment({ at: 'overview', text: 'doubt' }, 'on the doubt'));
		review.threads.add(storyComment({ at: 'overview', text: 'task' }, 'on the task'));

		expect(review.views.onScreen.threadsInOrder().map((thread) => thread.body)).toEqual([
			'on the task',
			'on the doubt',
			'in chapter one'
		]);
	});

	it("walks a chapter's own words before its steps, and a step's reason before the lines of its piece", () => {
		review = openReview({ story: TOLD_SAYING_ALL });
		review.views.choose('story');
		review.threads.add(newComment({ file: 'a.py', startLine: 9, body: 'on a line of chapter two' }));
		review.threads.add(storyComment({ at: 'reason', file: 'a.py', first_line: 9 }, 'on the reason in chapter two'));
		review.threads.add(newComment({ file: 'a.py', startLine: 1, body: 'on a line of chapter one' }));
		review.threads.add(storyComment({ at: 'chapter', chapter: 'ch-2', text: 'why' }, 'on why chapter two'));
		review.threads.add(storyComment({ at: 'chapter', chapter: 'ch-1', text: 'doubt' }, 'on the doubt of chapter one'));
		review.threads.add(storyComment({ at: 'item', list: 'later', item: 0 }, 'on what is left for later'));

		expect(review.views.onScreen.threadsInOrder().map((thread) => thread.body)).toEqual([
			'on what is left for later',
			'on the doubt of chapter one',
			'on a line of chapter one',
			'on why chapter two',
			'on the reason in chapter two',
			'on a line of chapter two'
		]);
	});

	it('walks first, and once, the threads on words the story says nowhere: its blocks no longer say them', () => {
		review.threads.add(storyComment({ at: 'overview', text: 'task' }, 'on the task'));
		review.threads.add(storyComment({ at: 'overview', text: 'doubt' }, 'on a doubt the story does not say'));
		review.threads.add(storyComment({ at: 'chapter', chapter: 'gone', text: 'why' }, 'on a chapter it does not tell'));
		review.threads.add(storyComment({ at: 'chapter', chapter: 'ch-1', text: 'doubt' }, 'on a doubt of a chapter'));
		review.threads.add(storyComment({ at: 'reason', file: 'a.py', first_line: 9 }, 'on a reason it does not give'));

		expect(review.views.onScreen.threadsInOrder().map((thread) => thread.body)).toEqual([
			'on a doubt the story does not say',
			'on a chapter it does not tell',
			'on a doubt of a chapter',
			'on a reason it does not give',
			'on the task'
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
			stepSectionKey(LINE_ONE_OF_A),
			stepSectionKey(LINE_FIVE_OF_B),
			stepSectionKey(LINE_NINE_OF_A),
			leftOutSectionKey(LEFT_OUT_OF_C)
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

	it('takes the reader to no file, though a step tells it: its pieces are of the file as it was', () => {
		expect(review.views.onScreen.sectionOfFile('a.py')).toBeNull();
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

	it('is as its story once that is brought on screen for a thread only it draws, and its view is handed over', () => {
		review = openReview({ story: TOLD });

		const handedOver = review.views.showStory();

		expect(review.views.onScreen.name).toBe('story');
		expect(handedOver).toBe(review.views.onScreen);
	});

	it('is still by its files, in the next review opened, though the story was brought on screen in this one', () => {
		review = openReview({ story: TOLD });

		review.views.showStory();

		expect(openReview({ story: TOLD }).views.onScreen.name).toBe('files');
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

	it("walks no thread while no story is held, though a thread hangs on the words of the overview's task", () => {
		review = openReview();
		review.views.choose('story');
		review.threads.add(storyComment({ at: 'overview', text: 'task' }, 'on the task of a story since lost'));

		expect(review.views.onScreen.threadsInOrder()).toEqual([]);
	});
});
