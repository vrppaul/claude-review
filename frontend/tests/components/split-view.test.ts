import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import FileSection from '$lib/components/FileSection.svelte';
import { diffStore } from '$lib/stores/diff.svelte';
import { commentStore } from '$lib/stores/comments.svelte';
import { addedLine, contextLine, diffFile, hunk, removedLine } from '../diff';
import { fakeServer, keepingSettings } from '../fake-server';
import { newComment } from '../new-comment';

const file = diffFile({
	path: 'src/app.ts',
	hunks: [
		hunk([
			contextLine(1, 1, 'const a = 1;'),
			removedLine(2, 'const b = 2;'),
			addedLine(2, 'const b = 3;'),
			addedLine(3, 'const c = 4;')
		])
	]
});

/** The row of the two columns that holds this text, on either side. */
function rowHolding(text: string): HTMLElement {
	const row = screen
		.getAllByTestId('split-row')
		.find((candidate) => candidate.textContent?.includes(text));
	if (!row) throw new Error(`No row holds ${text}`);
	return row;
}

/** Read the diff across two columns, as the reader chose in the settings. */
function inTwoColumns() {
	keepingSettings(fakeServer());
	diffStore.setDiffLayout('split');
}

describe('split layout', () => {
	beforeEach(() => {
		diffStore.setFiles([file], 'diff');
	});

	it('reads down one column until asked for two', () => {
		const { getByTestId, queryByTestId } = render(FileSection, { props: { file } });

		expect(getByTestId('raw-view')).toBeTruthy();
		expect(queryByTestId('split-view')).toBeNull();
	});

	it('faces the old version against the new one', () => {
		inTwoColumns();

		const { getByTestId, queryByTestId } = render(FileSection, { props: { file } });

		expect(getByTestId('split-view')).toBeTruthy();
		expect(queryByTestId('raw-view')).toBeNull();
	});

	it('shows both versions of a replaced line on one row', () => {
		inTwoColumns();

		render(FileSection, { props: { file } });
		const replaced = rowHolding('const b = 2;');

		expect(within(replaced).getByTestId('split-old-code').textContent).toContain('const b = 2;');
		expect(within(replaced).getByTestId('split-new-code').textContent).toContain('const b = 3;');
	});

	it('leaves the old side of a pure insertion empty', () => {
		inTwoColumns();

		render(FileSection, { props: { file } });
		const inserted = rowHolding('const c = 4;');

		expect(within(inserted).getByTestId('split-old-code').textContent?.trim()).toBe('');
		expect(within(inserted).getByTestId('split-new-code').textContent).toContain('const c = 4;');
	});

	it('files a comment left on the old side as a removal', async () => {
		const user = userEvent.setup();
		inTwoColumns();

		const { getByTestId } = render(FileSection, { props: { file } });
		await user.click(within(rowHolding('const b = 2;')).getByTestId('old-line-gutter'));
		await user.click(document.body);
		await user.type(getByTestId('comment-input'), 'why did this go');
		await user.click(getByTestId('save-comment'));

		expect(commentStore.comments[0].anchor).toMatchObject({ side: 'old', start_line: 2 });
	});

	it('keeps a comment made in one layout visible in the other', () => {
		commentStore.add(newComment({ file: 'src/app.ts', startLine: 2, body: 'tighten this' }));
		inTwoColumns();

		const { getByText } = render(FileSection, { props: { file } });

		expect(getByText('tighten this')).toBeTruthy();
	});

	it('shows a comment on an unchanged line once, not once per column', () => {
		// An unchanged line is the same line on both sides of the row
		commentStore.add(newComment({ file: 'src/app.ts', startLine: 1, body: 'name this' }));
		inTwoColumns();

		const { getAllByText } = render(FileSection, { props: { file } });

		expect(getAllByText('name this')).toHaveLength(1);
	});

	it('still shows a comment on each side of a replacement', () => {
		commentStore.add(newComment({ file: 'src/app.ts', side: 'old', startLine: 2, body: 'why gone' }));
		commentStore.add(newComment({ file: 'src/app.ts', side: 'new', startLine: 2, body: 'why this' }));
		inTwoColumns();

		const { getAllByText } = render(FileSection, { props: { file } });

		expect(getAllByText('why gone')).toHaveLength(1);
		expect(getAllByText('why this')).toHaveLength(1);
	});
});

describe('reaching every row from the keyboard in two columns', () => {
	const removal = diffFile({
		path: 'src/gone.ts',
		hunks: [
			hunk([
				contextLine(1, 1, 'const a = 1;'),
				removedLine(2, 'const b = 2;'),
				contextLine(3, 2, 'const c = 3;')
			])
		]
	});

	beforeEach(() => {
		diffStore.setFiles([removal], 'diff');
		inTwoColumns();
	});

	it('stops once on every row, a removed line with nothing beside it included', () => {
		const { getAllByTestId } = render(FileSection, { props: { file: removal } });

		const stops = getAllByTestId('line-gutter');

		expect(stops.map((stop) => stop.textContent?.trim())).toEqual(['1', '2', '2']);
		expect(stops[1].getAttribute('aria-label')).toBe('Comment on removed line 2');
		expect(stops.every((stop) => stop.tabIndex === 0)).toBe(true);
	});
});
