import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { userEvent } from '@testing-library/user-event';
import Button from '$lib/ui/Button.svelte';
import Card from '$lib/ui/Card.svelte';
import CodeBox from '$lib/ui/CodeBox.svelte';
import ColumnBar from '$lib/ui/ColumnBar.svelte';
import ColumnRail from '$lib/ui/ColumnRail.svelte';
import Dialog from '$lib/ui/Dialog.svelte';
import EdgeFrame from '$lib/ui/EdgeFrame.svelte';
import Icon from '$lib/ui/Icon.svelte';
import IconButton from '$lib/ui/IconButton.svelte';
import Link from '$lib/ui/Link.svelte';
import NoticeBar from '$lib/ui/NoticeBar.svelte';
import Pane from '$lib/ui/Pane.svelte';
import PopoverPanel from '$lib/ui/PopoverPanel.svelte';
import Row from '$lib/ui/Row.svelte';
import Segment from '$lib/ui/Segment.svelte';
import Segmented from '$lib/ui/Segmented.svelte';
import Chip from '$lib/ui/Chip.svelte';
import Count from '$lib/ui/Count.svelte';
import Dot from '$lib/ui/Dot.svelte';
import Key from '$lib/ui/Key.svelte';
import Tag from '$lib/ui/Tag.svelte';
import Band from '$lib/ui/Band.svelte';

// What a test hands the library's parts to draw inside them, and what it finds each by
const WORDS = 'Show the whole diff';
const drawn = createRawSnippet(() => ({ render: () => `<span>${WORDS}</span>` }));
const TEST_ID = 'drawn';
// A look someone might try to lay over a part of the library from outside, which the library takes no part of
const FROM_OUTSIDE = 'from-outside';
const RELEASE = 'https://github.com/pavelparanin/claude-review/releases';
// How many threads a count says hang on what it stands beside
const THREADS = 3;
// What a chip's cross says it does
const REMOVING = 'Take this thread out of the message';
// Keys held together, as the help writes them
const CHORD = 'Ctrl+Enter';

/** A part of the library, drawn with what every one of them is drawn with, and a class handed to it besides. */
const WITH_A_CLASS_FROM_OUTSIDE = [
	{
		part: 'a button',
		render: () =>
			render(Button, {
				tone: 'quiet',
				size: 'xs',
				testId: TEST_ID,
				children: drawn,
				class: FROM_OUTSIDE
			} as never)
	},
	{
		part: 'an icon button',
		render: () =>
			render(IconButton, {
				tone: 'quiet',
				size: 'xs',
				label: WORDS,
				testId: TEST_ID,
				children: drawn,
				class: FROM_OUTSIDE
			} as never)
	},
	{
		part: 'an icon',
		render: () => render(Icon, { name: 'check', size: 'xs', testId: TEST_ID, class: FROM_OUTSIDE } as never)
	},
	{
		part: 'a pane by a control',
		render: () =>
			render(PopoverPanel, {
				role: 'dialog',
				label: WORDS,
				placement: 'below-start',
				seenIn: () => new DOMRect(),
				width: 'medium',
				arrow: true,
				arrowOffset: 0,
				testId: TEST_ID,
				children: drawn,
				class: FROM_OUTSIDE
			} as never)
	},
	{
		part: 'a pane that stands by itself',
		render: () => render(Pane, { width: 'medium', testId: TEST_ID, children: drawn, class: FROM_OUTSIDE } as never)
	},
	{
		part: 'a modal',
		render: () =>
			render(Dialog, {
				label: WORDS,
				width: 'wide',
				testId: TEST_ID,
				onClose: () => undefined,
				children: drawn,
				class: FROM_OUTSIDE
			} as never)
	},
	{
		part: "a column's bar",
		render: () => render(ColumnBar, { testId: TEST_ID, children: drawn, class: FROM_OUTSIDE } as never)
	},
	{
		part: 'a card',
		render: () =>
			render(Card, { tone: 'quiet', hangs: 'line', testId: TEST_ID, children: drawn, class: FROM_OUTSIDE } as never)
	},
	{
		part: 'code set apart',
		render: () => render(CodeBox, { code: WORDS, testId: TEST_ID, class: FROM_OUTSIDE } as never)
	},
	{
		part: 'a frame with an edge at its start',
		render: () =>
			render(EdgeFrame, {
				tone: 'agent',
				ground: 'none',
				testId: TEST_ID,
				children: drawn,
				class: FROM_OUTSIDE
			} as never)
	},
	{
		part: 'a link',
		render: () => render(Link, { href: RELEASE, testId: TEST_ID, children: drawn, class: FROM_OUTSIDE } as never)
	},
	{
		part: 'a notice',
		render: () =>
			render(NoticeBar, {
				tone: 'warning',
				icon: 'notice',
				testId: TEST_ID,
				children: drawn,
				class: FROM_OUTSIDE
			} as never)
	},
	{
		part: 'a segment',
		render: () => render(Segment, { pressed: false, testId: TEST_ID, children: drawn, class: FROM_OUTSIDE } as never)
	},
	{
		part: 'a segmented control',
		render: () => render(Segmented, { label: WORDS, testId: TEST_ID, children: drawn, class: FROM_OUTSIDE } as never)
	},
	{
		part: 'a tag',
		render: () => render(Tag, { tone: 'quiet', testId: TEST_ID, children: drawn, class: FROM_OUTSIDE } as never)
	},
	{
		part: 'a count',
		render: () => render(Count, { count: THREADS, testId: TEST_ID, class: FROM_OUTSIDE } as never)
	},
	{
		part: 'a chip',
		render: () =>
			render(Chip, {
				voice: 'reader',
				onclick: () => undefined,
				testId: TEST_ID,
				children: drawn,
				class: FROM_OUTSIDE
			} as never)
	},
	{
		part: 'a dot',
		render: () => render(Dot, { tone: 'unread', testId: TEST_ID, class: FROM_OUTSIDE } as never)
	},
	{
		part: 'a key',
		render: () => render(Key, { keys: CHORD, testId: TEST_ID, class: FROM_OUTSIDE } as never)
	},
	{
		part: 'a band in a frame of bands',
		render: () =>
			render(Band, { current: false, testId: TEST_ID, children: drawn, offer: drawn, class: FROM_OUTSIDE } as never)
	}
];

describe('the component library', () => {
	it.each(WITH_A_CLASS_FROM_OUTSIDE)(
		'draws $part its own way: a class handed to it from outside is not drawn',
		({ render: drawIt }) => {
			const { getByTestId } = drawIt();

			expect(getByTestId(TEST_ID).classList).not.toContain(FROM_OUTSIDE);
		}
	);

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

	it('draws a tag with the words it is handed, as they are written', () => {
		const { getByTestId } = render(Tag, { tone: 'agent', testId: TEST_ID, children: drawn });

		expect(getByTestId(TEST_ID).textContent).toBe(WORDS);
	});

	it('says how many in a count', () => {
		const { getByTestId } = render(Count, { count: THREADS, testId: TEST_ID });

		expect(getByTestId(TEST_ID).textContent).toBe(String(THREADS));
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

	it('says a key is a key of the keyboard, to whoever cannot see its box', () => {
		const { getByTestId } = render(Key, { keys: CHORD, testId: TEST_ID });

		expect(getByTestId(TEST_ID).tagName).toBe('KBD');
		expect(getByTestId(TEST_ID).textContent).toBe(CHORD);
	});
});

// A row of the library, and the rail a column put away leaves, each with a class handed to it besides
const ROWS_WITH_A_CLASS_FROM_OUTSIDE = [
	{
		part: 'a row',
		render: () => render(Row, { names: 'path', testId: TEST_ID, label: drawn, class: FROM_OUTSIDE } as never)
	},
	{
		part: 'a row that folds what is under it',
		render: () =>
			render(Row, { names: 'title', folded: true, testId: TEST_ID, label: drawn, class: FROM_OUTSIDE } as never)
	},
	{
		part: 'the rail a column put away leaves',
		render: () => render(ColumnRail, { label: WORDS, testId: TEST_ID, class: FROM_OUTSIDE } as never)
	}
];

describe('a row of the library', () => {
	it.each(ROWS_WITH_A_CLASS_FROM_OUTSIDE)(
		'draws $part its own way: a class handed to it from outside is not drawn',
		({ render: drawIt }) => {
			const { getByTestId } = drawIt();

			expect(getByTestId(TEST_ID).classList).not.toContain(FROM_OUTSIDE);
		}
	);

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

	it('says what the rail a column put away leaves does, to whoever cannot see its chevron and under the pointer', () => {
		const { getByTestId } = render(ColumnRail, { label: WORDS, testId: TEST_ID });

		expect(getByTestId(TEST_ID).getAttribute('aria-label')).toBe(WORDS);
		expect(getByTestId(TEST_ID).getAttribute('title')).toBe(WORDS);
	});
});
