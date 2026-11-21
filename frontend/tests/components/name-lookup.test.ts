import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import type { Review } from '$lib/review/review.svelte';
import type { DiffFile, NamePlace, NameResponse } from '$lib/types';
import { caretByRangeAlone, caretFallsAt, caretRangeFallsAt, noCaretUnderThePointer } from '../caret';
import { A_LATER_TAKE, addedLine, contextLine, diffFile, diffResponse, hunk, OF_FILES, removedLine } from '../diff';
import { type FakeServer, fakeServer, SERVER_ERROR } from '../fake-server';
import { frames } from '../frames';
import { openReview } from '../review';
import { settled } from '../settled';
import { storyResponse } from '../story';

// A file of no language the page highlights, so each line's code is its text alone; its lines 1 to 3 and 40 are
// drawn, 4 to 39 left out between its hunks, and its old line 3 removed
const NOTES = diffFile({
	path: 'src/notes.txt',
	hunks: [
		hunk([
			contextLine(1, 1, 'total = 0'),
			addedLine(2, 'say(😀, total)'),
			contextLine(2, 3, '# keeps the total'),
			removedLine(3, 'total -= 9')
		]),
		hunk([contextLine(39, 40, 'total += 1')], { header: '', old_start: 39, new_start: 40 })
	]
});
// What the route answers where what it is asked of is not in the review
const NOT_FOUND = 404;

let server: FakeServer;
let review: Review;

beforeEach(() => {
	server = fakeServer();
});

/** Open the review of the change on screen, as a review of this kind. */
function opened(facts: Parameters<typeof openReview>[0] = {}): void {
	review = openReview({ files: [NOTES], ...facts });
	render(ReviewScreen, { props: { review } });
}

/** A place the review found the name at, as it answers one. */
function place(given: Partial<NamePlace>): NamePlace {
	return {
		path: 'src/notes.txt',
		line: 1,
		column: 0,
		text: 'total = 0',
		defined_as: null,
		inside: null,
		added: false,
		found_as: 'name',
		...given
	};
}

/** Press a line's code with the key held, the caret falling at a character of it, and let the review answer. */
async function pressWithTheKey(row: number, offset: number): Promise<void> {
	const code = screen.getAllByTestId('line-code')[row];
	caretFallsAt(code.firstChild as Node, offset);
	fireEvent.click(code, { ctrlKey: true });
	await settled();
}

/** Take the change again, as a round landing does, with these files in it, and let the page draw what came. */
async function takenAgainAs(files: DiffFile[]): Promise<void> {
	server.answer('POST /api/anchors/follow', { anchors: [] });
	server.answer('GET /api/diff', diffResponse({ files, take: A_LATER_TAKE }));
	server.answer('GET /api/story', storyResponse());
	await review.takeRetakenDiff();
	await frames();
}

/** What the page asked the review about names. */
function namesAsked(): Record<string, string>[] {
	return server.requests.filter((request) => request.path === '/api/name').map((request) => request.query);
}

/** The pane's words, group by group: each group's heading and count, then each file's path and its lines. */
function listed(): string[] {
	return within(screen.getByTestId('name-lookup'))
		.getAllByTestId(/^name-(defined|used-untouched|used-in-the-change)$/)
		.map((group) => group.textContent.replace(/\s+/g, ' ').trim());
}

const TOTAL: NameResponse = {
	name: 'total',
	places: [
		place({ line: 1, column: 0, text: 'total = 0', defined_as: 'variable' }),
		place({ line: 2, column: 7, text: 'say(😀, total)', added: true }),
		place({ path: 'src/report.txt', line: 9, column: 6, text: 'print(total)' })
	]
};

describe('asking where a name is defined and used', () => {
	it('asks the review about the character pressed, its column counted in characters as the review counts them', async () => {
		server.answer('GET /api/name', TOTAL);
		opened();

		await pressWithTheKey(1, 8);

		expect(namesAsked()).toEqual([{ path: 'src/notes.txt', side: 'new', line: '2', column: '7' }]);
	});

	it('asks the review about the old side of a removed line, at its old number', async () => {
		server.answer('GET /api/name', TOTAL);
		opened();

		await pressWithTheKey(3, 0);

		expect(namesAsked()).toEqual([{ path: 'src/notes.txt', side: 'old', line: '3', column: '0' }]);
	});

	it('asks nothing at a click without the key, nor at one on no word', async () => {
		opened();
		const code = screen.getAllByTestId('line-code')[1];
		caretFallsAt(code.firstChild as Node, 8);

		fireEvent.click(code);
		caretFallsAt(code.firstChild as Node, 4);
		fireEvent.click(code, { ctrlKey: true });
		await settled();

		expect([namesAsked(), screen.queryByTestId('name-lookup')]).toEqual([[], null]);
	});

	it('asks nothing in a review of files, which has no repository', async () => {
		opened({ facts: { where: OF_FILES } });

		await pressWithTheKey(1, 8);

		expect([namesAsked(), screen.queryByTestId('name-lookup')]).toEqual([[], null]);
	});

	it('reads the caret by its range in a browser that has no other way to say it', async () => {
		server.answer('GET /api/name', TOTAL);
		caretByRangeAlone();
		opened();
		const code = screen.getAllByTestId('line-code')[1];

		caretRangeFallsAt(code.firstChild as Node, 8);
		fireEvent.click(code, { ctrlKey: true });
		await settled();

		expect(namesAsked()).toEqual([{ path: 'src/notes.txt', side: 'new', line: '2', column: '7' }]);
	});

	it.each([
		['no marks over text', () => vi.stubGlobal('Highlight', undefined)],
		['no caret under the pointer', noCaretUnderThePointer]
	])('opens the review in a browser with %s, offering no lookup there nor in the help', async (_, lacking) => {
		const user = userEvent.setup();
		lacking();
		opened();

		await pressWithTheKey(1, 8);
		await user.keyboard('?');

		expect(namesAsked()).toEqual([]);
		expect(within(screen.getByTestId('shortcuts-list')).queryByText('Ctrl+click')).toBeNull();
	});

	it('says what it looks for while the review looks', async () => {
		server.hold('GET /api/name');
		opened();

		await pressWithTheKey(1, 8);

		const pane = screen.getByTestId('name-lookup');
		expect(within(pane).getByTestId('name-lookup-heading').textContent).toBe('total');
		expect(within(pane).getByTestId('name-lookup-looking').textContent).toContain('Looking through the repository');
	});

	it('lists where the name is defined, used where the change did not touch, and used in the change, with a count', async () => {
		server.answer('GET /api/name', TOTAL);
		opened();

		await pressWithTheKey(1, 8);

		expect(screen.getByTestId('name-lookup-count').textContent).toBe('1 definition, 2 uses');
		expect(listed()).toEqual([
			'Defined 1 src/notes.txt 1total = 0Go to symbol',
			'Used where the change did not touch 1 src/report.txt 9print(total)Go to symbol',
			'Used in this change 1 src/notes.txt 2say(😀, total)Go to symbol'
		]);
	});

	it('hands the keyboard to the way to the first place as the places come', async () => {
		server.answer('GET /api/name', TOTAL);
		opened();

		await pressWithTheKey(1, 8);

		expect(document.activeElement).toBe(within(screen.getByTestId('name-defined')).getByTestId('go-to-symbol'));
	});

	it('lists a group’s first six places, and the rest at Show more', async () => {
		const uses = Array.from({ length: 8 }, (_, offset) => place({ line: offset + 10, text: `total(${offset})` }));
		server.answer('GET /api/name', { name: 'total', places: uses });
		opened();
		await pressWithTheKey(1, 8);
		const shownAtFirst = screen.getAllByTestId('name-place').length;
		const offered = screen.getByTestId('show-more-places').textContent;

		await userEvent.setup().click(screen.getByTestId('show-more-places'));

		expect([shownAtFirst, offered, screen.getAllByTestId('name-place').length]).toEqual([6, 'Show 2 more', 8]);
		expect(document.activeElement).toBe(screen.getAllByTestId('go-to-symbol')[6]);
	});

	it('says no definition was found where the review found none', async () => {
		server.answer('GET /api/name', { name: 'total', places: [place({})] });
		opened();

		await pressWithTheKey(1, 8);

		expect(screen.getByTestId('name-lookup-count').textContent).toBe('not defined here, 1 use');
		expect(screen.getByTestId('name-lookup-note').textContent).toBe(
			'No definition of this name was found in the repository.'
		);
	});

	it('says the uses may be of any of several things called so', async () => {
		const definitions = [place({ defined_as: 'variable' }), place({ line: 3, defined_as: 'function' })];
		server.answer('GET /api/name', { name: 'total', places: definitions });
		opened();

		await pressWithTheKey(1, 8);

		expect(screen.getByTestId('name-lookup-note').textContent).toBe(
			'2 things are called total. The review finds a name by how it is spelled, so the uses are of all of them.'
		);
	});

	it('says some places were found as words in text it reads no grammar of', async () => {
		const found = [place({ defined_as: 'variable' }), place({ path: 'README.md', found_as: 'text' })];
		server.answer('GET /api/name', { name: 'total', places: found });
		opened();

		await pressWithTheKey(1, 8);

		expect(screen.getByTestId('name-lookup-note').textContent).toBe(
			'Some places are this word found in text the review has no grammar for, so they may not be this name.'
		);
	});

	it('says nothing in the code is called so, where the word stands in a comment', async () => {
		server.answer('GET /api/name', { name: 'keeps', places: [] });
		opened();

		await pressWithTheKey(2, 3);

		expect(screen.getByTestId('name-lookup-nothing').textContent).toContain('Nothing in the code is called “keeps”.');
	});

	it('says what the review refused to look through, with Try again', async () => {
		server.refuse('GET /api/name', NOT_FOUND, 'no file to read at src/notes.txt on the new side');
		opened();

		await pressWithTheKey(1, 8);

		expect(screen.getByTestId('name-lookup-failed').textContent).toBe(
			'no file to read at src/notes.txt on the new side'
		);
		expect(screen.getByTestId('look-again').textContent?.trim()).toBe('Try again');
	});

	it('says why a lookup failed, and looks again at Try again, which holds the keyboard', async () => {
		server.refuse('GET /api/name', SERVER_ERROR, 'git stopped with "fatal: unable to read tree"');
		opened();
		await pressWithTheKey(1, 8);
		const said = screen.getByTestId('name-lookup-failed').textContent;
		const tryAgain = screen.getByTestId('look-again');
		const keyboardOn = document.activeElement;

		server.answer('GET /api/name', TOTAL);
		await userEvent.setup().click(tryAgain);
		await settled();

		expect([said, keyboardOn]).toEqual(['git stopped with "fatal: unable to read tree"', tryAgain]);
		expect(screen.getByTestId('name-lookup-count').textContent).toBe('1 definition, 2 uses');
	});

	it('closes at Escape, the keyboard back on the line pressed', async () => {
		server.answer('GET /api/name', TOTAL);
		opened();
		await pressWithTheKey(1, 8);

		await userEvent.setup().keyboard('{Escape}');
		await settled();

		expect(screen.queryByTestId('name-lookup')).toBeNull();
		expect(document.activeElement?.textContent?.trim()).toBe('2');
	});

	it('steps to the line after the one pressed at the key for the next line, pressed in the pane, which closes', async () => {
		server.answer('GET /api/name', TOTAL);
		opened();
		await pressWithTheKey(1, 8);

		await userEvent.setup().keyboard('j');
		await settled();

		expect(screen.queryByTestId('name-lookup')).toBeNull();
		expect(document.activeElement?.textContent?.trim()).toBe('3');
	});

	it('closes once the change is taken again, what it lists being of the take before, the keyboard on the line pressed', async () => {
		server.answer('GET /api/name', TOTAL);
		opened();
		await pressWithTheKey(1, 8);

		await takenAgainAs([NOTES]);

		expect(screen.queryByTestId('name-lookup')).toBeNull();
		expect(document.activeElement?.textContent?.trim()).toBe('2');
	});

	it('closes once the diff read against another base draws the line pressed without the name', async () => {
		server.answer('GET /api/name', TOTAL);
		opened();
		await pressWithTheKey(1, 8);
		const renamed = diffFile({
			path: 'src/notes.txt',
			hunks: [hunk([contextLine(1, 1, 'total = 0'), addedLine(2, 'say(😀, count)')])]
		});

		server.answer('GET /api/diff', diffResponse({ files: [renamed] }));
		await review.diff.take();
		await frames();

		expect(screen.queryByTestId('name-lookup')).toBeNull();
		expect(document.activeElement?.textContent?.trim()).toBe('2');
	});

	it('leaves the keyboard on the file’s toggle where the change taken again draws no such line', async () => {
		server.answer('GET /api/name', TOTAL);
		opened();
		await pressWithTheKey(1, 8);
		const shorter = diffFile({ path: 'src/notes.txt', hunks: [hunk([addedLine(1, 'total = 0')])] });

		await takenAgainAs([shorter]);

		expect(document.activeElement).toBe(screen.getByTestId('collapse-file'));
	});
});

describe('going to a place of a name', () => {
	it('takes the reader to the line, the pane put away, the keyboard on its number', async () => {
		server.answer('GET /api/name', TOTAL);
		opened();
		await pressWithTheKey(1, 8);

		await userEvent.setup().click(within(screen.getByTestId('name-defined')).getByTestId('go-to-symbol'));
		await settled();
		await frames();

		expect(screen.queryByTestId('name-lookup')).toBeNull();
		expect(document.activeElement?.textContent?.trim()).toBe('1');
	});

	it('reads in the line the diff left out between its hunks, and goes to it', async () => {
		const between = place({ line: 20, text: 'total -= 1' });
		server.answer('GET /api/name', { name: 'total', places: [between] });
		const read = Array.from({ length: 36 }, (_, offset) => `line ${offset + 4}`);
		server.answer('GET /api/file-window', { start: 4, lines: read, total: 40 });
		opened();
		await pressWithTheKey(1, 8);

		await userEvent.setup().click(screen.getByTestId('go-to-symbol'));
		await settled();
		await frames();

		expect(document.activeElement?.textContent?.trim()).toBe('20');
	});
});
