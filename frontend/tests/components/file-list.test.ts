import { describe, it, expect, vi } from 'vitest';
import { render, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import FileList from '$lib/components/FileList.svelte';
import { LINE_NUMBER_ROLE } from '$lib/dom/keyboard';
import { LINE_ROW_ROLE } from '$lib/dom/line-read-from.svelte';
import type { Review } from '$lib/review/review.svelte';
import type { NameResponse, NamesTouchedResponse, TouchedName } from '$lib/types';
import { stopsTogether } from '$lib/utils/stops';
import {
	A_LATER_TAKE,
	addedLine,
	diffFile,
	diffResponse,
	FIRST_TAKE,
	hunk,
	OF_A_CONVERSATION,
	OF_FILES,
	removedLine,
	sinceRound,
	wholeFile
} from '../diff';
import { failedCheck, failure } from '../checks';
import { fakeServer, keepingSettings } from '../fake-server';
import { frames } from '../frames';
import { inReview, openReview } from '../review';
import { settled } from '../settled';
import { storyResponse } from '../story';

const diffFiles = [
	diffFile({
		path: 'src/handler.ts',
		hunks: [hunk([addedLine(1, 'new line'), removedLine(1, 'old line')])]
	}),
	diffFile({ path: 'src/utils.ts', status: 'added' })
];

describe('the file tree', () => {
	it('counts what is being reviewed, in words', () => {
		const review = openReview({ files: diffFiles });

		const { getByTestId } = render(FileList, inReview(review));

		expect(getByTestId('sidebar-heading').textContent).toBe('2 changed files');
	});

	it('names plain files as files rather than changes', () => {
		const review = openReview({ files: [wholeFile('/tmp/plan.md', '# Plan')], facts: { where: OF_FILES } });

		const { getByTestId } = render(FileList, inReview(review));

		expect(getByTestId('sidebar-heading').textContent).toBe('1 file');
	});

	it('counts how many files are done once any are', async () => {
		const review = openReview({ files: diffFiles });
		review.reading.setViewed('src/handler.ts', true);

		const { getByTestId } = render(FileList, inReview(review));

		expect(getByTestId('sidebar-heading').textContent).toBe('2 changed files · 1 viewed');
	});

	it('names a file moved within its folder by its old name beside its new one', () => {
		const review = openReview({
			files: [diffFile({ path: 'src/handler.ts', status: 'renamed', old_path: 'src/old_handler.ts' })]
		});

		const { getByTestId } = render(FileList, inReview(review));

		const row = getByTestId('file-item').textContent?.replace(/\s+/g, ' ');
		expect(row).toContain('old_handler.ts → handler.ts');
		// The folder is the tree's to say, once, above the row
		expect(row).not.toContain('src/');
	});

	it('names a file moved from another folder by its old path', () => {
		const review = openReview({
			files: [diffFile({ path: 'src/handler.ts', status: 'renamed', old_path: 'lib/handler.ts' })]
		});

		const { getByTestId } = render(FileList, inReview(review));

		expect(getByTestId('file-item').textContent?.replace(/\s+/g, ' ')).toContain('lib/handler.ts → handler.ts');
	});

	it('lists every file', () => {
		const review = openReview({ files: diffFiles });

		const { getAllByTestId } = render(FileList, inReview(review));
		const items = getAllByTestId('file-item');

		expect(items).toHaveLength(2);
	});

	it('takes the reader to the file it names', async () => {
		const review = openReview({ files: diffFiles });
		const section = document.createElement('div');
		const scrollIntoView = vi.fn();
		section.scrollIntoView = scrollIntoView;
		const unregister = review.sections.register('src/utils.ts', 'src/utils.ts', section);

		const { getByRole } = render(FileList, inReview(review));
		await userEvent.click(getByRole('button', { name: /utils\.ts/ }));

		expect(scrollIntoView).toHaveBeenCalled();
		unregister();
	});

	it('marks a file the reader has finished with', () => {
		const review = openReview({ files: diffFiles });
		review.reading.setViewed('src/handler.ts', true);

		const { getAllByTestId } = render(FileList, inReview(review));

		expect(getAllByTestId('file-viewed-mark')).toHaveLength(1);
	});

	it('marks a file a round changed, and says since which round to whoever points at the mark', () => {
		const review = openReview({ files: diffFiles });
		review.noteRetake({ followed: 0, outdated: 0 }, { since_round: 1, base_key: 'round:1', paths: ['src/utils.ts'] });

		const { getAllByTestId } = render(FileList, inReview(review));
		const [untouched, changed] = getAllByTestId('file-item');

		expect(within(untouched).queryByTestId('file-changed-mark')).toBeNull();
		expect(within(changed).getByTestId('file-changed-mark').getAttribute('title')).toBe('Changed since round 1');
	});

	it('says a file is viewed to whoever reads the tree aloud', () => {
		const review = openReview({ files: diffFiles });
		review.reading.setViewed('src/handler.ts', true);

		const { getByRole } = render(FileList, inReview(review));

		expect(getByRole('img', { name: 'Viewed' })).toBeTruthy();
	});

	it('says what became of each file in a word, to whoever cannot see the letter that says it', () => {
		const review = openReview({ files: diffFiles });

		const { getAllByTestId } = render(FileList, inReview(review));
		const [changed, made] = getAllByTestId('file-item');

		expect(within(changed).getByText('modified')).toBeTruthy();
		expect(within(made).getByText('added')).toBeTruthy();
	});

	it('says nothing became of a plain file, which is no change', () => {
		const review = openReview({ files: [wholeFile('/tmp/plan.md', '# Plan')], facts: { where: OF_FILES } });

		const { getByTestId } = render(FileList, inReview(review));

		expect(within(getByTestId('file-item')).queryByText('added')).toBeNull();
	});

	it('counts a transcript in messages', () => {
		const review = openReview({
			files: [wholeFile('user-1', 'hello'), wholeFile('assistant-2', 'hi')],
			facts: { where: OF_A_CONVERSATION }
		});

		const { getByTestId, getAllByTestId } = render(FileList, inReview(review));

		expect(getByTestId('sidebar-heading').textContent).toBe('2 messages');
		expect(getAllByTestId('file-item')).toHaveLength(2);
	});
});

describe('finding a file in a long review', () => {
	it('narrows the list to paths that match', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: diffFiles });

		const { getByTestId, getAllByTestId } = render(FileList, inReview(review));
		await user.type(getByTestId('file-filter'), 'utils');

		const items = getAllByTestId('file-item');
		expect(items).toHaveLength(1);
		expect(items[0].textContent).toContain('utils.ts');
	});

	it('goes to the first file the filter leaves when the reader presses Enter', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: diffFiles });
		const section = document.createElement('div');
		section.scrollIntoView = vi.fn();
		const unregister = review.sections.register('src/utils.ts', 'src/utils.ts', section);

		const { getByTestId } = render(FileList, inReview(review));
		await user.type(getByTestId('file-filter'), 'utils{Enter}');

		expect(section.scrollIntoView).toHaveBeenCalled();
		unregister();
	});

	it('hands the keyboard to the first file the filter leaves on the down arrow', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: diffFiles });

		const { getByTestId, getAllByTestId } = render(FileList, inReview(review));
		await user.type(getByTestId('file-filter'), 'utils{ArrowDown}');

		expect(document.activeElement).toBe(getAllByTestId('file-item')[0]);
		expect(getAllByTestId('file-item')[0].textContent).toContain('utils.ts');
	});

	it('looks for messages, not files, in a transcript', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: [wholeFile('user-1', 'hello')], facts: { where: OF_A_CONVERSATION } });

		const { getByTestId, getByLabelText } = render(FileList, inReview(review));
		await user.type(getByTestId('file-filter'), 'nobody');

		expect(getByTestId('file-filter').getAttribute('placeholder')).toBe('Jump to a message');
		expect(getByLabelText('Find a message by its name')).toBe(getByTestId('file-filter'));
		expect(getByTestId('no-matches').textContent).toContain('No message matches');
	});

	it('keeps what was looked for, and the folders folded, while the tree is put away and brought back', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: [...diffFiles, diffFile({ path: 'docs/guide.md', status: 'added' })] });
		const { getByTestId, getByRole, getAllByTestId } = render(FileList, inReview(review));
		await user.type(getByTestId('file-filter'), '.');
		await user.click(getByRole('button', { name: 'src/' }));
		const folded = getByRole('button', { name: 'src/' }).textContent;

		await user.click(getByTestId('hide-sidebar'));
		await user.click(getByTestId('show-sidebar'));

		expect((getByTestId('file-filter') as HTMLInputElement).value).toBe('.');
		const folder = getAllByTestId('folder-item').find((row) => row.textContent === folded);
		expect(folder?.getAttribute('aria-expanded')).toBe('false');
	});

	it('names its filter to whoever cannot see it', () => {
		const review = openReview({ files: diffFiles });

		const { getByLabelText, getByTestId } = render(FileList, inReview(review));

		expect(getByLabelText('Find a file by its path')).toBe(getByTestId('file-filter'));
	});

	it('says the diff holds no file when it holds none, rather than that none matches an empty filter', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: [] });

		const { getByTestId, queryByTestId } = render(FileList, inReview(review));
		expect(getByTestId('no-files').textContent?.trim()).toBe('No changed files.');
		await user.type(getByTestId('file-filter'), 'zzz');

		expect(getByTestId('no-files').textContent?.trim()).toBe('No changed files.');
		expect(queryByTestId('no-matches')).toBeNull();
	});

	it('says so when nothing matches', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: diffFiles });

		const { getByTestId, queryAllByTestId } = render(FileList, inReview(review));
		await user.type(getByTestId('file-filter'), 'zzz');

		expect(queryAllByTestId('file-item')).toHaveLength(0);
		expect(getByTestId('no-matches')).toBeTruthy();
	});

	it('reports how many of the files are showing while filtering', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: diffFiles });

		const { getByTestId } = render(FileList, inReview(review));
		await user.type(getByTestId('file-filter'), 'utils');

		expect(getByTestId('sidebar-heading').textContent).toBe('1 of 2');
	});

	it('draws a chain of folders that each hold one folder as one row', () => {
		const review = openReview({
			files: [diffFile({ path: 'src/lib/components/one.ts' }), diffFile({ path: 'src/lib/components/two.ts' })]
		});

		const { getAllByTestId } = render(FileList, inReview(review));

		expect(getAllByTestId('folder-item').map((folder) => folder.textContent?.trim())).toEqual(['src/lib/components/']);
	});

	it('folds a directory away and back', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: diffFiles });

		const { getByRole, queryAllByTestId } = render(FileList, inReview(review));
		expect(queryAllByTestId('file-item')).toHaveLength(2);

		await user.click(getByRole('button', { name: 'src/' }));
		expect(queryAllByTestId('file-item')).toHaveLength(0);

		await user.click(getByRole('button', { name: 'src/' }));
		expect(queryAllByTestId('file-item')).toHaveLength(2);
	});
});

describe('putting the tree away', () => {
	it('leaves a rail where it stood, which brings it back', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: diffFiles });
		const { getByTestId, queryByTestId } = render(FileList, inReview(review));

		await user.click(getByTestId('hide-sidebar'));
		expect(queryByTestId('sidebar')).toBeNull();

		await user.click(getByTestId('show-sidebar'));
		expect(getByTestId('sidebar')).toBeTruthy();
		expect(queryByTestId('show-sidebar')).toBeNull();
	});

	it('says by name what each way does: to put the file tree away, and to bring it back', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: diffFiles });
		const { getByRole, getByTestId } = render(FileList, inReview(review));
		expect(getByRole('button', { name: 'Put the file tree away' })).toBe(getByTestId('hide-sidebar'));

		await user.click(getByTestId('hide-sidebar'));

		expect(getByRole('button', { name: 'Show the file tree' })).toBe(getByTestId('show-sidebar'));
	});

	it('counts the files of the change on the rail it leaves', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: diffFiles });
		const { getByTestId } = render(FileList, inReview(review));

		await user.click(getByTestId('hide-sidebar'));

		expect(getByTestId('sidebar-rail-count').textContent).toBe(String(diffFiles.length));
	});

	it('leaves the rail where the tour looks for the tree', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: diffFiles });
		const { getByTestId } = render(FileList, inReview(review));

		await user.click(getByTestId('hide-sidebar'));

		expect(getByTestId('show-sidebar').dataset.tour).toBe('file-tree');
	});
});

describe('sizing the tree', () => {
	it('widens it a step at a time with the arrow keys, rightward being wider', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: diffFiles });
		const before = review.layout.fileTree.width;

		const { getByTestId } = render(FileList, inReview(review));
		getByTestId('sidebar-resize').focus();
		await user.keyboard('{ArrowRight}');

		expect(review.layout.fileTree.width).toBeGreaterThan(before);
		await user.keyboard('{ArrowLeft}');
		expect(review.layout.fileTree.width).toBe(before);
	});
});

describe('where the checks failed, in the tree', () => {
	it('says on a file’s row how many places the checks failed in it, and nothing on a file they did not', () => {
		const failedIn = [failure({ path: 'src/a.py', line: 3 }), failure({ path: 'src/a.py', line: 9 })];
		const review = openReview({
			files: [diffFile({ path: 'src/a.py' }), diffFile({ path: 'src/b.py' })],
			facts: { checks: [failedCheck(failedIn, { name: 'pytest' }), failedCheck([failure({ path: 'src/a.py' })])] }
		});

		const { getAllByTestId } = render(FileList, inReview(review));

		expect(getAllByTestId('file-failures').map((mark) => mark.textContent.replace(/\s+/g, ' ').trim())).toEqual([
			'3 3 places the checks failed'
		]);
	});

	it('says the places in a file are out of date once every check that found them is, though the file did not change', () => {
		const review = openReview({
			files: [diffFile({ path: 'src/a.py' })],
			facts: {
				checks: [failedCheck([failure({ path: 'src/a.py' })], { changed_since: ['src/b.py'], out_of_date: true })]
			}
		});

		const { getByTestId } = render(FileList, inReview(review));

		expect(getByTestId('file-failures').textContent).toContain('1 place the checks failed, out of date');
	});
});

describe('the names the change touched, under their files', () => {
	const HANDLER = 'src/handler.ts';
	const handle: TouchedName = {
		name: 'handle',
		defined_as: 'function',
		change: 'modified',
		side: 'new',
		line: 4,
		column: 16,
		stands_on: [
			{ side: 'new', first: 4, last: 9 },
			{ side: 'old', first: 4, last: 11 }
		]
	};
	const retired: TouchedName = {
		name: 'Retired',
		defined_as: 'class',
		change: 'removed',
		side: 'old',
		line: 12,
		column: 6,
		stands_on: [{ side: 'old', first: 12, last: 20 }]
	};
	const namesOfHandler: NamesTouchedResponse = {
		take: FIRST_TAKE,
		files: [{ path: HANDLER, names: [handle, retired] }]
	};
	// What the review answers of handle: defined where the tree says, used nowhere
	const HANDLE_LOOKED_UP: NameResponse = {
		name: 'handle',
		places: [
			{
				path: HANDLER,
				line: 4,
				column: 16,
				text: 'export function handle() {',
				defined_as: 'function',
				inside: null,
				added: true,
				found_as: 'name'
			}
		]
	};

	/** A section of a file as an area draws it: the file, and what is drawn in it from the top down. */
	interface DrawnSection {
		path: string;
		drawn: HTMLElement[];
	}

	/** The row of a line, its number carrying the key the line's place is known by. */
	function lineRow(lineKey: string): HTMLElement {
		const row = document.createElement('div');
		const number = document.createElement('button');
		row.dataset.role = LINE_ROW_ROLE;
		number.dataset.role = LINE_NUMBER_ROLE;
		number.dataset.place = lineKey;
		row.append(number);
		return row;
	}

	// What the area the sections are drawn in is known by, and where a line scrolled up out of it stands in the window
	const READING_AREA = 'reading-area';
	const ABOVE_THE_AREA = new DOMRect(0, -40, 10, 20);

	/** Sections drawn in a watched area, the first on the page the one being read, and what stands where the reader reads from. */
	function readingAt(review: Review, sections: DrawnSection[], atSpot: Element): () => void {
		const area = document.createElement('div');
		area.dataset.testid = READING_AREA;
		const unregister = sections.map(({ path, drawn }) => {
			const section = document.createElement('div');
			section.append(...drawn);
			area.append(section);
			return review.sections.register(path, path, section);
		});
		document.body.append(area);
		Object.defineProperty(document, 'elementFromPoint', { configurable: true, value: () => atSpot });
		return stopsTogether(...unregister, review.sections.watchInView(area), () => area.remove());
	}

	it('lists under each file the names it touched, what became of each said in a word', async () => {
		fakeServer().answer('GET /api/names-touched', namesOfHandler);
		const review = openReview({ files: diffFiles });

		const { findAllByTestId } = render(FileList, inReview(review));
		const [modified, removed] = await findAllByTestId('name-item');

		expect(modified.textContent?.replace(/\s+/g, ' ').trim()).toBe('M modified handle()');
		expect(removed.textContent?.replace(/\s+/g, ' ').trim()).toBe('D removed Retired');
	});

	it('folds a file’s names by the chevron at its row’s end, the row itself still going to the file', async () => {
		const user = userEvent.setup();
		fakeServer().answer('GET /api/names-touched', namesOfHandler);
		const review = openReview({ files: diffFiles });
		const section = document.createElement('div');
		section.scrollIntoView = vi.fn();
		const unregister = review.sections.register(HANDLER, HANDLER, section);

		const { findAllByTestId, getByRole, queryAllByTestId } = render(FileList, inReview(review));
		await findAllByTestId('name-item');
		await user.click(getByRole('button', { name: 'Fold its names' }));
		await user.click(getByRole('button', { name: /handler\.ts/ }));

		expect(queryAllByTestId('name-item')).toHaveLength(0);
		expect(getByRole('button', { name: 'Show its names' }).getAttribute('aria-expanded')).toBe('false');
		expect(section.scrollIntoView).toHaveBeenCalled();
		unregister();
	});

	it('keeps the keyboard on a file’s row as its names arrive under it', async () => {
		const names = fakeServer().hold('GET /api/names-touched');
		const review = openReview({ files: diffFiles });

		const { findAllByTestId, getAllByTestId } = render(FileList, inReview(review));
		await vi.waitFor(() => expect(names.requests).toHaveLength(1));
		const row = getAllByTestId('file-item')[0];
		row.focus();
		names.answer(0, namesOfHandler);
		await findAllByTestId('name-item');

		expect(document.activeElement).toBe(row);
	});

	it.each([
		{
			what: 'another reading of the diff, its names on their way',
			takeOut: (review: Review) => review.setIgnoreWhitespace(true)
		},
		{ what: 'its file’s names folded', takeOut: (review: Review) => review.layout.fileTree.toggleNames(HANDLER) },
		{ what: 'the names turned off', takeOut: (review: Review) => review.layout.fileTree.toggleNamesListed() },
		{ what: 'a filter it does not answer', takeOut: (review: Review) => review.layout.fileTree.setFilter('retir') }
	])('hands the keyboard on a name’s row to its file’s row as $what takes the row out', async ({ takeOut }) => {
		const server = fakeServer();
		const names = server.hold('GET /api/names-touched');
		keepingSettings(server);
		server.answer('GET /api/diff', diffResponse({ files: diffFiles, take: FIRST_TAKE }));
		const review = openReview({ files: diffFiles });
		const { findAllByTestId, getAllByTestId } = render(FileList, inReview(review));
		await vi.waitFor(() => expect(names.requests).toHaveLength(1));
		names.answer(0, namesOfHandler);
		const [modified] = await findAllByTestId('name-item');
		modified.focus();

		await takeOut(review);
		await settled();

		expect(document.activeElement).toBe(getAllByTestId('file-item')[0]);
	});

	it('finds a name under a file whose path does not answer, only the names that do, and lights what answered', async () => {
		const user = userEvent.setup();
		fakeServer().answer('GET /api/names-touched', namesOfHandler);
		const review = openReview({ files: diffFiles });

		const { findAllByTestId, getAllByTestId, getByTestId } = render(FileList, inReview(review));
		await findAllByTestId('name-item');
		await user.type(getByTestId('file-filter'), 'RETIR');

		expect(getAllByTestId('file-item').map((row) => row.textContent?.includes('handler.ts'))).toEqual([true]);
		expect(getAllByTestId('name-item').map((row) => row.textContent?.replace(/\s+/g, ' ').trim())).toEqual([
			'D removed Retired'
		]);
		expect(getByTestId('name-sought').textContent).toBe('Retir');
		expect(getByTestId('sidebar-heading').textContent).toBe('1 of 2');
	});

	it('keeps every name under a file whose path answers, as well as a name does', async () => {
		const user = userEvent.setup();
		fakeServer().answer('GET /api/names-touched', namesOfHandler);
		const review = openReview({ files: diffFiles });

		const { findAllByTestId, getAllByTestId, getByTestId } = render(FileList, inReview(review));
		await findAllByTestId('name-item');
		await user.type(getByTestId('file-filter'), 'handle');

		expect(getAllByTestId('name-item')).toHaveLength(2);
		expect(getByTestId('name-sought').textContent).toBe('handle');
	});

	it('says no file or name matches, in a field that finds either', async () => {
		const user = userEvent.setup();
		fakeServer().answer('GET /api/names-touched', namesOfHandler);
		const review = openReview({ files: diffFiles });

		const { findAllByTestId, getByTestId } = render(FileList, inReview(review));
		await findAllByTestId('name-item');
		await user.type(getByTestId('file-filter'), 'zzz');

		expect(getByTestId('file-filter').getAttribute('placeholder')).toBe('Find a file or name');
		expect(getByTestId('no-matches').textContent?.trim()).toBe('No file or name matches “zzz”.');
	});

	it('lists the files alone once the reader turns the names off, the filter then finding files alone', async () => {
		const user = userEvent.setup();
		fakeServer().answer('GET /api/names-touched', namesOfHandler);
		const review = openReview({ files: diffFiles });

		const { findAllByTestId, getByRole, getByTestId, queryAllByTestId } = render(FileList, inReview(review));
		await findAllByTestId('name-item');
		await user.click(getByRole('button', { name: 'List the names under each file' }));
		await user.type(getByTestId('file-filter'), 'retir');

		expect(queryAllByTestId('name-item')).toHaveLength(0);
		expect(getByRole('button', { name: 'List the names under each file' }).getAttribute('aria-pressed')).toBe('false');
		expect(getByTestId('file-filter').getAttribute('placeholder')).toBe('Jump to a file');
		expect(getByTestId('no-matches').textContent?.trim()).toBe('No file matches “retir”.');
	});

	it('offers no way to list names where the diff on screen has none', async () => {
		fakeServer().answer('GET /api/names-touched', { take: FIRST_TAKE, files: [] });
		const review = openReview({ files: diffFiles });

		const { queryByRole } = render(FileList, inReview(review));
		await settled();

		expect(queryByRole('button', { name: /names under each file/ })).toBeNull();
	});

	it('takes the reader to where a name is defined, on the side its lines are numbered on', async () => {
		const user = userEvent.setup();
		fakeServer().answer('GET /api/names-touched', namesOfHandler);
		const review = openReview({ files: diffFiles });
		const goToLine = vi.spyOn(review.navigator, 'goToLine').mockResolvedValue();

		const { findAllByTestId } = render(FileList, inReview(review));
		const [modified, removed] = await findAllByTestId('name-item');
		await user.click(modified);
		await user.click(removed);

		expect(goToLine.mock.calls).toEqual([
			[HANDLER, { side: 'new', number: 4 }, { column: 16, name: 'handle' }],
			[HANDLER, { side: 'old', number: 12 }, { column: 6, name: 'Retired' }]
		]);
	});

	it('marks the name the reader is in as where they are, in place of its file', async () => {
		fakeServer().answer('GET /api/names-touched', namesOfHandler);
		const review = openReview({ files: diffFiles });
		const row = lineRow('old:15');
		const stop = readingAt(review, [{ path: HANDLER, drawn: [row] }], row);

		const { findAllByTestId, getAllByTestId } = render(FileList, inReview(review));
		const [modified, removed] = await findAllByTestId('name-item');
		await frames(1);

		expect(removed.getAttribute('aria-current')).toBe('true');
		expect(modified.getAttribute('aria-current')).toBeNull();
		expect(getAllByTestId('file-item')[0].getAttribute('aria-current')).toBeNull();
		stop();
	});

	it('marks a modified name as where the reader is on a line the change removed from it', async () => {
		fakeServer().answer('GET /api/names-touched', namesOfHandler);
		const review = openReview({ files: diffFiles });
		const row = lineRow('old:10');
		const stop = readingAt(review, [{ path: HANDLER, drawn: [row] }], row);

		const { findAllByTestId } = render(FileList, inReview(review));
		const [modified] = await findAllByTestId('name-item');
		await frames(1);

		expect(modified.getAttribute('aria-current')).toBe('true');
		stop();
	});

	it('keeps the name the reader is in as where they are while a card under one of its lines stands there', async () => {
		fakeServer().answer('GET /api/names-touched', namesOfHandler);
		const review = openReview({ files: diffFiles });
		const card = document.createElement('div');
		const words = document.createElement('p');
		card.append(words);
		const stop = readingAt(review, [{ path: HANDLER, drawn: [lineRow('new:5'), card] }], words);

		const { findAllByTestId } = render(FileList, inReview(review));
		const [modified] = await findAllByTestId('name-item');
		await frames(1);

		expect(modified.getAttribute('aria-current')).toBe('true');
		stop();
	});

	it('marks no name of the file in view by a line of another file read from', async () => {
		fakeServer().answer('GET /api/names-touched', namesOfHandler);
		const review = openReview({ files: diffFiles });
		const row = lineRow('new:5');
		const stop = readingAt(
			review,
			[
				{ path: HANDLER, drawn: [] },
				{ path: 'src/utils.ts', drawn: [row] }
			],
			row
		);

		const { findAllByTestId, getAllByTestId } = render(FileList, inReview(review));
		const [modified] = await findAllByTestId('name-item');
		await frames(1);

		expect(modified.getAttribute('aria-current')).toBeNull();
		expect(getAllByTestId('file-item')[0].getAttribute('aria-current')).toBe('true');
		stop();
	});

	it('marks the file as where the reader is while they read a line of no name in it', async () => {
		fakeServer().answer('GET /api/names-touched', namesOfHandler);
		const review = openReview({ files: diffFiles });
		const row = lineRow('new:2');
		const stop = readingAt(review, [{ path: HANDLER, drawn: [row] }], row);

		const { findAllByTestId, getAllByTestId } = render(FileList, inReview(review));
		await findAllByTestId('name-item');
		await frames(1);

		expect(getAllByTestId('file-item')[0].getAttribute('aria-current')).toBe('true');
		stop();
	});

	it('marks the name of the line the reader was taken to as where they are, though the file above stands at the top', async () => {
		fakeServer().answer('GET /api/names-touched', namesOfHandler);
		const review = openReview({ files: diffFiles });
		const atTheTop = lineRow('new:2');
		const stop = readingAt(
			review,
			[
				{ path: 'src/utils.ts', drawn: [atTheTop] },
				{ path: HANDLER, drawn: [lineRow('new:2'), lineRow('old:12')] }
			],
			atTheTop
		);

		const { findAllByTestId, getAllByTestId } = render(FileList, inReview(review));
		const [, removed] = await findAllByTestId('name-item');
		await frames(1);
		review.sections.goToLine(HANDLER, { line: 'old:12', name: { column: 6, name: 'Retired' } });
		await settled();

		expect(removed.getAttribute('aria-current')).toBe('true');
		expect(getAllByTestId('file-item').map((row) => row.getAttribute('aria-current'))).toEqual([null, null]);
		stop();
	});

	it('marks the file at the top as where the reader is once they scroll the line they were taken to out of sight', async () => {
		fakeServer().answer('GET /api/names-touched', namesOfHandler);
		const review = openReview({ files: diffFiles });
		const atTheTop = lineRow('new:2');
		const takenTo = lineRow('old:12');
		const stop = readingAt(
			review,
			[
				{ path: 'src/utils.ts', drawn: [atTheTop] },
				{ path: HANDLER, drawn: [lineRow('new:2'), takenTo] }
			],
			atTheTop
		);

		const { findAllByTestId, getAllByTestId, getByTestId } = render(FileList, inReview(review));
		const [, removed] = await findAllByTestId('name-item');
		await frames(1);
		review.sections.goToLine(HANDLER, { line: 'old:12', name: { column: 6, name: 'Retired' } });
		await settled();
		vi.spyOn(within(takenTo).getByRole('button'), 'getBoundingClientRect').mockReturnValue(ABOVE_THE_AREA);
		getByTestId(READING_AREA).dispatchEvent(new Event('scroll'));
		await frames(1);

		expect(removed.getAttribute('aria-current')).toBeNull();
		expect(getAllByTestId('file-item').map((row) => row.getAttribute('aria-current'))).toEqual([null, 'true']);
		stop();
	});

	it('hands the keyboard on the chevron that folds a file’s names to the file’s row as the names go', async () => {
		const server = fakeServer();
		const names = server.hold('GET /api/names-touched');
		keepingSettings(server);
		server.answer('GET /api/diff', diffResponse({ files: diffFiles, take: FIRST_TAKE }));
		const review = openReview({ files: diffFiles });
		const { findAllByTestId, getAllByTestId, getByTestId } = render(FileList, inReview(review));
		await vi.waitFor(() => expect(names.requests).toHaveLength(1));
		names.answer(0, namesOfHandler);
		await findAllByTestId('name-item');
		getByTestId('file-item-names-fold').focus();

		await review.setIgnoreWhitespace(true);
		await settled();

		expect(document.activeElement).toBe(getAllByTestId('file-item')[0]);
	});

	it('draws no names of a diff read another way, until those of it arrive', async () => {
		const server = fakeServer();
		const names = server.hold('GET /api/names-touched');
		keepingSettings(server);
		server.answer('GET /api/diff', diffResponse({ files: diffFiles, take: FIRST_TAKE }));
		const review = openReview({ files: diffFiles });

		const { findAllByTestId, queryAllByTestId } = render(FileList, inReview(review));
		await vi.waitFor(() => expect(names.requests).toHaveLength(1));
		names.answer(0, namesOfHandler);
		await findAllByTestId('name-item');
		await review.setIgnoreWhitespace(true);

		expect(queryAllByTestId('name-item')).toHaveLength(0);
		await vi.waitFor(() => expect(names.requests).toHaveLength(2));
		names.answer(1, namesOfHandler);
		expect(await findAllByTestId('name-item')).toHaveLength(2);
		expect(names.requests[1].query.ignore_whitespace).toBe('true');
	});

	it('asks the review about a name by its place at the icon at its row’s end, and opens the lookup by it', async () => {
		const user = userEvent.setup();
		const server = fakeServer();
		server.answer('GET /api/names-touched', namesOfHandler);
		server.answer('GET /api/name', HANDLE_LOOKED_UP);
		const review = openReview({ files: diffFiles });

		const { findAllByTestId, getByTestId } = render(FileList, inReview(review));
		await user.click((await findAllByTestId('name-look-up'))[0]);
		await settled();

		expect(server.requestsTo('GET /api/name').map((request) => request.query)).toEqual([
			{ path: HANDLER, side: 'new', line: '4', column: '16' }
		]);
		expect(getByTestId('name-lookup-heading').textContent).toBe('handle');
		expect(getByTestId('name-lookup-count').textContent).toBe('1 definition, 0 uses');
	});

	it('says the change removed a name it removed that nothing in the code is called now', async () => {
		const user = userEvent.setup();
		const server = fakeServer();
		server.answer('GET /api/names-touched', namesOfHandler);
		server.answer('GET /api/name', { name: 'Retired', places: [] });
		const review = openReview({ files: diffFiles });

		const { findAllByTestId, getByTestId } = render(FileList, inReview(review));
		await user.click((await findAllByTestId('name-look-up'))[1]);
		await settled();

		expect(getByTestId('name-lookup-nothing').textContent?.replace(/\s+/g, ' ').trim()).toBe(
			'Nothing in the code is called “Retired” now: the change removed it.'
		);
	});

	it('says at the foot of the pane opened from the tree how to open it from the code', async () => {
		const user = userEvent.setup();
		const server = fakeServer();
		server.answer('GET /api/names-touched', namesOfHandler);
		server.answer('GET /api/name', HANDLE_LOOKED_UP);
		const review = openReview({ files: diffFiles });

		const { findAllByTestId, getByTestId } = render(FileList, inReview(review));
		await user.click((await findAllByTestId('name-look-up'))[0]);
		await settled();

		expect(getByTestId('name-lookup-foot').textContent?.replace(/\s+/g, ' ').trim()).toBe(
			'Ctrl+click on any name in the code opens this.'
		);
	});

	it('gives the keyboard back to the icon as the pane closes at Escape', async () => {
		const user = userEvent.setup();
		const server = fakeServer();
		server.answer('GET /api/names-touched', namesOfHandler);
		server.answer('GET /api/name', HANDLE_LOOKED_UP);
		const review = openReview({ files: diffFiles });

		const { findAllByTestId, queryByTestId } = render(FileList, inReview(review));
		const [icon] = await findAllByTestId('name-look-up');
		await user.click(icon);
		await settled();
		await user.keyboard('{Escape}');
		await settled();

		expect([queryByTestId('name-lookup'), document.activeElement]).toEqual([null, icon]);
	});

	it('closes at a second press on its icon, asking nothing again', async () => {
		const user = userEvent.setup();
		const server = fakeServer();
		server.answer('GET /api/names-touched', namesOfHandler);
		server.answer('GET /api/name', HANDLE_LOOKED_UP);
		const review = openReview({ files: diffFiles });

		const { findAllByTestId, queryByTestId } = render(FileList, inReview(review));
		const [icon] = await findAllByTestId('name-look-up');
		await user.click(icon);
		await settled();
		await user.click(icon);
		await settled();

		expect(queryByTestId('name-lookup')).toBeNull();
		expect(server.requestsTo('GET /api/name')).toHaveLength(1);
	});

	it('closes once the tree is scrolled until its icon is out of sight, the keyboard back on the icon', async () => {
		const user = userEvent.setup();
		const server = fakeServer();
		server.answer('GET /api/names-touched', namesOfHandler);
		server.answer('GET /api/name', HANDLE_LOOKED_UP);
		const review = openReview({ files: diffFiles });
		const { findAllByTestId, queryByTestId } = render(FileList, inReview(review));
		const [icon] = await findAllByTestId('name-look-up');
		await user.click(icon);
		await settled();

		icon.getBoundingClientRect = () => new DOMRect(0, -window.innerHeight, icon.offsetWidth, icon.offsetHeight);
		await frames();
		await settled();

		expect([queryByTestId('name-lookup'), document.activeElement]).toEqual([null, icon]);
	});

	it('closes once the change is taken again, its row gone until the names of the take come, the keyboard on its file', async () => {
		const user = userEvent.setup();
		const server = fakeServer();
		server.answer('GET /api/names-touched', namesOfHandler);
		server.answer('GET /api/name', HANDLE_LOOKED_UP);
		const review = openReview({ files: diffFiles });
		const { findAllByTestId, getAllByTestId, queryByTestId } = render(FileList, inReview(review));
		await user.click((await findAllByTestId('name-look-up'))[0]);
		await settled();

		server.hold('GET /api/names-touched');
		server.answer('POST /api/anchors/follow', { anchors: [] });
		server.answer('GET /api/diff', diffResponse({ files: diffFiles, take: A_LATER_TAKE }));
		server.answer('GET /api/story', storyResponse());
		await review.takeRetakenDiff();
		await frames();
		await settled();

		expect(queryByTestId('name-lookup')).toBeNull();
		expect(document.activeElement).toBe(getAllByTestId('file-item')[0]);
	});

	it('offers no lookup of a removed name while the diff on screen is read against another base', async () => {
		const server = fakeServer();
		server.answer('GET /api/names-touched', namesOfHandler);
		const review = openReview({ files: diffFiles });
		server.answer('GET /api/diff', diffResponse({ files: diffFiles, base: sinceRound(1) }));
		await review.diff.setBase('round:1');

		const { findAllByTestId, queryByRole } = render(FileList, inReview(review));
		await findAllByTestId('name-item');

		expect(queryByRole('button', { name: 'Where handle is defined and used' })).not.toBeNull();
		expect(queryByRole('button', { name: 'Where Retired is defined and used' })).toBeNull();
	});

	it('asks for no names in a review of files, which has no change to a repository’s code', () => {
		const server = fakeServer();
		const review = openReview({ files: [wholeFile('/tmp/plan.md', '# Plan')], facts: { where: OF_FILES } });

		render(FileList, inReview(review));

		expect(server.requestsTo('GET /api/names-touched')).toHaveLength(0);
	});
});
