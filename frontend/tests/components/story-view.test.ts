import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import { flushSync } from 'svelte';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import type { Review } from '$lib/review/review.svelte';
import type { StoryHeld, ToldChapter, ToldStep } from '$lib/types';
import { A_LATER_TAKE, addedLine, diffFile, diffResponse, hunk, sinceRound } from '../diff';
import { said } from '../elements';
import { fakeServer, keepingSettings, SERVER_ERROR } from '../fake-server';
import { newComment } from '../new-comment';
import { handOverNext } from '../pushes';
import { openReview } from '../review';
import { areasWatching, scriptTheScroll, scrollTo } from '../scripted-scroll';
import { settled } from '../settled';
import {
	ASKED,
	chapterChanged,
	changedStep,
	codeMovedOn,
	stepWithoutCode,
	storyHeld,
	TAKEN,
	toldChapter,
	toldStep,
	toldStepOfLines
} from '../story';

// The change under review: a.py gained lines 1, 5 and 9, b.py gained a line, and so did a lock file
const files = [
	diffFile({ path: 'a.py', hunks: [hunk([addedLine(1, 'one'), addedLine(5, 'five'), addedLine(9, 'nine')])] }),
	diffFile({ path: 'b.py', hunks: [hunk([addedLine(5, 'in b.py')])] }),
	diffFile({ path: 'uv.lock', hunks: [hunk([addedLine(1, 'locked')])] })
];
// The story told of it: line 1 of a.py and b.py in a first chapter, line 9 of a.py in a second; line 5 of
// a.py is told by no step and left out, and the lock file is housekeeping
const LEFT_OUT_OF_A = diffFile({
	path: 'a.py',
	hunks: [hunk([addedLine(5, 'line 5 of a.py')], { header: '', old_start: 5, new_start: 5 })]
});
const TOLD = storyHeld({
	title: 'Lines for a.py and b.py',
	chapters: [
		toldChapter('ch-1', [toldStep('a.py', 1, 'The first line comes first.'), toldStep('b.py', 5)], {
			title: 'The beginnings',
			doubt: 'Whether b.py needs its line at all.'
		}),
		toldChapter('ch-2', [toldStep('a.py', 9, 'The last line closes the file.')], { title: 'The end' })
	],
	left_out: [{ piece: LEFT_OUT_OF_A, changed_lines: 1 }],
	housekeeping: ['uv.lock']
});
// What a story told from commits says of itself, by how it begins
const NOT_THE_AGENTS_OWN_CHANGE = /^The agent did not make this change\./;

let review: Review;

/** The pieces of files the story draws, in the order it draws them. */
function pieces(): HTMLElement[] {
	return screen.getAllByTestId('story-piece');
}

describe('a review a story can be told of', () => {
	beforeEach(() => {
		review = openReview({ files, story: TOLD });
	});

	it('is read by its files until the reader chooses its story, which the header offers beside them', () => {
		render(ReviewScreen, { props: { review } });

		expect(screen.getByTestId('diff-view')).toBeTruthy();
		expect(screen.getByTestId('read-as-files').getAttribute('aria-pressed')).toBe('true');
		expect(screen.getByTestId('read-as-story').getAttribute('aria-pressed')).toBe('false');
	});

	it('is read as its story once the reader chooses it, and by its files again when they choose those', async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });

		await user.click(screen.getByTestId('read-as-story'));
		expect(screen.getByTestId('story-view')).toBeTruthy();
		expect(screen.queryByTestId('diff-view')).toBeNull();

		await user.click(screen.getByTestId('read-as-files'));
		expect(screen.getByTestId('diff-view')).toBeTruthy();
		expect(screen.queryByTestId('story-view')).toBeNull();
	});

	it('says in the header which way it is read now', async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });

		await user.click(screen.getByTestId('read-as-story'));

		expect(screen.getByTestId('read-as-story').getAttribute('aria-pressed')).toBe('true');
		expect(screen.getByTestId('read-as-files').getAttribute('aria-pressed')).toBe('false');
	});
});

describe('a review read as its story', () => {
	beforeEach(() => {
		review = openReview({ files, story: TOLD });
		review.views.choose('story');
	});

	it('says what the change is called, which round the story was told in, and that its code is current', () => {
		render(ReviewScreen, { props: { review } });

		expect(screen.getByTestId('story-title').textContent).toBe('Lines for a.py and b.py');
		expect(said(screen.getByTestId('story-round'))).toBe('Round 1 current');
	});

	it('says the round it was told in where that was a later one', () => {
		review = openReview({ files, story: storyHeld(TOLD.story, { round: 3 }) });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		expect(said(screen.getByTestId('story-round'))).toBe('Round 3 current');
	});

	it('says the round it was told in, and the round a later one moved the code on in', () => {
		review = openReview({ files, story: storyHeld(TOLD.story, { moved_on: codeMovedOn() }) });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		expect(said(screen.getByTestId('story-round'))).toBe('Round 1 the code moved on in round 2');
	});

	it('says what was asked and what was done, and nothing to doubt where the agent named nothing', () => {
		render(ReviewScreen, { props: { review } });

		const overview = screen.getByTestId('story-overview');

		expect(within(overview).getByText('What was asked.')).toBeTruthy();
		expect(within(overview).getByText('What was done.')).toBeTruthy();
		expect(screen.queryByTestId('overview-doubt')).toBeNull();
	});

	it('says what to doubt of the whole change, where the agent said', () => {
		const overview = { ...TOLD.story.overview, doubt: 'Whether a.py is the place for them.' };
		review = openReview({ files, story: storyHeld({ ...TOLD.story, overview }) });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		const doubt = within(screen.getByTestId('overview-doubt')).getByTestId('block-words');
		expect(doubt.textContent).toBe('Whether a.py is the place for them.');
	});

	it('tells every chapter in a row, each by its name', () => {
		render(ReviewScreen, { props: { review } });

		expect(screen.getAllByTestId('chapter-title').map((title) => title.textContent)).toEqual([
			'The beginnings',
			'The end'
		]);
	});

	it('says of each chapter why its changes belong together, and how many files it tells in how many steps', () => {
		render(ReviewScreen, { props: { review } });

		const [beginnings, end] = screen.getAllByTestId('story-chapter');

		expect(within(beginnings).getByTestId('chapter-why').textContent).toBe('Why the changes of ch-1 belong together.');
		expect(within(beginnings).getByText('2 files · 2 steps')).toBeTruthy();
		expect(within(end).getByTestId('chapter-why').textContent).toBe('Why the changes of ch-2 belong together.');
		expect(within(end).getByText('1 file · 1 step')).toBeTruthy();
	});

	it('counts a file a chapter tells in two steps once', () => {
		const chapters = [toldChapter('ch-1', [toldStep('a.py', 1), toldStep('b.py', 5), toldStep('a.py', 9)])];
		review = openReview({ files, story: storyHeld({ chapters }) });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		expect(within(screen.getByTestId('story-chapter')).getByText('2 files · 3 steps')).toBeTruthy();
	});

	it('says in the head of a piece the other chapter that tells its file, and nothing of a file told in one', () => {
		render(ReviewScreen, { props: { review } });

		// a.py is told in both chapters, b.py in the first alone; what no step tells of a.py is in no chapter
		const [ofAInTheFirst, ofB, ofAInTheSecond, leftOutOfA] = pieces();

		expect(within(ofAInTheFirst).getByTestId('also-in').textContent).toBe('also in chapter 2');
		expect(within(ofAInTheSecond).getByTestId('also-in').textContent).toBe('also in chapter 1');
		expect(within(ofB).queryByTestId('also-in')).toBeNull();
		expect(within(leftOutOfA).queryByTestId('also-in')).toBeNull();
	});

	it('names every other chapter that tells the file of a piece, where they are several', () => {
		const chapters = [
			toldChapter('ch-1', [toldStep('a.py', 1)]),
			toldChapter('ch-2', [toldStep('a.py', 5)]),
			toldChapter('ch-3', [toldStep('a.py', 9)])
		];
		review = openReview({ files, story: storyHeld({ chapters }) });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		const [, inTheSecond] = pieces();

		expect(within(inTheSecond).getByTestId('also-in').textContent).toBe('also in chapters 1, 3');
	});

	it('says where to doubt a chapter, where the agent said', () => {
		render(ReviewScreen, { props: { review } });

		expect(screen.getByTestId('chapter-doubt').textContent).toContain('Whether b.py needs its line at all.');
	});

	it('numbers each step by its chapter and its place in it, and says its reason where it has one', () => {
		render(ReviewScreen, { props: { review } });

		const [first, second] = pieces();

		expect(screen.getAllByTestId('step-number').map((number) => number.textContent.trim())).toEqual([
			'1.1',
			'1.2',
			'2.1'
		]);
		expect(within(first).getByTestId('step-reason').textContent).toBe('The first line comes first.');
		expect(within(second).queryByTestId('step-reason')).toBeNull();
	});

	it('takes the reader to a step from its number and reason down: they head the section gone to', async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });
		const [, second, third] = pieces();
		// Its own, given to it here: a spy on the method would be the one every element shares
		const broughtIntoView = vi.fn();
		third.scrollIntoView = broughtIntoView;

		within(second).getByTestId('line-gutter').focus();
		await user.keyboard(']');

		expect(broughtIntoView).toHaveBeenCalled();
		expect(within(third).getByRole('heading', { level: 3, name: 'Step 2.1' })).toBeTruthy();
		expect(within(third).getByTestId('step-reason').textContent).toBe('The last line closes the file.');
	});

	it('heads each chapter with its number and its name', () => {
		render(ReviewScreen, { props: { review } });

		expect(screen.getByRole('heading', { level: 2, name: '1 The beginnings' })).toBeTruthy();
		expect(screen.getByRole('heading', { level: 2, name: '2 The end' })).toBeTruthy();
	});

	it('heads each step once, by its number, so two steps of one file are told apart', () => {
		const chapters = [toldChapter('ch-1', [toldStep('a.py', 1), toldStepOfLines('a.py', 5, 9)])];
		review = openReview({ files, story: storyHeld({ chapters }) });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		const [first, second] = pieces();

		expect(within(first).getByRole('heading')).toBe(within(first).getByRole('heading', { level: 3, name: 'Step 1.1' }));
		expect(within(second).getByRole('heading')).toBe(
			within(second).getByRole('heading', { level: 3, name: 'Step 1.2' })
		);
	});

	it('heads what no step tells of a file with what became of the file and its name, under what says it is not in the story', () => {
		render(ReviewScreen, { props: { review } });

		const leftOut = screen.getByTestId('story-left-out');

		expect(within(leftOut).getByRole('heading', { level: 2, name: 'Not in the story' })).toBeTruthy();
		expect(within(leftOut).getByRole('heading', { level: 3, name: 'modified a.py' })).toBeTruthy();
	});

	it('says the change in short under a heading of its own, as what is asked of it and what is said', () => {
		const overview = { ...TOLD.story.overview, doubt: 'Whether a.py is the place for them.' };
		review = openReview({ files, story: storyHeld({ ...TOLD.story, overview }) });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		const inShort = screen.getByTestId('story-overview');

		expect(within(inShort).getByRole('heading', { level: 2, name: 'The change in short' })).toBeTruthy();
		expect(
			within(inShort)
				.getAllByRole('term')
				.map((term) => term.textContent)
		).toEqual(['Task', 'Done', 'Doubt']);
		expect(
			within(inShort)
				.getAllByRole('definition')
				.map((said) => said.textContent)
		).toEqual(['What was asked.', 'What was done.', 'Whether a.py is the place for them.']);
	});

	it('says which lines of its file each step tells: one by its number, several from the first to the last', () => {
		const chapters = [toldChapter('ch-1', [toldStep('a.py', 1), toldStepOfLines('a.py', 5, 9)])];
		review = openReview({ files, story: storyHeld({ chapters }) });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		expect(screen.getAllByTestId('step-lines').map((lines) => lines.textContent)).toEqual(['1', '5–9']);
	});

	it("says the lines a step's code stands at now, where a round moved it from those it was told on", () => {
		const told = toldStep('a.py', 1);
		const movedDown = { ...told, now: { ...toldStepOfLines('a.py', 3, 4).now, changed_since_told: false } };
		review = openReview({ files, story: storyHeld({ chapters: [toldChapter('ch-1', [movedDown])] }) });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		expect(screen.getAllByTestId('step-lines').map((lines) => lines.textContent)).toEqual(['3–4']);
	});

	it('says of each piece what became of its file, and how many lines the piece adds and removes', () => {
		const made = diffFile({ path: 'new.py', status: 'added', hunks: [hunk([addedLine(1, 'x'), addedLine(2, 'y')])] });
		const ofTheFileMade = {
			file: 'new.py',
			lines: { first: 1, last: 2 },
			reason: null,
			now: { lines: { first: 1, last: 2 }, piece: made, changed_since_told: false }
		};
		const chapters = [toldChapter('ch-1', [toldStep('a.py', 1), ofTheFileMade])];
		review = openReview({ files, story: storyHeld({ chapters }) });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		const [ofTheChanged, ofTheMade] = screen.getAllByTestId('story-piece-header');

		expect(within(ofTheChanged).getByText('M')).toBeTruthy();
		expect(within(ofTheChanged).getByText('+1')).toBeTruthy();
		expect(within(ofTheMade).getByText('A')).toBeTruthy();
		expect(within(ofTheMade).getByText('+2')).toBeTruthy();
		expect(within(ofTheMade).getByText('−0')).toBeTruthy();
	});

	it('says what became of the file of each piece in a word too, to whoever cannot see the letter', () => {
		const made = diffFile({ path: 'new.py', status: 'added', hunks: [hunk([addedLine(1, 'x')])] });
		const ofTheFileMade = {
			file: 'new.py',
			lines: { first: 1, last: 1 },
			reason: null,
			now: { lines: { first: 1, last: 1 }, piece: made, changed_since_told: false }
		};
		const chapters = [toldChapter('ch-1', [toldStep('a.py', 1), ofTheFileMade])];
		review = openReview({ files, story: storyHeld({ chapters }) });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		const [ofTheChanged, ofTheMade] = screen.getAllByTestId('story-piece-header');

		expect(within(ofTheChanged).getByText('modified')).toBeTruthy();
		expect(within(ofTheMade).getByText('added')).toBeTruthy();
	});

	it('shows in each step the piece of its file the step tells, and no more of the file', () => {
		render(ReviewScreen, { props: { review } });

		const [firstStep] = pieces();

		expect(firstStep.dataset.path).toBe('a.py');
		expect(firstStep.textContent).toContain('line 1 of a.py');
		expect(firstStep.textContent).not.toContain('line 9 of a.py');
	});

	it('sets the lines of every piece across two columns where the reader reads changes so', async () => {
		keepingSettings(fakeServer());
		await review.settings.change({ diff_layout: 'split' });
		render(ReviewScreen, { props: { review } });

		expect(screen.getAllByTestId('split-view')).toHaveLength(pieces().length);
	});

	it('shows what no step tells all the same, apart from the story', () => {
		render(ReviewScreen, { props: { review } });

		const leftOut = screen.getByTestId('story-left-out');

		expect(leftOut.textContent).toContain('line 5 of a.py');
		expect(within(leftOut).getByText('1 changed line')).toBeTruthy();
	});

	it('shows a file it leaves out whole as that file says of itself, with no count of lines it has none of', () => {
		const picture = diffFile({ path: 'docs/logo.png', status: 'added', unshown: 'binary' });
		review = openReview({ files, story: storyHeld({ left_out: [{ piece: picture, changed_lines: 0 }] }) });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		const leftOut = screen.getByTestId('story-left-out');

		expect(leftOut.textContent).toContain('Binary file');
		expect(leftOut.textContent).not.toContain('changed line');
	});

	it('names the one file the agent called housekeeping, and draws none of it', () => {
		render(ReviewScreen, { props: { review } });

		const housekeeping = screen.getByTestId('story-housekeeping');

		expect(within(housekeeping).getByText('Housekeeping · 1 file')).toBeTruthy();
		expect(housekeeping.textContent).toContain('uv.lock');
		expect(pieces().map((piece) => piece.dataset.path)).toEqual(['a.py', 'b.py', 'a.py', 'a.py']);
	});

	it('says how many files are housekeeping where they are several', () => {
		review = openReview({ files, story: storyHeld({ housekeeping: ['uv.lock', 'pnpm-lock.yaml'] }) });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		expect(within(screen.getByTestId('story-housekeeping')).getByText('Housekeeping · 2 files')).toBeTruthy();
	});

	it('says nothing of what it leaves out, nor of housekeeping, where every change is told by a step', () => {
		review = openReview({ files, story: storyHeld() });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		expect(screen.queryByTestId('story-left-out')).toBeNull();
		expect(screen.queryByTestId('story-housekeeping')).toBeNull();
	});

	it('draws a thread under its line once, in the piece that shows the line', () => {
		review.threads.add(newComment({ file: 'a.py', startLine: 9, body: 'about the last line' }));
		render(ReviewScreen, { props: { review } });

		const [, , ofLineNine] = pieces();

		expect(screen.getAllByTestId('comment-thread')).toHaveLength(1);
		expect(within(ofLineNine).getByTestId('comment-thread').textContent).toContain('about the last line');
	});

	it('takes a comment on a line of a step, which hangs on that line of the file', async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });

		await user.click(within(pieces()[1]).getByRole('button', { name: 'Comment on line 5' }));
		await user.type(screen.getByTestId('comment-input'), 'why this line');
		await user.click(screen.getByTestId('save-comment'));

		expect(review.threads.all.map((thread) => thread.anchor)).toMatchObject([
			{ file: 'b.py', side: 'new', start_line: 5 }
		]);
	});

	it('says how many comments are on lines it does not show', () => {
		review.threads.add(newComment({ file: 'uv.lock', startLine: 1, body: 'about the lock file' }));
		render(ReviewScreen, { props: { review } });

		expect(screen.getByTestId('threads-off-the-story').textContent).toContain(
			'1 comment is on lines the story does not show.'
		);
	});

	it('offers the way to them by where it leads: Show in Files', () => {
		review.threads.add(newComment({ file: 'uv.lock', startLine: 1, body: 'about the lock file' }));
		render(ReviewScreen, { props: { review } });

		expect(screen.getByTestId('show-in-files').textContent.trim()).toBe('Show in Files');
	});

	it('takes the reader to the first of them in the files, with the keyboard on it', async () => {
		const user = userEvent.setup();
		review.threads.add(newComment({ file: 'a.py', startLine: 9, body: 'on a line the story shows' }));
		review.threads.add(newComment({ file: 'uv.lock', startLine: 1, body: 'about the lock file' }));
		render(ReviewScreen, { props: { review } });

		await user.click(screen.getByTestId('show-in-files'));
		await settled();

		// The files draw both threads, down the diff: the one on a.py, then the one the story did not draw
		const [, notDrawnByTheStory] = within(screen.getByTestId('diff-view')).getAllByTestId('comment-thread');
		expect(notDrawnByTheStory.textContent).toContain('about the lock file');
		expect(document.activeElement).toBe(notDrawnByTheStory);
	});

	it('asks for no diff to go to a thread in the files, which already read the whole review', async () => {
		const diffs = fakeServer().hold('GET /api/diff');
		review.threads.add(newComment({ file: 'uv.lock', startLine: 1, body: 'about the lock file' }));
		const [thread] = review.threads.all;
		render(ReviewScreen, { props: { review } });

		review.navigator.reveal(thread);
		await settled();

		expect(diffs.requests).toEqual([]);
	});

	it('takes the reader to a thread it does not draw though the files are read against a narrower base, which is put back whole for it', async () => {
		// Since round one, the first file alone; the diff asked for after that is the review's own
		fakeServer().answer('GET /api/diff', diffResponse({ files: files.slice(0, 1), base: sinceRound(1) }));
		await review.diff.setBase('round:1');
		fakeServer().answer('GET /api/diff', diffResponse({ files }));
		review.threads.add(newComment({ file: 'uv.lock', startLine: 1, body: 'about the lock file' }));
		const [thread] = review.threads.all;
		render(ReviewScreen, { props: { review } });

		review.navigator.reveal(thread);
		await settled();

		expect(review.diff.narrowed).toBe(false);
		expect(document.activeElement).toBe(screen.getByTestId('comment-thread'));
	});

	it("leaves the files' narrower base as it is when the reader is taken to a file the story draws", async () => {
		fakeServer().answer('GET /api/diff', diffResponse({ files: files.slice(0, 1), base: sinceRound(1) }));
		await review.diff.setBase('round:1');
		render(ReviewScreen, { props: { review } });

		review.navigator.showFile('b.py');
		await settled();

		expect(review.views.onScreen.name).toBe('story');
		expect(review.diff.narrowed).toBe(true);
	});

	it('brings the files on screen when the reader asks to see what changed since the last retake', async () => {
		const user = userEvent.setup();
		fakeServer().answer('GET /api/diff', diffResponse({ files: files.slice(0, 1), base: sinceRound(1) }));
		review.noteRetake({ followed: 0, outdated: 0 }, { since_round: 1, base_key: 'round:1', paths: ['a.py'] });
		render(ReviewScreen, { props: { review } });

		await user.click(screen.getByTestId('show-what-changed'));
		await settled();

		expect(screen.getByTestId('diff-view')).toBeTruthy();
		expect(review.diff.narrowed).toBe(true);
	});

	it('says nothing of comments while every one is on a line it shows', () => {
		review.threads.add(newComment({ file: 'a.py', startLine: 1 }));
		render(ReviewScreen, { props: { review } });

		expect(screen.queryByTestId('threads-off-the-story')).toBeNull();
	});

	it('goes to a thread it does not draw in the files, which come on screen for it', async () => {
		review.threads.add(newComment({ file: 'uv.lock', startLine: 1, body: 'about the lock file' }));
		const [thread] = review.threads.all;
		render(ReviewScreen, { props: { review } });

		review.navigator.reveal(thread);
		await settled();

		expect(review.views.onScreen.name).toBe('files');
		expect(document.activeElement).toBe(screen.getByTestId('comment-thread'));
	});

	it('leaves how the reader chose to read as they chose it, when it takes them to the files for a thread', async () => {
		review.threads.add(newComment({ file: 'uv.lock', startLine: 1, body: 'about the lock file' }));
		const [thread] = review.threads.all;
		render(ReviewScreen, { props: { review } });

		review.navigator.reveal(thread);
		await settled();

		expect(openReview({ files, story: TOLD }).views.onScreen.name).toBe('story');
	});

	it('shows a file the agent names in the files, where the story draws none of it, once they are drawn', async () => {
		render(ReviewScreen, { props: { review } });

		handOverNext(review, { type: 'show', file: 'uv.lock' });
		await settled();

		expect(review.views.onScreen.name).toBe('files');
		expect(review.sections.fileInView).toBe('uv.lock');
	});

	it('shows a file the agent names where the story first tells it, and stays in the story', async () => {
		render(ReviewScreen, { props: { review } });

		handOverNext(review, { type: 'show', file: 'b.py' });
		await settled();

		expect(review.views.onScreen.name).toBe('story');
		expect(review.sections.fileInView).toBe('b.py');
	});

	it('says nothing of a narrower base: that is how the files are read, and a story is of the whole change', async () => {
		fakeServer().answer('GET /api/diff', diffResponse({ files, base: sinceRound(1) }));
		await review.diff.setBase('round:1');
		render(ReviewScreen, { props: { review } });

		expect(screen.queryByTestId('narrowed-to')).toBeNull();
	});

	it('steps through the threads down the story, whatever order the files stand in', async () => {
		const user = userEvent.setup();
		review.threads.add(newComment({ file: 'a.py', startLine: 9, body: 'in chapter two' }));
		review.threads.add(newComment({ file: 'b.py', startLine: 5, body: 'in chapter one' }));
		render(ReviewScreen, { props: { review } });

		// b.py is told in chapter one, by the second piece; line 9 of a.py in chapter two, by the third
		const inChapterOne = within(pieces()[1]).getByTestId('comment-thread');
		const inChapterTwo = within(pieces()[2]).getByTestId('comment-thread');

		await user.keyboard('n');
		expect(document.activeElement).toBe(inChapterOne);

		await user.keyboard('n');
		expect(document.activeElement).toBe(inChapterTwo);
	});

	it('keeps what was decided, turned down and left for later one fold away, each saying the chapter it leads to', () => {
		const overview = {
			...TOLD.story.overview,
			decisions: [{ text: 'The last line closes the file.', chapter: 'ch-2' }],
			later: [{ text: 'A line for c.py.', chapter: null }]
		};
		review = openReview({ files, story: storyHeld({ ...TOLD.story, overview }) });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		const more = screen.getByTestId('story-more');

		expect(more.textContent).toContain('Decided, and why');
		expect(more.textContent).toContain('The last line closes the file. — chapter 2');
		expect(more.textContent).toContain('Left for later');
		expect(more.textContent).not.toContain('Turned down');
	});

	it('heads each of those lists a level under the change in short, never beside the chapters', () => {
		const overview = {
			...TOLD.story.overview,
			decisions: [{ text: 'The last line closes the file.', chapter: 'ch-2' }],
			later: [{ text: 'A line for c.py.', chapter: null }]
		};
		review = openReview({ files, story: storyHeld({ ...TOLD.story, overview }) });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		const headings = within(screen.getByTestId('story-more')).getAllByRole('heading', { level: 3 });

		expect(headings.map((heading) => heading.textContent)).toEqual(['Decided, and why', 'Left for later']);
	});

	it('offers no more about a change the overview lists nothing of', () => {
		render(ReviewScreen, { props: { review } });

		expect(screen.queryByTestId('story-more')).toBeNull();
	});

	it('shows no base in the header: a story is of the whole change, whatever the files are read against', () => {
		render(ReviewScreen, { props: { review } });

		expect(screen.queryByTestId('base-picker')).toBeNull();
	});

	it('says the story is a reconstruction where the agent told it from commits', () => {
		review = openReview({ files, story: storyHeld({ told_from: 'commits' }) });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		expect(screen.getByTestId('story-reconstructed').textContent).toBe('reconstructed');
		expect(screen.getByText(NOT_THE_AGENTS_OWN_CHANGE)).toBeTruthy();
	});

	it('says nothing of a reconstruction where the agent told it from memory', () => {
		render(ReviewScreen, { props: { review } });

		expect(screen.queryByTestId('story-reconstructed')).toBeNull();
		expect(screen.queryByText(NOT_THE_AGENTS_OWN_CHANGE)).toBeNull();
	});
});

describe('a piece of a story, as the reader scrolls', () => {
	beforeEach(() => {
		scriptTheScroll();
		review = openReview({ files, story: TOLD });
		review.views.choose('story');
	});

	it('is not built until the reader comes near it, and stays built once they have', () => {
		render(ReviewScreen, { props: { review } });
		const [first, second] = pieces();
		expect(within(first).getByTestId('file-placeholder')).toBeTruthy();
		expect(first.textContent).not.toContain('line 1 of a.py');

		scrollTo(first);
		flushSync();
		expect(first.textContent).toContain('line 1 of a.py');
		expect(within(second).getByTestId('file-placeholder')).toBeTruthy();

		scrollTo(second);
		flushSync();
		expect(first.textContent).toContain('line 1 of a.py');
		expect(second.textContent).toContain('line 5 of b.py');
	});

	it('is the one the reader is in once they have scrolled to it', () => {
		render(ReviewScreen, { props: { review } });
		const [, second] = pieces();

		scrollTo(second);

		expect(review.sections.fileInView).toBe('b.py');
	});

	it('is watched for coming near within the area the story scrolls in, not within the page', () => {
		render(ReviewScreen, { props: { review } });
		const [first] = pieces();

		expect(new Set(areasWatching(first))).toEqual(new Set([screen.getByTestId('story-view')]));
	});
});

describe('the room a piece of a story holds before it is built', () => {
	it('is a row for every line it shows, and one row where it shows no line', () => {
		const picture = diffFile({ path: 'docs/logo.png', status: 'added', unshown: 'binary' });
		const chapters = [toldChapter('ch-1', [toldStepOfLines('a.py', 5, 9)])];
		review = openReview({ files, story: storyHeld({ chapters, left_out: [{ piece: picture, changed_lines: 0 }] }) });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		const [ofFiveLines, ofNoLine] = pieces();

		expect(ofFiveLines.style.getPropertyValue('--cr-rows')).toBe('5');
		expect(ofNoLine.style.getPropertyValue('--cr-rows')).toBe('1');
	});
});

describe('a story the diff is taken again under', () => {
	it('is drawn no more once the story followed onto the diff taken again cannot be read', async () => {
		review = openReview({ files, story: TOLD });
		review.views.choose('story');
		const server = fakeServer();
		server.answer('POST /api/anchors/follow', { anchors: [] });
		server.answer('GET /api/diff', diffResponse({ files, take: A_LATER_TAKE }));
		server.refuse('GET /api/story', SERVER_ERROR, 'the review fell over');
		render(ReviewScreen, { props: { review } });

		handOverNext(review, { type: 'diff', file_count: 3, changes: null });
		await settled();

		expect(screen.queryAllByTestId('story-piece')).toEqual([]);
	});
});

describe('a piece of a file that was moved', () => {
	it('says where the file was, as the files do', () => {
		const moved = diffFile({
			path: 'new_name.py',
			old_path: 'old_name.py',
			status: 'renamed',
			hunks: [hunk([addedLine(1, 'one')], { header: '', old_start: 1, new_start: 1 })]
		});
		const told = storyHeld({
			chapters: [
				toldChapter('ch-1', [
					{
						...toldStep('new_name.py', 1),
						now: { lines: { first: 1, last: 1 }, piece: moved, changed_since_told: false }
					}
				])
			]
		});
		review = openReview({ files, story: told });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		expect(screen.getByTestId('story-piece-header').textContent).toContain('old_name.py → new_name.py');
	});
});

describe('what a piece of a story leaves out between its hunks', () => {
	// A step that runs over two changes of a.py, lines 1 and 9, and what no step tells of b.py: two runs
	// of it, lines 1 and 6, around lines some other step tells
	const overTwoChanges = diffFile({
		path: 'a.py',
		hunks: [
			hunk([addedLine(1, 'one')], { header: '', old_start: 1, new_start: 1 }),
			hunk([addedLine(9, 'nine')], { header: '', old_start: 8, new_start: 9 })
		]
	});
	const twoRunsNoStepTells = diffFile({
		path: 'b.py',
		hunks: [
			hunk([addedLine(1, 'first')], { header: '', old_start: 1, new_start: 1 }),
			hunk([addedLine(6, 'sixth')], { header: '', old_start: 1, new_start: 6 })
		]
	});
	const told = storyHeld({
		chapters: [
			toldChapter('ch-1', [
				{
					...toldStep('a.py', 1),
					lines: { first: 1, last: 9 },
					now: { lines: { first: 1, last: 9 }, piece: overTwoChanges, changed_since_told: false }
				}
			])
		],
		left_out: [{ piece: twoRunsNoStepTells, changed_lines: 2 }]
	});

	beforeEach(() => {
		review = openReview({ files, story: told });
		review.views.choose('story');
	});

	it('is said to be unchanged in a step: between two changes it tells lie lines the change kept', () => {
		render(ReviewScreen, { props: { review } });

		const [theStep] = pieces();

		expect(within(theStep).getByTestId('hunk-gap').textContent.trim()).toBe('⋯ 7 unchanged lines');
	});

	it('is said only to be not shown where no step tells the lines around it: a step may tell those between', () => {
		render(ReviewScreen, { props: { review } });

		const inWhatWasLeftOut = within(screen.getByTestId('story-left-out')).getByTestId('hunk-gap');

		expect(inWhatWasLeftOut.textContent.trim()).toBe('⋯ 4 lines not shown here');
	});
});

describe('the files, read where a story could be', () => {
	it('stay drawn as they are when the tree beside them is put away', async () => {
		const user = userEvent.setup();
		review = openReview({ files, story: TOLD });
		render(ReviewScreen, { props: { review } });
		const drawn = screen.getByTestId('diff-view');

		await user.click(screen.getByTestId('hide-sidebar'));

		expect(screen.getByTestId('diff-view')).toBe(drawn);
	});
});

describe('a story whose code a round changed after it was told', () => {
	// The round the code moved on in, and a story whose first chapter has these steps, marked as a round changed them,
	// and says of itself what the review says the round changed of it
	const MOVED_ON_IN = 2;
	function followedWith(first: ToldStep[], changed: ToldChapter['changed']): StoryHeld {
		return storyHeld(
			{
				...TOLD.story,
				chapters: [toldChapter('ch-1', first, { title: 'The beginnings', changed }), ...TOLD.story.chapters.slice(1)]
			},
			{ moved_on: codeMovedOn({ round: MOVED_ON_IN }) }
		);
	}

	it('says first under the head of a chapter the review says it changed, how many steps, and in which round', () => {
		// The page counts no step: the warning says the review's count, whatever the steps' marks
		const changed = chapterChanged({ round: MOVED_ON_IN, steps: 2 });
		review = openReview({ files, story: followedWith([toldStep('a.py', 1), toldStep('b.py', 5)], changed) });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		const [beginnings] = screen.getAllByTestId('story-chapter');
		const inOrder = beginnings.querySelectorAll<HTMLElement>(
			'[data-testid="part-head"], [data-testid="chapter-changed"], [data-testid="chapter-why-block"]'
		);

		expect([...inOrder].map((element) => element.dataset.testid)).toEqual([
			'part-head',
			'chapter-changed',
			'chapter-why-block'
		]);
		expect(said(within(beginnings).getByTestId('chapter-changed'))).toBe(
			'Changed after it was told. 2 steps in this chapter changed in round 2. The code below is current; the reasons beside it may not be.'
		);
	});

	it('says last that the agent is updating the reasons, while it tells the story again', () => {
		const story = followedWith([changedStep('a.py', 1), toldStep('b.py', 5)], chapterChanged());
		review = openReview({ files, story, asking: TAKEN });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		expect(said(screen.getByTestId('chapter-changed'))).toBe(
			'Changed after it was told. 1 step in this chapter changed in round 2. The code below is current; the reasons beside it may not be. The agent is updating them.'
		);
	});

	it('says nothing of the agent updating them where the story asked for again waits for an agent to attach', () => {
		const story = followedWith([changedStep('a.py', 1), toldStep('b.py', 5)], chapterChanged());
		review = openReview({ files, story, asking: ASKED });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		expect(said(screen.getByTestId('chapter-changed'))).not.toContain('The agent is updating them.');
	});

	it('says one step as one', () => {
		review = openReview({
			files,
			story: followedWith([changedStep('a.py', 1), toldStep('b.py', 5)], chapterChanged())
		});
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		expect(said(screen.getByTestId('chapter-changed'))).toContain('1 step in this chapter changed in round 2.');
	});

	it('says nothing of it in a chapter the review says it changed nothing of', () => {
		review = openReview({
			files,
			story: followedWith([changedStep('a.py', 1), toldStep('b.py', 5)], chapterChanged())
		});
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		const [, theEnd] = screen.getAllByTestId('story-chapter');

		expect(within(theEnd).queryByTestId('chapter-changed')).toBeNull();
	});

	it('draws a step whose code is out of the change by its number and its reason, and says in a line it is gone', () => {
		const story = followedWith([stepWithoutCode('a.py', 1, 'Why a.py starts so.'), toldStep('b.py', 5)], null);
		review = openReview({ files, story });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		const [beginnings] = screen.getAllByTestId('story-chapter');
		const [withoutCode] = within(beginnings).getAllByTestId('story-step-without-code');

		expect(said(within(withoutCode).getByTestId('step-reason'))).toBe('Why a.py starts so.');
		expect(said(within(withoutCode).getByTestId('step-code-not-found'))).toBe('Its code in a.py is no longer found.');
		expect(within(beginnings).getAllByTestId('story-piece')).toHaveLength(1);
	});

	it('counts in the head of a chapter whose steps show no code only its steps, and no files', () => {
		review = openReview({ files, story: followedWith([stepWithoutCode('a.py', 1)], null) });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		const [beginnings] = screen.getAllByTestId('story-chapter');

		expect(said(within(beginnings).getByTestId('chapter-counts'))).toBe('1 step');
	});

	it('lets the reader ask about the reason of a step whose code is out of the change', () => {
		const story = followedWith([stepWithoutCode('a.py', 1, 'Why a.py starts so.'), toldStep('b.py', 5)], null);
		review = openReview({ files, story });
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		const [withoutCode] = screen.getAllByTestId('story-step-without-code');

		expect(within(withoutCode).getByTestId('step-reason-block')).toBeTruthy();
	});

	it('names a step it changed so to whoever cannot see it stepped back, and a step it did not as ever', () => {
		review = openReview({
			files,
			story: followedWith([changedStep('a.py', 1), toldStep('b.py', 5)], chapterChanged())
		});
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		const [beginnings] = screen.getAllByTestId('story-chapter');

		expect(
			within(beginnings)
				.getAllByTestId('step-number')
				.map((number) => number.getAttribute('aria-label'))
		).toEqual(['Step 1.1, changed after it was told', 'Step 1.2']);
	});
});

describe('a review nobody has told a story of yet', () => {
	it('says nothing of the comments it holds: there is no story for them to be off', () => {
		review = openReview({ files });
		review.threads.add(newComment({ file: 'a.py', startLine: 9, body: 'about the last line' }));
		review.views.choose('story');
		render(ReviewScreen, { props: { review } });

		expect(screen.queryByTestId('threads-off-the-story')).toBeNull();
	});
});

describe('a review no story can be told of', () => {
	it('offers none, and is read by its files though the reader chose the story last', () => {
		openReview({ files, story: TOLD }).views.choose('story');
		review = openReview({ files, facts: { takes_a_story: false } });
		render(ReviewScreen, { props: { review } });

		expect(screen.queryByTestId('reading-view')).toBeNull();
		expect(screen.getByTestId('diff-view')).toBeTruthy();
	});
});
