import { describe, it, expect } from 'vitest';

// Every source of the page as it is written, by where it is from here
const sources: Record<string, string> = import.meta.glob('../src/**/*.{ts,svelte}', {
	query: '?raw',
	import: 'default',
	eager: true
});

// A drawing written into markup, wherever a source writes one
const DRAWING = /<svg\b/g;
// The one source that draws an icon, by its row of ICONS
const ICON = '../src/lib/components/Icon.svelte';

/**
 * Every icon is drawn once, as a row of ICONS that `Icon` draws by name. A
 * review found a speech bubble written into a component with numbers of its
 * own, beside the same bubble in ICONS: so the sources are asked.
 */
describe('an icon', () => {
	it('is drawn by Icon alone: no other source of the page writes a drawing', () => {
		const drawnIn = Object.entries(sources).flatMap(([path, text]) => [...text.matchAll(DRAWING)].map(() => path));

		expect(drawnIn).toEqual([ICON]);
	});
});
