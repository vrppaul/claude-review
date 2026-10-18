import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { userEvent } from '@testing-library/user-event';
import Button from '$lib/ui/Button.svelte';
import IconButton from '$lib/ui/IconButton.svelte';
import Link from '$lib/ui/Link.svelte';
import Segment from '$lib/ui/Segment.svelte';
import Segmented from '$lib/ui/Segmented.svelte';

// What a test hands the library's parts to draw inside them, and what it finds each by
const WORDS = 'Show the whole diff';
const drawn = createRawSnippet(() => ({ render: () => `<span>${WORDS}</span>` }));
const TEST_ID = 'drawn';
// A look someone might try to lay over a part of the library from outside, which the library takes no part of
const FROM_OUTSIDE = 'from-outside';
const RELEASE = 'https://github.com/pavelparanin/claude-review/releases';

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
		part: 'a link',
		render: () => render(Link, { href: RELEASE, testId: TEST_ID, children: drawn, class: FROM_OUTSIDE } as never)
	},
	{
		part: 'a segment',
		render: () => render(Segment, { pressed: false, testId: TEST_ID, children: drawn, class: FROM_OUTSIDE } as never)
	},
	{
		part: 'a segmented control',
		render: () => render(Segmented, { label: WORDS, testId: TEST_ID, children: drawn, class: FROM_OUTSIDE } as never)
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
});
