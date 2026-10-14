/**
 * A story's diagram, drawn from the Mermaid the agent wrote.
 *
 * Whether a source draws only a browser can say, so this is where it is
 * said: a drawing comes back as its svg, or as what stopped it, as mermaid
 * threw it. Mermaid is loaded the first time a story has a diagram to draw,
 * never with the page, and the module system keeps it from then on: a
 * review with no diagram fetches none of it.
 *
 * Mermaid draws at its strict level, where it cleans every label and wires
 * no `click` line of a source. A source may carry settings of its own, in a
 * directive (`%%{init: …}%%`): it may change none of those it is kept from
 * below, which hold that level, and the look and the layout the page gives
 * every drawing.
 *
 * Mermaid writes a drawing's look into a style inside its svg, each rule
 * scoped by the drawing's id, where no rule of the page's stylesheet
 * reaches. The page's look goes in with it (`assets/diagram.css`), naming
 * the page's tokens. The page's font goes in as a setting, read off the
 * page as it draws: mermaid measures every label in its own font, so a font
 * set only in the stylesheet would draw labels it had measured in another.
 */

import type { MermaidConfig } from 'mermaid';
import diagramLook from '$lib/assets/diagram.css?raw';

/** A drawing: its svg, or what stopped mermaid drawing it, as mermaid threw it. */
export type Drawing = { svg: string } | { fault: unknown };

// The page's own font, as its stylesheet names it on the page's root
const PAGE_FONT = '--font-sans';
// How large the words of a node are drawn: a step under the overview's own words, as the page's small words are
const LABEL_SIZE = '13px';

// What a source's own directive may not change: mermaid's six, which hold the level it draws at, and the
// look and the layout the page gives every drawing. Mermaid takes this list in place of its own
const KEPT_FROM_SOURCES = [
	'secure',
	'securityLevel',
	'startOnLoad',
	'maxTextSize',
	'suppressErrorRendering',
	'maxEdges',
	'theme',
	'themeVariables',
	'themeCSS',
	'fontFamily',
	'look',
	'darkMode',
	'layout'
];

const SETTINGS: MermaidConfig = {
	startOnLoad: false,
	securityLevel: 'strict',
	secure: KEPT_FROM_SOURCES,
	// A source that does not draw throws, and leaves nothing behind: otherwise mermaid draws a picture of its
	// error in the page's body, and throws before it takes it away
	suppressErrorRendering: true,
	// The one theme whose colours are all its settings: the page's look then overrides it rule by rule
	theme: 'base',
	themeCSS: diagramLook,
	// Mermaid's own layout is elk: a flowchart it lays out fetches 2.2 MB, one dagre lays out 0.8 MB, and draws
	// in a third of the time. Named here, the layout stays when mermaid next changes its own
	layout: 'dagre',
	// A flowchart is drawn at its own size, not shrunk to its column: its box scrolls sideways instead
	flowchart: { useMaxWidth: false }
};

/** The page's own font, as the page has it now. */
function pageFont(): string {
	return getComputedStyle(document.documentElement).getPropertyValue(PAGE_FONT).trim();
}

/** The settings a drawing is drawn with: made afresh for each, as mermaid writes the font into the theme's. */
function settings(): MermaidConfig {
	return { ...SETTINGS, fontFamily: pageFont(), themeVariables: { fontSize: LABEL_SIZE } };
}

/**
 * Draw a source, under an id no other drawing on the page has: mermaid
 * scopes the drawing's look, and the ids of what it draws, by it.
 */
export async function drawDiagram(source: string, drawingId: string): Promise<Drawing> {
	try {
		const { default: mermaid } = await import('mermaid');
		mermaid.initialize(settings());
		const { svg } = await mermaid.render(drawingId, source);
		return { svg };
	} catch (fault: unknown) {
		return { fault };
	}
}
