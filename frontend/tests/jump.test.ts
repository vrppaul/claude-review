import { describe, expect, it, vi } from 'vitest';
import { Jumps } from '$lib/dom/jump';
import { frames } from './frames';

/** Something drawn on the page that stands still wherever it is scrolled to: jsdom lays nothing out. */
function standingStill(): HTMLElement {
	const element = document.body.appendChild(document.createElement('div'));
	element.scrollIntoView = () => undefined;
	return element;
}

// Where a jump ends, and what it does at rest, is held through the sections that ask for one, in
// tests/show-file.test.ts and tests/reading-band.test.ts: here, what only whoever is landed on can say
describe('whoever says where the reader is, landed on by a jump', () => {
	it('hears that the reader came to rest once, not again when a later jump to something else does', async () => {
		const jumps = new Jumps();
		const reading = { land: vi.fn(), settle: vi.fn() };
		jumps.land(reading, standingStill());
		await frames();

		jumps.to(standingStill(), 'center');
		await frames();

		expect(reading.settle).toHaveBeenCalledTimes(1);
	});
});
