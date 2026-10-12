import { beforeEach, describe, it, expect, vi } from 'vitest';
import { Navigator, type ViewsOnScreen } from '$lib/review/navigator';
import type { ReadingView } from '$lib/review/reading-view';
import type { Review } from '$lib/review/review.svelte';
import { addedLine, contextLine, diffFile, hunk, removedLine } from './diff';
import { newComment } from './new-comment';
import { openReview } from './review';
import { settled } from './settled';

let review: Review;

beforeEach(() => {
	review = openReview();
});

/**
 * Draw every thread of the review where the page would, and keep the body
 * of each one brought into view, in the order they were.
 */
function drawThreads(): string[] {
	const brought: string[] = [];
	for (const thread of review.threads.all) {
		const drawn = document.createElement('div');
		drawn.scrollIntoView = () => brought.push(thread.body);
		review.sections.registerThread(thread.id, drawn);
	}
	return brought;
}

describe('stepping through the threads', () => {
	it('keeps one position, so two controls cannot disagree', () => {
		review.threads.add(newComment({ startLine: 1, body: 'one' }));
		review.threads.add(newComment({ startLine: 2, body: 'two' }));
		const brought = drawThreads();

		review.navigator.step(1);
		review.navigator.step(1);
		review.navigator.step(-1);

		expect(brought).toEqual(['one', 'two', 'one']);
	});

	it('wraps around rather than stopping at the end', () => {
		review.threads.add(newComment({ body: 'one' }));
		const brought = drawThreads();

		review.navigator.step(1);
		review.navigator.step(1);

		expect(brought).toEqual(['one', 'one']);
	});

	it('puts the keyboard on the thread without moving the screen again, which is already on its way there', () => {
		review.threads.add(newComment({ startLine: 1, body: 'one' }));
		const [thread] = review.threads.all;
		const drawn = document.createElement('div');
		drawn.scrollIntoView = () => undefined;
		const focusedWith: (FocusOptions | undefined)[] = [];
		drawn.focus = (options) => focusedWith.push(options);
		review.sections.registerThread(thread.id, drawn);

		review.navigator.step(1);

		expect(focusedWith).toEqual([{ preventScroll: true }]);
	});

	it('has nothing to step to when there are no threads', () => {
		const brought = drawThreads();

		review.navigator.step(1);

		expect(brought).toEqual([]);
	});

	it('goes back from nowhere to the last thread', () => {
		review.threads.add(newComment({ startLine: 1, body: 'one' }));
		review.threads.add(newComment({ startLine: 2, body: 'two' }));
		review.threads.add(newComment({ startLine: 3, body: 'three' }));
		const brought = drawThreads();

		review.navigator.step(-1);

		expect(brought).toEqual(['three']);
	});

	it('goes on from the thread it is on when one before it is removed', () => {
		const first = review.threads.add(newComment({ startLine: 1, body: 'one' }));
		review.threads.add(newComment({ startLine: 2, body: 'two' }));
		review.threads.add(newComment({ startLine: 3, body: 'three' }));
		const brought = drawThreads();
		review.navigator.step(1);
		review.navigator.step(1);

		review.threads.remove(first);
		review.navigator.step(1);

		expect(brought).toEqual(['one', 'two', 'three']);
	});

	it('goes on from the thread the reader was last taken to, by whatever control', () => {
		review.threads.add(newComment({ startLine: 1, body: 'one' }));
		review.threads.add(newComment({ startLine: 2, body: 'two' }));
		review.threads.add(newComment({ startLine: 3, body: 'three' }));
		const brought = drawThreads();
		const [, second] = review.threads.all;

		if (second) review.navigator.reveal(second);
		review.navigator.step(1);

		expect(brought).toEqual(['two', 'three']);
	});

	it('goes on to the next thread from one the reader removed, and back to the one before it', () => {
		review.threads.add(newComment({ startLine: 1, body: 'one' }));
		const second = review.threads.add(newComment({ startLine: 2, body: 'two' }));
		review.threads.add(newComment({ startLine: 3, body: 'three' }));
		const brought = drawThreads();
		review.navigator.step(1);
		review.navigator.step(1);

		review.threads.remove(second);
		review.navigator.step(1);
		review.navigator.step(-1);

		expect(brought).toEqual(['one', 'two', 'three', 'one']);
	});

	it('goes back from a removed thread to the one before it', () => {
		review.threads.add(newComment({ startLine: 1, body: 'one' }));
		const second = review.threads.add(newComment({ startLine: 2, body: 'two' }));
		review.threads.add(newComment({ startLine: 3, body: 'three' }));
		const brought = drawThreads();
		review.navigator.step(1);
		review.navigator.step(1);

		review.threads.remove(second);
		review.navigator.step(-1);

		expect(brought).toEqual(['one', 'two', 'one']);
	});
});

describe('the order the threads are stepped through', () => {
	// Two files, in the order the diff holds them: a.py with a change at its
	// top and one further down, where two lines were replaced by two
	const files = [
		diffFile({
			path: 'a.py',
			hunks: [
				hunk([contextLine(1, 1, 'import os'), addedLine(2, 'import sys')]),
				hunk(
					[
						contextLine(38, 39, 'def run():'),
						removedLine(39, '    old_first()'),
						removedLine(40, '    old_second()'),
						addedLine(40, '    new_first()'),
						addedLine(41, '    new_second()')
					],
					{ header: '@@ -38,3 +39,3 @@', old_start: 38, new_start: 39 }
				)
			]
		}),
		diffFile({ path: 'b.py', hunks: [hunk([addedLine(1, 'x = 1')])] })
	];

	it('goes down the diff, file by file and line by line, whatever order they were written in', () => {
		review = openReview({ files });
		review.threads.add(newComment({ file: 'b.py', startLine: 1, body: 'b.py:1' }));
		review.threads.add(newComment({ file: 'a.py', startLine: 41, body: 'a.py:41' }));
		review.threads.add(newComment({ file: 'a.py', startLine: 2, body: 'a.py:2' }));
		const brought = drawThreads();

		review.navigator.step(1);
		review.navigator.step(1);
		review.navigator.step(1);

		expect(brought).toEqual(['a.py:2', 'a.py:41', 'b.py:1']);
	});

	it('takes a removed line before the line that replaced it, as they are drawn, whatever their numbers', () => {
		review = openReview({ files });
		review.threads.add(newComment({ file: 'a.py', startLine: 40, body: 'new 40' }));
		review.threads.add(newComment({ file: 'a.py', side: 'old', startLine: 40, body: 'old 40' }));
		const brought = drawThreads();

		review.navigator.step(1);
		review.navigator.step(1);

		expect(brought).toEqual(['old 40', 'new 40']);
	});

	it('takes a thread on a line read in between two changes where that line stands', () => {
		review = openReview({ files });
		review.threads.add(newComment({ file: 'a.py', startLine: 41, body: 'below' }));
		review.threads.add(newComment({ file: 'a.py', startLine: 20, body: 'read in between' }));
		review.threads.add(newComment({ file: 'a.py', startLine: 2, body: 'above' }));
		const brought = drawThreads();

		review.navigator.step(1);
		review.navigator.step(1);
		review.navigator.step(1);

		expect(brought).toEqual(['above', 'read in between', 'below']);
	});

	it('takes first the threads on a file the diff no longer holds, which are drawn above it', () => {
		review = openReview({ files });
		review.threads.add(newComment({ file: 'a.py', startLine: 2, body: 'on a.py' }));
		review.threads.add(newComment({ file: 'gone.py', startLine: 7, body: 'on gone.py' }));
		const brought = drawThreads();

		review.navigator.step(1);
		review.navigator.step(1);

		expect(brought).toEqual(['on gone.py', 'on a.py']);
	});
});

describe('moving the reader in whatever view the review is read in', () => {
	/** A view that draws none of the review: no section, no thread, no file. */
	const DRAWS_NOTHING: ReadingView = {
		sectionKeys: () => [],
		threadsInOrder: () => [],
		sectionOf: () => null,
		sectionOfFile: () => null,
		unfold: () => undefined,
		fileBeingRead: () => null
	};

	/** The review read in one view alone, with nothing else to bring on screen: what that view draws none of is nowhere. */
	function onlyIn(view: ReadingView): ViewsOnScreen {
		return { onScreen: () => view, showEverything: () => Promise.resolve(view) };
	}

	/** A section on the page under a key, which says when it is brought into view. */
	function sectionKnownBy(key: string, brought: string[]): HTMLElement {
		const section = document.createElement('section');
		section.scrollIntoView = () => brought.push(key);
		document.body.append(section);
		review.sections.register(key, 'a.py', section);
		return section;
	}

	it('takes the reader nowhere for a thread no view draws, though the page still does', async () => {
		review.threads.add(newComment({ startLine: 1, body: 'one' }));
		const brought = drawThreads();
		const [thread] = review.threads.all;
		const navigator = new Navigator(review.threads, review.sections, onlyIn(DRAWS_NOTHING));

		navigator.reveal(thread);
		await settled();

		expect(brought).toEqual([]);
	});

	it('goes to a thread the view on screen does not draw in the view that draws them all, brought on screen for it', async () => {
		review.threads.add(newComment({ file: 'a.py', startLine: 1, body: 'one' }));
		const [thread] = review.threads.all;
		const brought: string[] = [];
		sectionKnownBy('in the files', brought);
		const drawsAll = { ...DRAWS_NOTHING, sectionOf: () => 'in the files' };
		const showEverything = vi.fn(() => Promise.resolve(drawsAll));
		const navigator = new Navigator(review.threads, review.sections, { onScreen: () => DRAWS_NOTHING, showEverything });

		navigator.reveal(thread);
		await settled();

		expect(showEverything).toHaveBeenCalledOnce();
		expect(brought).toEqual(['in the files']);
	});

	it('leaves the view on screen as it is for a thread it draws', () => {
		review.threads.add(newComment({ file: 'a.py', startLine: 1, body: 'one' }));
		const [thread] = review.threads.all;
		sectionKnownBy('the piece that draws it', []);
		const draws = { ...DRAWS_NOTHING, sectionOf: () => 'the piece that draws it' };
		const showEverything = vi.fn(() => Promise.resolve(DRAWS_NOTHING));
		const navigator = new Navigator(review.threads, review.sections, { onScreen: () => draws, showEverything });

		navigator.reveal(thread);

		expect(showEverything).not.toHaveBeenCalled();
	});

	it('shows a file the view on screen draws none of in the view that draws every file, brought on screen for it', async () => {
		const brought: string[] = [];
		sectionKnownBy('a.py in the files', brought);
		const drawsAll = { ...DRAWS_NOTHING, sectionOfFile: () => 'a.py in the files' };
		const navigator = new Navigator(review.threads, review.sections, {
			onScreen: () => DRAWS_NOTHING,
			showEverything: () => Promise.resolve(drawsAll)
		});

		navigator.showFile('a.py');
		await settled();

		expect(brought).toEqual(['a.py in the files']);
	});

	it('shows no file no view draws any of, though a section stands on the page under its name', async () => {
		const brought: string[] = [];
		sectionKnownBy('a.py', brought);
		const navigator = new Navigator(review.threads, review.sections, onlyIn(DRAWS_NOTHING));

		navigator.showFile('a.py');
		await settled();

		expect(brought).toEqual([]);
	});

	it('shows a file in the section the view says draws it', () => {
		const brought: string[] = [];
		sectionKnownBy('the first piece of a.py', brought);
		const view = { ...DRAWS_NOTHING, sectionOfFile: vi.fn(() => 'the first piece of a.py') };
		const navigator = new Navigator(review.threads, review.sections, onlyIn(view));

		navigator.showFile('a.py');

		expect(view.sectionOfFile).toHaveBeenCalledWith('a.py');
		expect(brought).toEqual(['the first piece of a.py']);
	});

	it('walks the sections the view draws, in the order it draws them', () => {
		const brought: string[] = [];
		sectionKnownBy('drawn second', brought);
		sectionKnownBy('drawn first', brought);
		const view = { ...DRAWS_NOTHING, sectionKeys: () => ['drawn first', 'drawn second'] };
		const navigator = new Navigator(review.threads, review.sections, onlyIn(view));

		navigator.stepSection(1);

		expect(brought).toEqual(['drawn first']);
	});

	it('goes on from the section the reader is in, the one a line of which has the keyboard', () => {
		const brought: string[] = [];
		sectionKnownBy('drawn first', brought);
		const second = sectionKnownBy('drawn second', brought);
		sectionKnownBy('drawn third', brought);
		const lineNumber = second.appendChild(document.createElement('button'));
		const view = { ...DRAWS_NOTHING, sectionKeys: () => ['drawn first', 'drawn second', 'drawn third'] };
		const navigator = new Navigator(review.threads, review.sections, onlyIn(view));
		lineNumber.focus();

		navigator.stepSection(1);

		expect(brought).toEqual(['drawn third']);
	});

	it('goes to a thread by the section the view says draws it, and brings out what folds it away', () => {
		review.threads.add(newComment({ file: 'a.py', startLine: 1, body: 'one' }));
		const [thread] = review.threads.all;
		const brought: string[] = [];
		sectionKnownBy('the piece that draws it', brought);
		const view = { ...DRAWS_NOTHING, sectionOf: () => 'the piece that draws it', unfold: vi.fn() };
		const navigator = new Navigator(review.threads, review.sections, onlyIn(view));

		navigator.reveal(thread);

		expect(brought).toEqual(['the piece that draws it']);
		expect(view.unfold).toHaveBeenCalledWith(expect.objectContaining({ file: 'a.py' }));
	});
});

describe('going to a thread in the files as they are read one by one', () => {
	it('opens the file the reader folded away, so the thread in it can be drawn', () => {
		review = openReview({ files: [diffFile({ path: 'a.py', hunks: [hunk([addedLine(1, 'x = 1')])] })] });
		review.threads.add(newComment({ file: 'a.py', startLine: 1, body: 'in a folded file' }));
		const [thread] = review.threads.all;
		review.reading.toggleFolded('a.py');

		review.navigator.reveal(thread);

		expect(review.reading.isFolded('a.py')).toBe(false);
	});
});
