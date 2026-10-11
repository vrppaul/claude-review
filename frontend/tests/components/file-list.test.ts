import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import FileList from '$lib/components/FileList.svelte';
import { addedLine, diffFile, hunk, removedLine, wholeFile } from '../diff';
import { inReview, openReview } from '../review';

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
		const review = openReview({ files: [wholeFile('/tmp/plan.md', '# Plan')], facts: { mode: 'files' } });

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
		const unregister = review.sections.register('src/utils.ts', section);

		const { getAllByTestId } = render(FileList, inReview(review));
		await userEvent.click(getAllByTestId('file-item')[1]);

		expect(scrollIntoView).toHaveBeenCalled();
		unregister();
	});

	it('marks a file the reader has finished with', () => {
		const review = openReview({ files: diffFiles });
		review.reading.setViewed('src/handler.ts', true);

		const { getAllByTestId } = render(FileList, inReview(review));

		expect(getAllByTestId('file-viewed-mark')).toHaveLength(1);
	});

	it('says a file is viewed to whoever reads the tree aloud', () => {
		const review = openReview({ files: diffFiles });
		review.reading.setViewed('src/handler.ts', true);

		const { getByRole } = render(FileList, inReview(review));

		expect(getByRole('img', { name: 'Viewed' })).toBeTruthy();
	});

	it('counts a transcript in messages', () => {
		const review = openReview({
			files: [wholeFile('user-1', 'hello'), wholeFile('assistant-2', 'hi')],
			facts: { mode: 'transcript' }
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
		const unregister = review.sections.register('src/utils.ts', section);

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
		const review = openReview({ files: [wholeFile('user-1', 'hello')], facts: { mode: 'transcript' } });

		const { getByTestId, getByLabelText } = render(FileList, inReview(review));
		await user.type(getByTestId('file-filter'), 'nobody');

		expect(getByTestId('file-filter').getAttribute('placeholder')).toBe('Jump to a message');
		expect(getByLabelText('Find a message by its name')).toBe(getByTestId('file-filter'));
		expect(getByTestId('no-matches').textContent).toContain('No message matches');
	});

	it('keeps what was looked for, and the folders folded, while the tree is put away and brought back', async () => {
		const user = userEvent.setup();
		const review = openReview({ files: [...diffFiles, diffFile({ path: 'docs/guide.md', status: 'added' })] });
		const first = render(FileList, inReview(review));
		await user.type(first.getByTestId('file-filter'), '.');
		await user.click(first.getAllByTestId('folder-item')[0]);
		const folded = first.getAllByTestId('folder-item')[0].textContent;
		first.unmount();

		const again = render(FileList, inReview(review));

		expect((again.getByTestId('file-filter') as HTMLInputElement).value).toBe('.');
		const folder = again.getAllByTestId('folder-item').find((row) => row.textContent === folded);
		expect(folder?.getAttribute('aria-expanded')).toBe('false');
	});

	it('names its filter to whoever cannot see it', () => {
		const review = openReview({ files: diffFiles });

		const { getByLabelText, getByTestId } = render(FileList, inReview(review));

		expect(getByLabelText('Find a file by its path')).toBe(getByTestId('file-filter'));
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

		const { getAllByTestId, queryAllByTestId } = render(FileList, inReview(review));
		expect(queryAllByTestId('file-item')).toHaveLength(2);

		await user.click(getAllByTestId('folder-item')[0]);
		expect(queryAllByTestId('file-item')).toHaveLength(0);

		await user.click(getAllByTestId('folder-item')[0]);
		expect(queryAllByTestId('file-item')).toHaveLength(2);
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
