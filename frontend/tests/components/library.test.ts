import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { userEvent } from '@testing-library/user-event';
import Button from '$lib/ui/Button.svelte';
import ColumnRail from '$lib/ui/ColumnRail.svelte';
import Heading from '$lib/ui/Heading.svelte';
import IconButton from '$lib/ui/IconButton.svelte';
import Link from '$lib/ui/Link.svelte';
import Row from '$lib/ui/Row.svelte';
import Segment from '$lib/ui/Segment.svelte';
import Segmented from '$lib/ui/Segmented.svelte';
import Chip from '$lib/ui/Chip.svelte';
import Count from '$lib/ui/Count.svelte';
import Dot from '$lib/ui/Dot.svelte';
import Key from '$lib/ui/Key.svelte';

// What a test hands the library's parts to draw inside them, and what it finds each by
const WORDS = 'Show the whole diff';
const drawn = createRawSnippet(() => ({ render: () => `<span>${WORDS}</span>` }));
const TEST_ID = 'drawn';
const RELEASE = 'https://github.com/pavelparanin/claude-review/releases';
// How many threads a count says hang on what it stands beside
const THREADS = 3;
// What a chip's cross says it does
const REMOVING = 'Take this thread out of the message';
// Keys held together, as the help writes them
const CHORD = 'Ctrl+Enter';

describe('the component library', () => {
	it('draws a button with the words it is handed, and does what it does when pressed', async () => {
		const onclick = vi.fn();
		const { getByTestId } = render(Button, {
			tone: 'primary',
			size: 'sm',
			testId: TEST_ID,
			onclick,
			children: drawn
		});

		await userEvent.click(getByTestId(TEST_ID));

		expect(getByTestId(TEST_ID).textContent).toBe(WORDS);
		expect(onclick).toHaveBeenCalledOnce();
	});

	it('says what an icon button does to whoever cannot see its icon, and under the pointer', () => {
		const { getByTestId } = render(IconButton, {
			tone: 'quiet',
			size: 'xs',
			shape: 'square',
			label: WORDS,
			testId: TEST_ID,
			children: drawn
		});

		expect(getByTestId(TEST_ID).getAttribute('aria-label')).toBe(WORDS);
		expect(getByTestId(TEST_ID).getAttribute('title')).toBe(WORDS);
	});

	it('leads a link outside the review in a tab of its own, telling the page it opens nothing of the review', () => {
		const { getByTestId } = render(Link, { href: RELEASE, testId: TEST_ID, children: drawn });

		expect(getByTestId(TEST_ID).getAttribute('href')).toBe(RELEASE);
		expect(getByTestId(TEST_ID).getAttribute('target')).toBe('_blank');
		expect(getByTestId(TEST_ID).getAttribute('rel')).toBe('noopener noreferrer');
	});

	it('draws a link that does something in place as a button, which does it when pressed', async () => {
		const onclick = vi.fn();
		const { getByTestId } = render(Link, { onclick, testId: TEST_ID, children: drawn });

		await userEvent.click(getByTestId(TEST_ID));

		expect(getByTestId(TEST_ID).tagName).toBe('BUTTON');
		expect(onclick).toHaveBeenCalledOnce();
	});

	it('says a segment is pressed to whoever cannot see it', () => {
		const { getByTestId } = render(Segment, { pressed: true, testId: TEST_ID, children: drawn });

		expect(getByTestId(TEST_ID).getAttribute('aria-pressed')).toBe('true');
	});

	it('names a segmented control to whoever cannot see what its segments pick between', () => {
		const { getByTestId } = render(Segmented, { label: WORDS, testId: TEST_ID, children: drawn });

		expect(getByTestId(TEST_ID).getAttribute('role')).toBe('group');
		expect(getByTestId(TEST_ID).getAttribute('aria-label')).toBe(WORDS);
	});

	it('draws a chip that names a way somewhere as a button, which takes the reader there when pressed', async () => {
		const onclick = vi.fn();
		const { getByTestId } = render(Chip, { voice: 'agent', onclick, testId: TEST_ID, children: drawn });

		await userEvent.click(getByTestId(TEST_ID));

		expect(getByTestId(TEST_ID).tagName).toBe('BUTTON');
		expect(onclick).toHaveBeenCalledOnce();
	});

	it('takes a chip out of what is being written by its own cross, which says so', async () => {
		const onRemove = vi.fn();
		const { getByTestId } = render(Chip, {
			voice: 'reader',
			removing: REMOVING,
			onRemove,
			testId: TEST_ID,
			children: drawn
		});

		await userEvent.click(getByTestId(`${TEST_ID}-remove`));

		expect(getByTestId(`${TEST_ID}-remove`).getAttribute('aria-label')).toBe(REMOVING);
		expect(onRemove).toHaveBeenCalledOnce();
	});

	it('draws a chip whose name is out of reach as words, with nothing to press', () => {
		const { getByTestId } = render(Chip, { voice: 'agent', outOfReach: true, testId: TEST_ID, children: drawn });

		expect(getByTestId(TEST_ID).textContent).toBe(WORDS);
		expect(getByTestId(TEST_ID).querySelector('button')).toBeNull();
		expect(getByTestId(TEST_ID).tagName).toBe('SPAN');
	});

	it('leaves a dot unsaid to whoever cannot see it: the words beside it say what it marks', () => {
		const { getByTestId } = render(Dot, { tone: 'unread', testId: TEST_ID });

		expect(getByTestId(TEST_ID).getAttribute('aria-hidden')).toBe('true');
	});

	it('shows what a dot marks under the pointer, where it is handed the words', () => {
		const { getByTestId } = render(Dot, { tone: 'reader', title: WORDS, testId: TEST_ID });

		expect(getByTestId(TEST_ID).getAttribute('title')).toBe(WORDS);
	});

	it('leaves a count unsaid to whoever cannot see it, where the name of what it stands in says how many', () => {
		const { getByTestId } = render(Count, { count: THREADS, 'aria-hidden': true, testId: TEST_ID });

		expect(getByTestId(TEST_ID).getAttribute('aria-hidden')).toBe('true');
	});

	it('says a key is a key of the keyboard, to whoever cannot see its box', () => {
		const { getByTestId } = render(Key, { keys: CHORD, stands: 'inline', testId: TEST_ID });

		expect(getByTestId(TEST_ID).tagName).toBe('KBD');
		expect(getByTestId(TEST_ID).textContent).toBe(CHORD);
	});

	it('draws a heading at the level it is told, to whoever goes through the page by its headings', () => {
		const { getByRole } = render(Heading, { tag: 'h3', heads: 'list', children: drawn });

		expect(getByRole('heading', { level: 3 }).textContent).toBe(WORDS);
	});

	it('draws what is told to stand as plain words as words, where something else heads its part', () => {
		const { queryByRole, getByText } = render(Heading, { tag: 'p', heads: 'piece', children: drawn });

		expect(queryByRole('heading')).toBeNull();
		expect(getByText(WORDS)).toBeDefined();
	});
});

describe('a row of the library', () => {
	it('draws what it is called, and does what it does when pressed', async () => {
		const onclick = vi.fn();
		const { getByTestId } = render(Row, { names: 'path', testId: TEST_ID, label: drawn, onclick });

		await userEvent.click(getByTestId(TEST_ID));

		expect(getByTestId(TEST_ID).textContent.trim()).toBe(WORDS);
		expect(onclick).toHaveBeenCalledOnce();
	});

	it.each([
		{ folded: true, expanded: 'false' },
		{ folded: false, expanded: 'true' }
	])(
		'says whether what it folds is open, folded $folded, to whoever cannot see its chevron',
		({ folded, expanded }) => {
			const { getByTestId } = render(Row, { names: 'title', folded, testId: TEST_ID, label: drawn });

			expect(getByTestId(TEST_ID).getAttribute('aria-expanded')).toBe(expanded);
		}
	);

	it('says nothing of being open where it folds nothing', () => {
		const { getByTestId } = render(Row, { names: 'title', testId: TEST_ID, label: drawn });

		expect(getByTestId(TEST_ID).hasAttribute('aria-expanded')).toBe(false);
	});

	it('says what the rail a column put away leaves does, to whoever cannot see its toggle, and with its key under the pointer', () => {
		const { getByTestId } = render(ColumnRail, { side: 'left', label: WORDS, key: 'f', testId: TEST_ID });

		expect(getByTestId(TEST_ID).getAttribute('aria-label')).toBe(WORDS);
		expect(getByTestId(TEST_ID).getAttribute('title')).toBe(`${WORDS} (f)`);
	});
});
