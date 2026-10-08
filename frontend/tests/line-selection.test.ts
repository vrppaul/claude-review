import { describe, it, expect } from 'vitest';
import { createLineSelection } from '$lib/utils/line-selection.svelte';
import { contextLine } from './diff';

// The most lines the review takes in one comment, as the server would say it
const LONGEST_RANGE = 3;

function selection() {
	return createLineSelection({ mayCommentOnRemoved: () => true, longestRange: () => LONGEST_RANGE });
}

describe('selecting lines to comment on', () => {
	it('stops a drag at the most lines one comment may cover', () => {
		const lines = selection();

		lines.handleMouseDown(contextLine(10, 10, 'start'), 0);
		lines.handleMouseEnter(contextLine(20, 20, 'far below'), 10);
		lines.handleMouseUp();

		expect(lines.commentingAt).toMatchObject({ line: 10, endLine: 12 });
	});

	it('stops a drag upwards the same way', () => {
		const lines = selection();

		lines.handleMouseDown(contextLine(20, 20, 'start'), 10);
		lines.handleMouseEnter(contextLine(10, 10, 'far above'), 0);
		lines.handleMouseUp();

		expect(lines.commentingAt).toMatchObject({ line: 18, endLine: 20 });
	});

	it('shows the drag as far as it will go', () => {
		const lines = selection();

		lines.handleMouseDown(contextLine(10, 10, 'start'), 0);
		lines.handleMouseEnter(contextLine(20, 20, 'far below'), 10);

		expect(lines.isHighlighted('new', 12)).toBe(true);
		expect(lines.isHighlighted('new', 13)).toBe(false);
	});
});
