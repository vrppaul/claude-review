/**
 * How the agent's panel stands as a column (lib/ui Column): on the right of
 * what is read, beside it, as the panel does whole and as what stands in its
 * place does where the panel could not be drawn, so the review beside it does
 * not move.
 */
export const AGENT_COLUMN = {
	side: 'right',
	landmark: 'aside',
	label: 'The agent',
	resizing: 'Resize the panel'
} as const;
