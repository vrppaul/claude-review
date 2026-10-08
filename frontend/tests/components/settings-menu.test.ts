import { describe, it, expect, beforeEach, vi } from 'vitest';
import { userEvent } from '@testing-library/user-event';
import { render } from '@testing-library/svelte';
import TopBar from '$lib/components/TopBar.svelte';
import { diffStore } from '$lib/stores/diff.svelte';
import { settingsStore } from '$lib/stores/settings.svelte';

const HEADER = { submitting: false, error: null, onOpenModal: () => {} };

/** A server that answers the diff of one repository, and takes any setting. */
function serveRepository() {
	vi.stubGlobal(
		'fetch',
		vi.fn().mockResolvedValue({
			ok: true,
			json: () =>
				Promise.resolve({
					files: [],
					mode: 'diff',
					title: 'repo: uncommitted changes',
					phrase: 'uncommitted changes',
					release: '1.5.0'
				})
		})
	);
}

describe('the settings', () => {
	beforeEach(async () => {
		localStorage.clear();
		settingsStore.clear();
		diffStore.clear();
		serveRepository();
		await diffStore.fetchDiff();
	});


	it('keep the choices made once out of the header, behind the gear', async () => {
		const user = userEvent.setup();
		const { getByTestId, queryByTestId } = render(TopBar, { props: HEADER });
		expect(queryByTestId('layout-split')).toBeNull();

		await user.click(getByTestId('settings-toggle'));
		await user.click(getByTestId('layout-split'));

		expect(diffStore.diffLayout).toBe('split');
	});

	it('say in the header that whitespace is hidden, and show it again from there', async () => {
		const user = userEvent.setup();
		await settingsStore.change({ ignore_whitespace: true });
		const { getByTestId, queryByTestId } = render(TopBar, { props: HEADER });
		expect(getByTestId('whitespace-hidden').textContent).toContain('No whitespace');

		await user.click(getByTestId('show-whitespace'));

		expect(settingsStore.settings.ignore_whitespace).toBe(false);
		expect(queryByTestId('whitespace-hidden')).toBeNull();
	});
});
