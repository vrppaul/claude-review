import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { PageLayout } from '$lib/reader/page-layout.svelte';
import { handOverNext } from './pushes';
import { openReview } from './review';
import { themeVariable } from './stylesheets';

// A wide screen zoomed to twice its size, or a phone's: too narrow for either column beside the diff
const NARROW = 640;
// Room for the tree beside the diff, not for the panel as well
const MIDDLING = 900;
// A wide screen, which holds the tree, the diff and the panel side by side
const WIDE = 1280;
// What a rem is in a media query: the browser's own size of type, whatever the page sets
const PIXELS_PER_REM = 16;
// Where each column stops lying over the diff and stands beside it, as the stylesheet names them
const BREAKPOINTS = ['--breakpoint-cr-side-column-beside', '--breakpoint-cr-panel-beside'];
// How a media query asks for a screen at least so wide: `(width >= 46rem)`
const AT_LEAST = /^\(width >= ([\d.]+)rem\)$/;

/** A screen this many pixels wide, of a system that has no taste in colours or motion. */
function screenOf(width: number): void {
	vi.stubGlobal(
		'matchMedia',
		vi.fn().mockImplementation((query: string) => {
			const least = AT_LEAST.exec(query);
			return { matches: least !== null && width >= Number(least[1]) * PIXELS_PER_REM };
		})
	);
}

/** Whether each column is on the screen: the tree, and the panel. */
function columns(layout: PageLayout): { tree: boolean; panel: boolean } {
	return { tree: layout.fileTree.open, panel: layout.agentPanel.open };
}

describe('the columns, until the reader opens or shuts them', () => {
	beforeEach(() => {
		// The breakpoints as the built stylesheet sets them on the page's root
		for (const name of BREAKPOINTS) document.documentElement.style.setProperty(name, themeVariable(name));
	});

	afterEach(() => {
		for (const name of BREAKPOINTS) document.documentElement.style.removeProperty(name);
		vi.unstubAllGlobals();
	});

	it('start put away on a narrow screen: the tree from the start, the panel when an agent turns up', () => {
		screenOf(NARROW);
		const review = openReview();

		handOverNext(review, { type: 'answerer', attached: true });

		expect(review.answerer.attached).toBe(true);
		expect(columns(review.layout)).toEqual({ tree: false, panel: false });
	});

	it('stand beside the diff on a wide screen: the tree from the start, the panel when an agent turns up', () => {
		screenOf(WIDE);
		const review = openReview();

		handOverNext(review, { type: 'answerer', attached: true });

		expect(columns(review.layout)).toEqual({ tree: true, panel: true });
	});

	it('each go by their own breakpoint: with room for the tree alone, the panel stays shut', () => {
		screenOf(MIDDLING);
		const layout = new PageLayout();

		layout.agentPanel.offer();

		expect(columns(layout)).toEqual({ tree: true, panel: false });
	});

	it('come when the reader asks for them on a narrow screen', () => {
		screenOf(NARROW);
		const layout = new PageLayout();

		layout.fileTree.toggle();
		layout.agentPanel.toggle();

		expect(columns(layout)).toEqual({ tree: true, panel: true });
	});

	it('stay as the reader left them on a wider screen, opened again on a narrow one', () => {
		screenOf(WIDE);
		const wide = new PageLayout();
		wide.fileTree.toggle();
		wide.fileTree.toggle();
		wide.agentPanel.setOpen(true);

		screenOf(NARROW);
		const narrow = new PageLayout();

		expect(columns(narrow)).toEqual({ tree: true, panel: true });
	});
});
