import { describe, it, expect } from 'vitest';
import { LineSelection } from '$lib/components/line-selection.svelte';
import { contextLine } from './diff';

// The most lines the review takes in one comment, as the server would say it
const LONGEST_RANGE = 3;
// Where the lines in these tests stand among the rows: line 10 is the first
const FIRST_LINE = 10;

function selection() {
	return new LineSelection({
		mayCommentOnRemoved: () => true,
		longestRange: () => LONGEST_RANGE,
		rowOf: (_side, lineNumber) => lineNumber - FIRST_LINE
	});
}

describe('selecting lines to comment on', () => {
	it('stops a drag at the most lines one comment may cover', () => {
		const lines = selection();

		lines.handleMouseDown(contextLine(10, 10, 'start'), 0);
		lines.handleMouseEnter(contextLine(20, 20, 'far below'), 10);
		lines.handleMouseUp();

		expect(lines.commentingAt).toMatchObject({ startLine: 10, endLine: 12 });
	});

	it('stops a drag upwards the same way', () => {
		const lines = selection();

		lines.handleMouseDown(contextLine(20, 20, 'start'), 10);
		lines.handleMouseEnter(contextLine(10, 10, 'far above'), 0);
		lines.handleMouseUp();

		expect(lines.commentingAt).toMatchObject({ startLine: 18, endLine: 20 });
	});

	it('opens the comment under the row the drag stopped at, however far past it the pointer went', () => {
		const lines = selection();

		lines.handleMouseDown(contextLine(10, 10, 'start'), 0);
		lines.handleMouseEnter(contextLine(20, 20, 'far below'), 10);
		lines.handleMouseUp();

		expect(lines.commentingAt?.opensBelow).toBe(12 - FIRST_LINE);
	});

	it('shows the drag as far as it will go', () => {
		const lines = selection();

		lines.handleMouseDown(contextLine(10, 10, 'start'), 0);
		lines.handleMouseEnter(contextLine(20, 20, 'far below'), 10);

		expect(lines.isHighlighted('new', 12)).toBe(true);
		expect(lines.isHighlighted('new', 13)).toBe(false);
	});
});
