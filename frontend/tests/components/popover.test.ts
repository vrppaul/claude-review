import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import ReviewHeader from '$lib/components/ReviewHeader.svelte';
import type { Review } from '$lib/review/review.svelte';
import { contextLine, diffFile, diffResponse, hunk } from '../diff';
import { fakeServer, keepingSettings } from '../fake-server';
import { inReview, openReview } from '../review';

const ROUND_ONE = {
	key: 'round:1',
	kind: 'round',
	label: 'Round 1',
	phrase: 'changes since round 1',
	at: null,
	changed: 2
};

let review: Review;

beforeEach(() => {
	const server = fakeServer();
	server.answer('GET /api/diff', diffResponse());
	server.answer('GET /api/versions', { versions: [ROUND_ONE] });
	keepingSettings(server);
	review = openReview({ files: [diffFile({ path: 'a.py', hunks: [hunk([contextLine(1, 1, 'x')])] })] });
});

describe('a menu in the header', () => {
	it('says it opens a pane, whether it is open, and which pane it is', async () => {
		const user = userEvent.setup();
		render(ReviewHeader, inReview(review));
		const toggle = screen.getByTestId('settings-toggle');
		expect(toggle.getAttribute('aria-haspopup')).toBe('dialog');
		expect(toggle.getAttribute('aria-expanded')).toBe('false');

		await user.click(toggle);

		const menu = screen.getByTestId('settings-menu');
		expect(toggle.getAttribute('aria-expanded')).toBe('true');
		expect(toggle.getAttribute('aria-controls')).toBe(menu.id);
		expect(menu.getAttribute('role')).toBe('dialog');
		expect(menu.getAttribute('aria-label')).toBe('Settings');
	});

	it('takes the keyboard into itself when it opens', async () => {
		const user = userEvent.setup();
		render(ReviewHeader, inReview(review));

		await user.click(screen.getByTestId('settings-toggle'));

		expect(screen.getByTestId('settings-menu').contains(document.activeElement)).toBe(true);
	});

	it('closes on Escape and gives the keyboard back to what opened it', async () => {
		const user = userEvent.setup();
		render(ReviewHeader, inReview(review));
		await user.click(screen.getByTestId('settings-toggle'));

		await user.keyboard('{Escape}');

		expect(screen.queryByTestId('settings-menu')).toBeNull();
		expect(document.activeElement).toBe(screen.getByTestId('settings-toggle'));
	});

	it('closes as soon as the reader presses anywhere else', async () => {
		const user = userEvent.setup();
		render(ReviewHeader, inReview(review));
		await user.click(screen.getByTestId('settings-toggle'));

		await user.pointer({ keys: '[MouseLeft>]', target: document.body });

		expect(screen.queryByTestId('settings-menu')).toBeNull();
	});

	it('is one open at a time: opening another closes it', async () => {
		const user = userEvent.setup();
		render(ReviewHeader, inReview(review));
		await user.click(screen.getByTestId('settings-toggle'));

		await user.click(screen.getByTestId('base-picker'));

		expect(screen.queryByTestId('settings-menu')).toBeNull();
		expect(screen.getByTestId('base-list')).toBeTruthy();
	});
});

describe('the list of bases', () => {
	it('puts the keyboard in its filter, and back on the base once one is taken', async () => {
		const user = userEvent.setup();
		render(ReviewHeader, inReview(review));
		await user.click(screen.getByTestId('base-picker'));
		expect(document.activeElement).toBe(screen.getByTestId('base-filter'));

		await user.click(await screen.findByTestId('base-option'));

		expect(screen.queryByTestId('base-list')).toBeNull();
		expect(document.activeElement).toBe(screen.getByTestId('base-picker'));
	});
});
