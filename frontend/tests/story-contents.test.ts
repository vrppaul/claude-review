import { describe, expect, it } from 'vitest';
import { contentsOf, LEFT_OUT_PART, OVERVIEW_PART } from '$lib/review/story-contents';
import { stepSectionKey } from '$lib/review/story-pieces';
import { toldChapter, toldStep, toldStory } from './story';

// A story of three chapters. The first tells a.py twice, around b.py; the second tells b.py and a.py;
// the third tells c.py, which no other chapter tells, and a.py once more
const aFirst = toldStep('a.py', 1);
const bFirst = toldStep('b.py', 1);
const aAgain = toldStep('a.py', 5);
const chapters = [
	toldChapter('ch-1', [aFirst, bFirst, aAgain]),
	toldChapter('ch-2', [toldStep('b.py', 5), toldStep('a.py', 7)]),
	toldChapter('ch-3', [toldStep('c.py', 1), toldStep('a.py', 9)])
];
const [ofTheFirst, ofTheSecond, ofTheThird] = contentsOf(toldStory({ chapters })).chapters;

describe('what a story lists of itself', () => {
	it('lists its chapters as they were told, each by its place among them', () => {
		expect([ofTheFirst, ofTheSecond, ofTheThird].map(({ told, place }) => [told.id, place])).toEqual([
			['ch-1', 0],
			['ch-2', 1],
			['ch-3', 2]
		]);
	});

	it('lists each file a chapter tells once, in the order the chapter first tells it', () => {
		expect(ofTheFirst.files.map(({ file }) => file.path)).toEqual(['a.py', 'b.py']);
	});

	it('says a file as the first piece of it in the chapter says it', () => {
		const [a, b] = ofTheFirst.files;

		expect(a.file).toBe(aFirst.piece);
		expect(b.file).toBe(bFirst.piece);
	});

	it("lists a chapter's steps in the order it tells them, each by its section and its place among them", () => {
		expect(ofTheFirst.steps.map(({ told, section, place }) => [told, section, place])).toEqual([
			[aFirst, stepSectionKey(aFirst), 0],
			[bFirst, stepSectionKey(bFirst), 1],
			[aAgain, stepSectionKey(aAgain), 2]
		]);
	});

	it("gives each step its chapter's one listing of its file", () => {
		const [a, b] = ofTheFirst.files;
		const [ofAFirst, ofB, ofAAgain] = ofTheFirst.steps;

		expect(ofAFirst.file).toBe(a);
		expect(ofB.file).toBe(b);
		expect(ofAAgain.file).toBe(a);
	});

	it('says of a file the other chapters that tell it, by their places, in the order the story tells them', () => {
		expect(ofTheFirst.files.map(({ alsoIn }) => alsoIn)).toEqual([[1, 2], [1]]);
		expect(ofTheSecond.files.map(({ alsoIn }) => alsoIn)).toEqual([[0], [0, 2]]);
	});

	it("knows each chapter's part of the page by a key of its own, apart from the overview's and from what is left out", () => {
		const parts = [ofTheFirst, ofTheSecond, ofTheThird].map(({ part }) => part);

		expect(new Set([...parts, OVERVIEW_PART, LEFT_OUT_PART]).size).toBe(5);
	});

	it('says no other chapter of a file one chapter alone tells', () => {
		const [c] = ofTheThird.files;

		expect(c.alsoIn).toEqual([]);
	});
});
