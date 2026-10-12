import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import type { Review } from '$lib/review/review.svelte';
import { A_LATER_TAKE, addedLine, diffFile, diffResponse, hunk, sinceRound } from '../diff';
import { fakeServer, keepingSettings } from '../fake-server';
import { newComment } from '../new-comment';
import { handOverNext } from '../pushes';
import { openReview } from '../review';
import { settled } from '../settled';
import { storyHeld, toldChapter, toldStep } from '../story';

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
});

describe('a review read as its story', () => {
	beforeEach(() => {
		review = openReview({ files, story: TOLD });
		review.layout.readingView.set('story');
	});

	it('says what the change is called, and which round the story was told in', () => {
		render(ReviewScreen, { props: { review } });

		expect(screen.getByTestId('story-title').textContent).toBe('Lines for a.py and b.py');
		expect(screen.getByTestId('story-round').textContent).toBe('Round 1');
	});

	it('tells every chapter in a row, each by its name', () => {
		render(ReviewScreen, { props: { review } });

		expect(screen.getAllByTestId('chapter-title').map((title) => title.textContent)).toEqual([
			'The beginnings',
			'The end'
		]);
	});

	it('says where to doubt a chapter, where the agent said', () => {
		render(ReviewScreen, { props: { review } });

		expect(screen.getByTestId('chapter-doubt').textContent).toContain('Whether b.py needs its line at all.');
	});

	it('numbers each step by its chapter and its place in it, and says its reason where it has one', () => {
		render(ReviewScreen, { props: { review } });

		const steps = screen.getAllByTestId('story-step');

		expect(steps.map((step) => within(step).getByTestId('step-number').textContent.trim())).toEqual([
			'1.1',
			'1.2',
			'2.1'
		]);
		expect(within(steps[0]).getByTestId('step-reason').textContent).toBe('The first line comes first.');
		expect(within(steps[1]).queryByTestId('step-reason')).toBeNull();
	});

	it('shows under each step the piece of its file the step tells, and no more of the file', () => {
		render(ReviewScreen, { props: { review } });

		const [firstStep] = screen.getAllByTestId('story-step');
		const shown = within(firstStep).getByTestId('story-piece');

		expect(shown.dataset.path).toBe('a.py');
		expect(shown.textContent).toContain('line 1 of a.py');
		expect(shown.textContent).not.toContain('line 9 of a.py');
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
		review.layout.readingView.set('story');
		render(ReviewScreen, { props: { review } });

		const leftOut = screen.getByTestId('story-left-out');

		expect(leftOut.textContent).toContain('Binary file');
		expect(leftOut.textContent).not.toContain('changed line');
	});

	it('names the files the agent called housekeeping, and draws none of them', () => {
		render(ReviewScreen, { props: { review } });

		expect(screen.getByTestId('story-housekeeping').textContent).toContain('uv.lock');
		expect(pieces().map((piece) => piece.dataset.path)).toEqual(['a.py', 'b.py', 'a.py', 'a.py']);
	});

	it('draws a thread under its line, in the one piece that shows the line', () => {
		review.threads.add(newComment({ file: 'a.py', startLine: 9, body: 'about the last line' }));
		render(ReviewScreen, { props: { review } });

		const drawingIt = pieces().filter((piece) => within(piece).queryByText('about the last line') !== null);

		expect(drawingIt).toEqual([pieces()[2]]);
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

	it('says how many comments are on lines it does not show, and takes the reader to the files for them', async () => {
		const user = userEvent.setup();
		review.threads.add(newComment({ file: 'uv.lock', startLine: 1, body: 'about the lock file' }));
		render(ReviewScreen, { props: { review } });

		expect(screen.getByTestId('threads-off-the-story').textContent).toContain(
			'1 comment is on lines the story does not show.'
		);
		await user.click(screen.getByTestId('show-in-files'));

		expect(screen.getByTestId('diff-view')).toBeTruthy();
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

		expect(review.readsStory).toBe(false);
		expect(document.activeElement).toBe(screen.getByTestId('comment-thread'));
	});

	it('shows a file the agent names in the files, where the story draws none of it, once they are drawn', async () => {
		render(ReviewScreen, { props: { review } });

		handOverNext(review, { type: 'show', file: 'uv.lock' });
		await settled();

		expect(review.readsStory).toBe(false);
		expect(review.sections.fileInView).toBe('uv.lock');
	});

	it('shows a file the agent names where the story first tells it, and stays in the story', async () => {
		render(ReviewScreen, { props: { review } });

		handOverNext(review, { type: 'show', file: 'b.py' });
		await settled();

		expect(review.readsStory).toBe(true);
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

		await user.keyboard('n');
		expect(document.activeElement?.textContent).toContain('in chapter one');

		await user.keyboard('n');
		expect(document.activeElement?.textContent).toContain('in chapter two');
	});

	it('keeps what was decided, turned down and left for later one fold away, each saying the chapter it leads to', () => {
		const overview = {
			...TOLD.story.overview,
			decisions: [{ text: 'The last line closes the file.', chapter: 'ch-2' }],
			later: [{ text: 'A line for c.py.', chapter: null }]
		};
		review = openReview({ files, story: storyHeld({ ...TOLD.story, overview }) });
		review.layout.readingView.set('story');
		render(ReviewScreen, { props: { review } });

		const more = screen.getByTestId('story-more');

		expect(more.textContent).toContain('Decided, and why');
		expect(more.textContent).toContain('The last line closes the file. — chapter 2');
		expect(more.textContent).toContain('Left for later');
		expect(more.textContent).not.toContain('Turned down');
	});

	it('offers no more about a change the overview lists nothing of', () => {
		render(ReviewScreen, { props: { review } });

		expect(screen.queryByTestId('story-more')).toBeNull();
	});

	it('shows a diagram as the agent wrote it, under what it is called', () => {
		const diagram = { mermaid: 'flowchart LR; a --> b', caption: 'How a line travels', links: {} };
		const overview = { ...TOLD.story.overview, diagram };
		review = openReview({ files, story: storyHeld({ ...TOLD.story, overview }) });
		review.layout.readingView.set('story');
		render(ReviewScreen, { props: { review } });

		const drawn = screen.getByTestId('story-diagram');

		expect(drawn.textContent).toContain('How a line travels');
		expect(drawn.textContent).toContain('flowchart LR; a --> b');
	});

	it('shows no base in the header: a story is of the whole change, whatever the files are read against', () => {
		render(ReviewScreen, { props: { review } });

		expect(screen.queryByTestId('base-picker')).toBeNull();
	});

	it('says the story is a reconstruction where the agent told it from commits', () => {
		review = openReview({ files, story: storyHeld({ told_from: 'commits' }) });
		review.layout.readingView.set('story');
		render(ReviewScreen, { props: { review } });

		expect(screen.getByTestId('story-reconstructed').textContent).toBe('reconstructed');
	});

	it('says nothing of a reconstruction where the agent told it from memory', () => {
		render(ReviewScreen, { props: { review } });

		expect(screen.queryByTestId('story-reconstructed')).toBeNull();
	});
});

describe('a story told of the take of the change the page reads', () => {
	beforeEach(() => {
		review = openReview({ files, story: TOLD });
		review.layout.readingView.set('story');
	});

	it('says nothing of the code having changed', () => {
		render(ReviewScreen, { props: { review } });

		expect(screen.queryByTestId('story-moved-on')).toBeNull();
	});

	it('says the code has changed since it was told, once the diff is taken again under it', async () => {
		const server = fakeServer();
		server.answer('POST /api/anchors/follow', { anchors: [] });
		server.answer('GET /api/diff', diffResponse({ files, take: A_LATER_TAKE }));
		render(ReviewScreen, { props: { review } });

		handOverNext(review, { type: 'diff', file_count: 3, changes: null });
		await settled();

		expect(screen.getByTestId('story-moved-on').textContent).toContain(
			'The code has changed since this story was told.'
		);
	});
});

describe('a story the code has moved on from', () => {
	beforeEach(() => {
		review = openReview({ files, story: TOLD, diff: { take: A_LATER_TAKE } });
		review.layout.readingView.set('story');
	});

	it('is still told whole, every step with the code as it was', () => {
		render(ReviewScreen, { props: { review } });

		expect(pieces().map((piece) => piece.dataset.path)).toEqual(['a.py', 'b.py', 'a.py', 'a.py']);
		expect(pieces()[1].textContent).toContain('line 5 of b.py');
	});

	it('takes no comment on a line of a step, whose number is no longer that line of the file, and says why', async () => {
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });
		const lineNumber = within(pieces()[1]).getByRole('button', { name: 'Comment on line 5' });

		await user.click(lineNumber);

		expect(screen.queryByTestId('comment-input')).toBeNull();
		expect(lineNumber.getAttribute('aria-disabled')).toBe('true');
		expect(lineNumber.title).toBe(
			'This is the code as the story was told; it has changed since. Comment on it in Files.'
		);
	});

	it('draws no thread under a line of the number the thread hangs on, and says the comments are in Files', () => {
		review.threads.add(newComment({ file: 'a.py', startLine: 9, body: 'about the last line' }));
		render(ReviewScreen, { props: { review } });

		expect(screen.queryByText('about the last line')).toBeNull();
		expect(screen.getByTestId('story-moved-on').textContent).toContain('1 comment is in Files.');
	});

	it('says nothing of comments while the review holds none', () => {
		render(ReviewScreen, { props: { review } });

		expect(screen.getByTestId('story-moved-on').textContent).not.toContain('in Files');
	});

	it('says a comment that was being written on a line of it is in Files, where its line now is', () => {
		const onLineFive = { side: 'new', startLine: 5, endLine: 5, opensBelow: { side: 'new', number: 5 } } as const;
		review.threads.writing.pickLines('b.py', onLineFive, ['in b.py']);
		render(ReviewScreen, { props: { review } });

		expect(screen.queryByTestId('comment-input')).toBeNull();
		expect(screen.getByTestId('story-moved-on').textContent).toContain('1 comment you were writing is in Files.');
	});

	it('counts no comment as on a line it does not show: it shows no line of the code as it is', () => {
		review.threads.add(newComment({ file: 'uv.lock', startLine: 1, body: 'about the lock file' }));
		render(ReviewScreen, { props: { review } });

		expect(screen.queryByTestId('threads-off-the-story')).toBeNull();
	});

	it('is of the code on screen again once the agent tells it again', async () => {
		fakeServer().answer('GET /api/story', { held: storyHeld(TOLD.story, { take: A_LATER_TAKE }) });
		render(ReviewScreen, { props: { review } });

		handOverNext(review, { type: 'story' });
		await settled();

		expect(screen.queryByTestId('story-moved-on')).toBeNull();
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

describe('a review nobody has told a story of yet', () => {
	it('says so where the story would be, and how one is told', () => {
		review = openReview({ files });
		review.layout.readingView.set('story');
		render(ReviewScreen, { props: { review } });

		expect(screen.getByTestId('no-story').textContent).toContain('No story has been told of this change yet.');
	});
});

describe('a review no story can be told of', () => {
	it('offers none, and is read by its files though the reader chose the story last', () => {
		review = openReview({ files, facts: { takes_a_story: false } });
		review.layout.readingView.set('story');
		render(ReviewScreen, { props: { review } });

		expect(screen.queryByTestId('reading-view')).toBeNull();
		expect(screen.getByTestId('diff-view')).toBeTruthy();
	});
});
