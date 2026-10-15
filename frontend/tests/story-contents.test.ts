import { describe, expect, it } from 'vitest';
import { contentsOf, tellsFirst } from '$lib/review/story-contents';
import { LEFT_OUT_PART, OVERVIEW_PART } from '$lib/review/story-keys';
import { piecesOf } from '$lib/review/story-pieces';
import { addedLine, diffFile, hunk, removedLine } from './diff';
import { stepWithoutCode, toldChapter, toldStep, toldStory } from './story';

// A story of three chapters. The first tells a.py twice, around b.py; the second tells b.py and a.py;
// the third tells c.py, which no other chapter tells, and a.py once more. Every step tells one line
// its file gained. No step tells two more changes of a.py: a line it gained, and one it lost
const aFirst = toldStep('a.py', 1);
const bFirst = toldStep('b.py', 1);
const aAgain = toldStep('a.py', 5);
const chapters = [
	toldChapter('ch-1', [aFirst, bFirst, aAgain]),
	toldChapter('ch-2', [toldStep('b.py', 5), toldStep('a.py', 7)]),
	toldChapter('ch-3', [toldStep('c.py', 1), toldStep('a.py', 9)])
];
const leftOutOfA = {
	piece: diffFile({ path: 'a.py', hunks: [hunk([addedLine(20, 'gained'), removedLine(21, 'lost')])] }),
	changed_lines: 2
};
const story = toldStory({ chapters, left_out: [leftOutOfA] });
const contents = contentsOf(story);
const [ofTheFirst, ofTheSecond, ofTheThird] = contents.chapters;

describe('what a story lists of itself', () => {
	it('lists its chapters as they were told, each by its place among them', () => {
		expect([ofTheFirst, ofTheSecond, ofTheThird].map(({ told, place }) => [told.id, place])).toEqual([
			['ch-1', 0],
			['ch-2', 1],
			['ch-3', 2]
		]);
	});

	it('lists each file a chapter tells once, in the order the chapter first tells it', () => {
		expect(ofTheFirst.files.map(({ firstPiece }) => firstPiece.path)).toEqual(['a.py', 'b.py']);
	});

	it('says a file as the first piece of it in the chapter says it', () => {
		const [a, b] = ofTheFirst.files;

		expect(a.firstPiece).toBe(aFirst.now?.piece);
		expect(b.firstPiece).toBe(bFirst.now?.piece);
	});

	it("lists a chapter's steps in the order it tells them, each by its section and its place among them", () => {
		expect(ofTheFirst.steps.map(({ told, section, place }) => [told, section, place])).toEqual([
			[aFirst, 'step:a.py:1', 0],
			[bFirst, 'step:b.py:1', 1],
			[aAgain, 'step:a.py:5', 2]
		]);
	});

	it("gives each step its piece and its chapter's one listing of its file", () => {
		const [a, b] = ofTheFirst.files;
		const [ofAFirst, ofB, ofAAgain] = ofTheFirst.steps;

		expect(ofAFirst.shown).toEqual({ piece: aFirst.now?.piece, lines: aFirst.now?.lines, fileListed: a });
		expect(ofB.shown).toEqual({ piece: bFirst.now?.piece, lines: bFirst.now?.lines, fileListed: b });
		expect(ofAAgain.shown).toEqual({ piece: aAgain.now?.piece, lines: aAgain.now?.lines, fileListed: a });
	});

	it('lists no file of a chapter where no step of it shows code of it, and shows nothing of such a step', () => {
		const ofB = toldStep('b.py', 1);
		const withoutCode = toldChapter('ch-1', [stepWithoutCode('a.py', 1), ofB]);
		const [listed] = contentsOf(
			toldStory({ chapters: [withoutCode, toldChapter('ch-2', [toldStep('a.py', 5)])] })
		).chapters;
		const [b] = listed.files;

		expect(listed.files.map(({ firstPiece, alsoIn }) => [firstPiece.path, alsoIn])).toEqual([['b.py', []]]);
		expect(listed.steps.map(({ shown }) => shown)).toEqual([
			null,
			{ piece: ofB.now?.piece, lines: ofB.now?.lines, fileListed: b }
		]);
	});

	it('says no chapter tells a file where its only step of the file shows no code of it', () => {
		const withoutCode = toldChapter('ch-1', [stepWithoutCode('a.py', 1), toldStep('b.py', 1)]);
		const [, listed] = contentsOf(
			toldStory({ chapters: [withoutCode, toldChapter('ch-2', [toldStep('a.py', 5)])] })
		).chapters;

		expect(listed.files.map(({ firstPiece, alsoIn }) => [firstPiece.path, alsoIn])).toEqual([['a.py', []]]);
	});

	it('says of a file the other chapters that tell it, by their places, in the order the story tells them', () => {
		expect(ofTheFirst.files.map(({ alsoIn }) => alsoIn)).toEqual([[1, 2], [1]]);
		expect(ofTheSecond.files.map(({ alsoIn }) => alsoIn)).toEqual([[0], [0, 2]]);
	});

	it('says whether a chapter is the first to tell a file', () => {
		expect(ofTheFirst.files.map((listed) => tellsFirst(ofTheFirst, listed))).toEqual([true, true]);
		expect(ofTheSecond.files.map((listed) => tellsFirst(ofTheSecond, listed))).toEqual([false, false]);
		expect(ofTheThird.files.map((listed) => tellsFirst(ofTheThird, listed))).toEqual([true, false]);
	});

	it('lists what it leaves out, file by file, each with what its section is known by', () => {
		expect(contents.leftOut).toEqual([{ told: leftOutOfA, section: 'left-out:a.py' }]);
	});

	it('says where a reader who picks a file is taken: to the first step of the chapter that tells it', () => {
		expect(ofTheFirst.files.map(({ opensAt }) => opensAt)).toEqual(['step:a.py:1', 'step:b.py:1']);
	});

	it('finds a step by what its section is known by', () => {
		const [, , ofAAgain] = ofTheFirst.steps;

		expect(contents.stepAt('step:a.py:5')).toBe(ofAAgain);
	});

	it('finds no step by a key no step has', () => {
		expect(contents.stepAt('left-out:a.py')).toBeNull();
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

describe('the pieces of what a story lists', () => {
	const pieces = piecesOf(contents);

	it('are known by the sections the story lists them under, in the order it lists them: every step, then what it leaves out', () => {
		expect(pieces.keys).toEqual([
			'step:a.py:1',
			'step:b.py:1',
			'step:a.py:5',
			'step:b.py:5',
			'step:a.py:7',
			'step:c.py:1',
			'step:a.py:9',
			'left-out:a.py'
		]);
	});

	it('say how much of a file the whole story changes: every piece of it, in whichever chapter, and what no step tells', () => {
		// a.py gained a line in each of four steps and one that no step tells, and lost one no step tells
		expect(pieces.changeOf('a.py')).toEqual({ additions: 5, deletions: 1 });
		expect(pieces.changeOf('b.py')).toEqual({ additions: 2, deletions: 0 });
	});

	it('say a file the story draws nothing of changes by nothing', () => {
		expect(pieces.changeOf('z.py')).toEqual({ additions: 0, deletions: 0 });
	});
});
