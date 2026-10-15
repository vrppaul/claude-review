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
// How wide the tree of files and a story's contents stand until the reader sizes them, in pixels,
// and a width the reader leaves them at
const TREE_AT_FIRST = 240;
const WIDTH_AS_LEFT = 300;
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

beforeEach(() => {
	// The breakpoints as the built stylesheet sets them on the page's root
	for (const name of BREAKPOINTS) document.documentElement.style.setProperty(name, themeVariable(name));
});

afterEach(() => {
	for (const name of BREAKPOINTS) document.documentElement.style.removeProperty(name);
	vi.unstubAllGlobals();
});

describe('the columns, until the reader opens or shuts them', () => {
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

describe('the contents beside a story, which the reader puts away apart from the tree of files, and which are as wide as it', () => {
	beforeEach(() => {
		screenOf(WIDE);
	});

	it('start as wide as the tree', () => {
		const layout = new PageLayout();

		expect([layout.storyContents.width, layout.fileTree.width]).toEqual([TREE_AT_FIRST, TREE_AT_FIRST]);
	});

	it('are still put away when the page opens again, and the tree still beside the files', () => {
		new PageLayout().storyContents.toggle();

		const openedAgain = new PageLayout();

		expect(openedAgain.storyContents.open).toBe(false);
		expect(openedAgain.fileTree.open).toBe(true);
	});

	it('widen the tree with them: one column beside what is read, whichever view it stands in', () => {
		const layout = new PageLayout();

		layout.storyContents.setWidth(WIDTH_AS_LEFT);

		expect(layout.fileTree.width).toBe(WIDTH_AS_LEFT);
	});

	it('are as wide as the reader left either when the page opens again', () => {
		new PageLayout().fileTree.setWidth(WIDTH_AS_LEFT);

		const openedAgain = new PageLayout();

		expect([openedAgain.storyContents.width, openedAgain.fileTree.width]).toEqual([WIDTH_AS_LEFT, WIDTH_AS_LEFT]);
	});
});
