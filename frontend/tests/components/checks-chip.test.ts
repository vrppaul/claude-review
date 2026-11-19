import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import ChecksChip from '$lib/components/ChecksChip.svelte';
import type { Check, DiffFile } from '$lib/types';
import { check, failedCheck, failure, outOfDateCheck } from '../checks';
import { diffFile } from '../diff';
import { inReview, openReview } from '../review';

/** The chip, drawn in a review of these files holding these checks, in its first round unless a test says. */
function chipOver(checks: Check[], { round = 1, files = [] }: { round?: number; files?: DiffFile[] } = {}) {
	const review = openReview({ files, facts: { checks, round } });
	return render(ChecksChip, inReview(review));
}

/** The name of a check its row says first. */
function nameIn(row: HTMLElement): string {
	return read(row).split(' ')[0];
}

/** Open the pane the chip opens, as the reader does. */
async function openPane(): Promise<HTMLElement> {
	await userEvent.setup({ delay: null }).click(screen.getByTestId('checks'));
	return screen.getByTestId('checks-pane');
}

/** Words as the reader reads them, however the markup breaks them. */
function read(element: HTMLElement): string {
	return element.textContent.replace(/\s+/g, ' ').trim();
}

describe('the checks the agent ran, in the header', () => {
	it('is not there while no check is reported', () => {
		chipOver([]);

		expect(screen.queryByTestId('checks')).toBeNull();
	});

	it.each([
		{ said: '3 checks', checks: [check({ name: 'a' }), check({ name: 'b' }), check({ name: 'c' })] },
		{ said: '1 check', checks: [check()] },
		{
			said: '2 of 3 out of date',
			checks: [outOfDateCheck(['a.py'], { name: 'a' }), outOfDateCheck(['a.py'], { name: 'b' }), check({ name: 'c' })]
		},
		{ said: '1 of 2 failed', checks: [failedCheck([failure()], { name: 'a' }), check({ name: 'b' })] },
		{
			said: '1 of 2 failed',
			checks: [failedCheck([], { name: 'a' }), outOfDateCheck(['a.py'], { name: 'b', status: 'failed' })]
		}
	])('says the worst of what they say: $said', ({ said, checks }) => {
		chipOver(checks);

		expect(read(screen.getByTestId('checks'))).toBe(said);
	});

	it('lists what failed first, then what the code changed after, then the rest', async () => {
		chipOver([
			check({ name: 'tsc' }),
			outOfDateCheck(['a.py'], { name: 'eslint', status: 'failed' }),
			failedCheck([failure()], { name: 'vitest' })
		]);

		const pane = await openPane();

		expect(within(pane).getAllByTestId('check').map(nameIn)).toEqual(['vitest', 'eslint', 'tsc']);
		expect(within(within(pane).getByTestId('checks-out-of-date')).getAllByTestId('check').map(nameIn)).toEqual([
			'eslint'
		]);
	});

	it('says which files changed after the checks out of date ran, each once', async () => {
		chipOver([outOfDateCheck(['src/a.py', 'src/b.py'], { name: 'ruff' }), outOfDateCheck(['src/a.py'])], {
			files: [diffFile({ path: 'src/a.py' }), diffFile({ path: 'src/b.py' })]
		});

		const pane = await openPane();

		expect(within(pane).getAllByTestId('check-changed-file').map(read)).toEqual(['a.py', 'b.py']);
	});

	it('says where a check failed, what failed and why', async () => {
		chipOver([failedCheck([failure({ path: 'src/a.py', line: 12, what: 'F401', why: '`os` imported but unused' })])]);

		const pane = await openPane();

		expect(read(within(pane).getByTestId('check-failure'))).toBe('F401 a.py:12 `os` imported but unused');
	});

	it('folds where a failed check failed by its line, and opens it again', async () => {
		const user = userEvent.setup({ delay: null });
		chipOver([failedCheck([failure({ what: 'test_rename' })], { name: 'pytest' })]);
		const pane = await openPane();
		const line = within(pane).getByRole('button', { name: /pytest/ });

		await user.click(line);
		expect(within(pane).queryByTestId('check-failure')).toBeNull();

		await user.click(line);
		expect(read(within(pane).getByTestId('check-failure'))).toContain('test_rename');
	});

	it('says the round a check was reported in, where it is not the round being written', async () => {
		chipOver([check({ name: 'ruff', round: 1 }), check({ name: 'mypy', round: 2 })], { round: 2 });

		const pane = await openPane();

		expect(within(pane).getAllByTestId('check').map(read)).toEqual([
			expect.stringMatching(/^ruff round 1, \d/),
			expect.stringMatching(/^mypy \d/)
		]);
	});
});
