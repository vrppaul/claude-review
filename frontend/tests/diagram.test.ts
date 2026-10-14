import { describe, it, expect } from 'vitest';
import { drawDiagram } from '$lib/dom/diagram';
import { diagramNotDrawn } from '$lib/components/diagram-words';

// A flowchart whose third line has one arrow too many: mermaid's parser stops there
const BROKEN_ON_LINE_3 = [
	'flowchart LR',
	'  paste[Reader pastes] --> service[ImageService]',
	'  service --> --> store[Image store]',
	'  store --> agent[Agent opens it]'
].join('\n');
// Words that begin no kind of diagram mermaid draws: no parser reads them, so none says where they break
const NO_KIND_OF_DIAGRAM = 'How an image travels, in words';

describe('a diagram the browser cannot draw', () => {
	it('is said by the line it breaks on, and the text mermaid did not expect there', async () => {
		const drawn = await drawDiagram(BROKEN_ON_LINE_3, 'broken-on-a-line');

		expect(diagramNotDrawn(drawn.fault)).toBe('This diagram could not be drawn: line 3, unexpected "-->".');
	});

	it("is said in mermaid's own words where they name no line", async () => {
		const drawn = await drawDiagram(NO_KIND_OF_DIAGRAM, 'no-kind-of-diagram');

		expect(diagramNotDrawn(drawn.fault)).toMatch(/^This diagram could not be drawn: No diagram type detected/);
	});

	it('leaves nothing of what mermaid drew it in on the page', async () => {
		const before = document.body.innerHTML;

		await drawDiagram(BROKEN_ON_LINE_3, 'nothing-left');

		expect(document.body.innerHTML).toBe(before);
	});
});
