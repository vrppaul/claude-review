import { describe, it, expect, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import ContentViewToggle from '$lib/components/ContentViewToggle.svelte';
import { diffStore } from '$lib/stores/diff.svelte';

describe('ContentViewToggle', () => {
	beforeEach(() => {
		diffStore.clear();
	});

	it('renders all three mode buttons', () => {
		const { getByTestId } = render(ContentViewToggle);

		expect(getByTestId('view-mode-raw')).toBeTruthy();
		expect(getByTestId('view-mode-preview')).toBeTruthy();
		expect(getByTestId('view-mode-side-by-side')).toBeTruthy();
	});

	it('raw button is active by default', () => {
		const { getByTestId } = render(ContentViewToggle);

		expect(getByTestId('view-mode-raw').classList.contains('btn-outline')).toBe(false);
		expect(getByTestId('view-mode-preview').classList.contains('btn-outline')).toBe(true);
	});

	it('clicking preview updates the store', async () => {
		const user = userEvent.setup();
		const { getByTestId } = render(ContentViewToggle);

		await user.click(getByTestId('view-mode-preview'));

		expect(diffStore.contentViewMode).toBe('preview');
	});

	it('clicking side-by-side updates the store', async () => {
		const user = userEvent.setup();
		const { getByTestId } = render(ContentViewToggle);

		await user.click(getByTestId('view-mode-side-by-side'));

		expect(diffStore.contentViewMode).toBe('side-by-side');
	});

	it('active state follows the store', async () => {
		const user = userEvent.setup();
		const { getByTestId } = render(ContentViewToggle);

		await user.click(getByTestId('view-mode-preview'));

		expect(getByTestId('view-mode-raw').classList.contains('btn-outline')).toBe(true);
		expect(getByTestId('view-mode-preview').classList.contains('btn-outline')).toBe(false);
	});
});
