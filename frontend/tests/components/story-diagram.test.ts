import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import { userEvent } from '@testing-library/user-event';
import { flushSync } from 'svelte';
import ReviewScreen from '$lib/components/ReviewScreen.svelte';
import { drawDiagram } from '$lib/dom/diagram';
import type { Review } from '$lib/review/review.svelte';
import { addedLine, diffFile, hunk } from '../diff';
import { broughtIntoView } from '../elements';
import { fakeServer } from '../fake-server';
import { openReview } from '../review';
import { storyHeld, storyResponse, toldChapter, toldStep } from '../story';

// jsdom cannot lay a drawing out, so mermaid's part is played here: the page is handed what a test says
// mermaid drew, or why it could not draw
vi.mock('$lib/dom/diagram', async (importOriginal) => ({
	...(await importOriginal<typeof import('$lib/dom/diagram')>()),
	drawDiagram: vi.fn()
}));

const files = [diffFile({ path: 'a.py', hunks: [hunk([addedLine(1, 'one'), addedLine(9, 'nine')])] })];
// The names the agent's source gives its nodes: one whose name begins another's, and one linked nowhere
const NODES = ['store', 'store-2', 'agent'];
const SOURCE = 'flowchart LR\n  store[Image store] --> store-2[Second store] --> agent[Agent opens it]';
const CAPTION = 'How an image travels';
const DIAGRAM = { mermaid: SOURCE, caption: CAPTION, links: { store: 'ch-1', 'store-2': 'ch-2' } };
const CHAPTERS = [
	toldChapter('ch-1', [toldStep('a.py', 1)], { title: 'The beginnings' }),
	toldChapter('ch-2', [toldStep('a.py', 9)], { title: 'The end' })
];
const HELD = storyHeld({ overview: { ...storyHeld().story.overview, diagram: DIAGRAM }, chapters: CHAPTERS });
// The same story told again: the same drawing, its first node no longer linked
const RELINKED = storyHeld({
	overview: { ...storyHeld().story.overview, diagram: { ...DIAGRAM, links: { 'store-2': 'ch-2' } } },
	chapters: CHAPTERS
});
// What the page calls a drawing the agent called nothing
const UNCAPTIONED = 'The change drawn';
// Why mermaid could not draw a source, as it might say
const MERMAIDS_REASON = 'No diagram type detected';

let review: Review;

/**
 * What mermaid draws of the source, as far as the page reads it: a node for each name, under the id
 * mermaid gives a node of a flowchart, which begins with the drawing's own. Its box carries a test id of
 * the test's own, which the page leaves alone: the node itself is the page's to mark.
 */
function drawnAs(_source: string, drawingId: string): Promise<{ svg: string }> {
	const nodes = NODES.map(
		(name, place) =>
			`<g class="node" id="${drawingId}-flowchart-${name}-${place}"><rect data-testid="node-${name}"></rect><text>${name}</text></g>`
	);
	return Promise.resolve({ svg: `<svg id="${drawingId}">${nodes.join('')}</svg>` });
}

/** The figure the overview draws the diagram in. */
function figure(): HTMLElement {
	return screen.getByTestId('story-diagram');
}

/** The chapters the story draws, in its order. */
function chapters(): HTMLElement[] {
	return screen.getAllByTestId('story-chapter');
}

describe("a story's diagram", () => {
	beforeEach(() => {
		// The stand-in for mermaid is the file's, and each test counts the drawings of its own page alone
		vi.mocked(drawDiagram).mockReset();
		review = openReview({ files, story: HELD });
		review.views.choose('story');
	});

	it('draws what mermaid drew of the source, under what the agent called it, and not the source', async () => {
		vi.mocked(drawDiagram).mockImplementation(drawnAs);
		render(ReviewScreen, { props: { review } });

		const drawing = await within(figure()).findByTestId('diagram-drawing');

		expect(within(drawing).getByTestId('node-store')).toBeTruthy();
		expect(figure().textContent).toContain(CAPTION);
		expect(figure().textContent).not.toContain(SOURCE);
	});

	it('says only what it is called while mermaid draws it', () => {
		vi.mocked(drawDiagram).mockReturnValue(new Promise(() => {}));
		render(ReviewScreen, { props: { review } });

		expect(figure().textContent.trim()).toBe(CAPTION);
	});

	it('says why mermaid could not draw it, and shows the source as the agent wrote it, with nothing to open large', async () => {
		vi.mocked(drawDiagram).mockResolvedValue({ fault: new Error(MERMAIDS_REASON) });
		render(ReviewScreen, { props: { review } });

		const fault = await within(figure()).findByTestId('diagram-fault');

		expect(fault.textContent).toBe(`This diagram could not be drawn: ${MERMAIDS_REASON}.`);
		expect(within(figure()).getByTestId('diagram-source').textContent).toBe(SOURCE);
		expect(within(figure()).queryByTestId('diagram-open-large')).toBeNull();
	});

	it('takes the reader to the chapter a node leads to when it is pressed', async () => {
		vi.mocked(drawDiagram).mockImplementation(drawnAs);
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });
		const toTheBeginnings = broughtIntoView(chapters()[0]);

		await user.click(await within(figure()).findByTestId('node-store'));

		expect(toTheBeginnings).toHaveBeenCalled();
	});

	it('tells a node from one whose name begins with its name', async () => {
		vi.mocked(drawDiagram).mockImplementation(drawnAs);
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });
		const [toTheBeginnings, toTheEnd] = chapters().map(broughtIntoView);

		await user.click(await within(figure()).findByTestId('node-store-2'));

		expect(toTheEnd).toHaveBeenCalled();
		expect(toTheBeginnings).not.toHaveBeenCalled();
	});

	it('marks each node that leads to a chapter, for a test to press, and no other', async () => {
		vi.mocked(drawDiagram).mockImplementation(drawnAs);
		render(ReviewScreen, { props: { review } });
		await within(figure()).findByTestId('diagram-drawing');

		expect(
			within(figure())
				.getAllByTestId('diagram-link')
				.map((node) => node.textContent)
		).toEqual(['store', 'store-2']);
	});

	it('takes the reader nowhere from a node the story, read again, no longer links, and no longer marks it', async () => {
		vi.mocked(drawDiagram).mockImplementation(drawnAs);
		fakeServer().answer('GET /api/story', storyResponse({ held: RELINKED }));
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });
		await within(figure()).findByTestId('diagram-drawing');
		const broughtTo = chapters().map(broughtIntoView);

		await review.story.read();
		flushSync();
		await user.click(within(figure()).getByTestId('node-store'));

		expect(broughtTo.map((brought) => brought.mock.calls.length)).toEqual([0, 0]);
		expect(
			within(figure())
				.getAllByTestId('diagram-link')
				.map((node) => node.textContent)
		).toEqual(['store-2']);
	});

	it('is named all the same where the agent called it nothing, and so is the dialog that draws it large', async () => {
		vi.mocked(drawDiagram).mockImplementation(drawnAs);
		review = openReview({
			files,
			story: storyHeld({
				overview: { ...storyHeld().story.overview, diagram: { ...DIAGRAM, caption: null } },
				chapters: CHAPTERS
			})
		});
		review.views.choose('story');
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });

		await user.click(await within(figure()).findByTestId('diagram-open-large'));

		expect(figure().getAttribute('aria-label')).toBe(UNCAPTIONED);
		expect(screen.getByTestId('diagram-large').getAttribute('aria-label')).toBe(UNCAPTIONED);
	});

	it('takes the reader nowhere from a node that leads nowhere', async () => {
		vi.mocked(drawDiagram).mockImplementation(drawnAs);
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });
		const broughtTo = chapters().map(broughtIntoView);

		await user.click(await within(figure()).findByTestId('node-agent'));

		expect(broughtTo.map((brought) => brought.mock.calls.length)).toEqual([0, 0]);
	});

	it('draws it again, in a dialog of its own, once asked to open it large', async () => {
		vi.mocked(drawDiagram).mockImplementation(drawnAs);
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });

		await user.click(await within(figure()).findByTestId('diagram-open-large'));
		const large = screen.getByTestId('diagram-large');

		expect(await within(large).findByTestId('diagram-drawing')).toBeTruthy();
		expect(large.getAttribute('aria-label')).toBe(CAPTION);
		expect(new Set(vi.mocked(drawDiagram).mock.calls.map(([, drawingId]) => drawingId)).size).toBe(2);
	});

	it('closes the dialog, then takes the reader to the chapter a node in it leads to', async () => {
		vi.mocked(drawDiagram).mockImplementation(drawnAs);
		const user = userEvent.setup();
		render(ReviewScreen, { props: { review } });
		const toTheEnd = broughtIntoView(chapters()[1]);

		await user.click(await within(figure()).findByTestId('diagram-open-large'));
		await user.click(await within(screen.getByTestId('diagram-large')).findByTestId('node-store-2'));

		expect(screen.queryByTestId('diagram-large')).toBeNull();
		expect(toTheEnd).toHaveBeenCalled();
	});

	it('is drawn once, however often the story is read again', async () => {
		vi.mocked(drawDiagram).mockImplementation(drawnAs);
		fakeServer().answer('GET /api/story', storyResponse({ held: HELD }));
		render(ReviewScreen, { props: { review } });
		await within(figure()).findByTestId('diagram-drawing');

		await review.story.read();
		flushSync();

		expect(drawDiagram).toHaveBeenCalledOnce();
	});
});
