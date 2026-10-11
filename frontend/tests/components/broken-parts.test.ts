import { describe, it, expect, vi } from 'vitest';
import { render, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import { tick } from 'svelte';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import { contextLine, diffFile, hunk } from '../diff';
import { work } from '../agent-work';
import { openReview } from '../review';

// What breaks: drawing one file, and naming one file in the panel. Hoisted
// with the mocks below, which run before anything else in this file.
const breaking = vi.hoisted(() => ({ section: 'broken.py', panel: 'breaks-the-panel.py' }));

vi.mock('$lib/utils/highlight', async (importOriginal) => {
	const original = await importOriginal<typeof import('$lib/utils/highlight')>();
	return {
		...original,
		languageOf: (...given: Parameters<typeof original.languageOf>) => {
			if (given[1] === breaking.section) throw new Error('could not tell what it is written in');
			return original.languageOf(...given);
		}
	};
});

vi.mock('$lib/utils/paths', async (importOriginal) => {
	const original = await importOriginal<typeof import('$lib/utils/paths')>();
	return {
		...original,
		fileName: (path: string) => {
			if (path === breaking.panel) throw new Error('could not name the file');
			return original.fileName(path);
		}
	};
});

const files = [
	diffFile({ path: 'first.py', hunks: [hunk([contextLine(1, 1, 'x = 1')])] }),
	diffFile({ path: breaking.section, hunks: [hunk([contextLine(1, 1, 'y = 2')])] }),
	diffFile({ path: 'last.py', hunks: [hunk([contextLine(1, 1, 'z = 3')])] })
];

/** The review on screen whole, an agent answering it and its panel open. */
function reviewOnScreen() {
	const review = openReview({ files, facts: { answerer_attached: true } });
	review.layout.agentPanel.setOpen(true);
	return { review, ...render(ReviewScreen, { props: { review } }) };
}

describe('a part of the review that breaks', () => {
	it('is a file that says it could not be drawn, among the files that could', () => {
		const { getAllByTestId, getByTestId } = reviewOnScreen();

		expect(getByTestId('part-failed').textContent).toContain(`${breaking.section} could not be drawn`);
		expect(getByTestId('part-failed').textContent).toContain('could not tell what it is written in');
		expect(getAllByTestId('file-section').map((section) => section.dataset.path)).toEqual(['first.py', 'last.py']);
		expect(getByTestId('top-bar')).toBeTruthy();
		expect(getByTestId('agent-panel')).toBeTruthy();
	});

	it('is a panel that says it broke, beside the review still on screen', async () => {
		const { review, getAllByTestId, getByTestId, queryByTestId } = reviewOnScreen();

		review.answerer.showWork(work({ files: [breaking.panel] }));
		await tick();

		expect(queryByTestId('agent-panel')).toBeNull();
		expect(getAllByTestId('part-failed').map((failed) => failed.textContent)).toContainEqual(
			expect.stringContaining('The agent panel could not be drawn')
		);
		expect(getAllByTestId('file-section')).toHaveLength(2);
		expect(getByTestId('top-bar')).toBeTruthy();
	});

	it('is drawn again when the reader asks, once what broke it has gone', async () => {
		const user = userEvent.setup();
		const { review, getAllByTestId, getByTestId } = reviewOnScreen();
		review.answerer.showWork(work({ files: [breaking.panel] }));
		await tick();

		review.answerer.showWork(null);
		const panelFailure = getAllByTestId('part-failed').find((failed) => failed.textContent?.includes('agent panel'));
		if (!panelFailure) throw new Error('The panel did not say it broke');
		await user.click(within(panelFailure).getByTestId('redraw-part'));

		expect(getByTestId('agent-panel')).toBeTruthy();
	});
});
