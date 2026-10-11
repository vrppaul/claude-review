/**
 * Every icon the review draws, drawn once.
 *
 * An icon is a few lines of a drawing, and copies of the same drawing drift
 * apart one edit at a time; here each has one entry, and `Icon` draws it by
 * name. A circle is written as two arcs, so every icon is paths alone.
 */

/** How an icon is drawn: filled in, or traced with a line this wide. */
type Drawn = { kind: 'filled' } | { kind: 'traced'; width: number };

export interface IconShape {
	viewBox: string;
	paths: readonly string[];
	drawn: Drawn;
}

const FILLED: Drawn = { kind: 'filled' };
// The line most icons are traced with
const TRACED: Drawn = { kind: 'traced', width: 1.5 };

export const ICONS = {
	// Points down; turned for up, or to say something is folded
	chevron: { viewBox: '0 0 12 12', paths: ['M2 4l4 4 4-4z'], drawn: FILLED },
	// Points right; turned to point left
	caret: { viewBox: '0 0 12 12', paths: ['M4.5 2L8 6l-3.5 4z'], drawn: FILLED },
	check: { viewBox: '0 0 12 12', paths: ['M4.6 8.8L2 6.2l.9-.9 1.7 1.7L9.1 2.4l.9.9z'], drawn: FILLED },
	// Lines read in above a hunk, up and down from where they were left out
	expand: { viewBox: '0 0 12 12', paths: ['M6 1L3 4h2v4H3l3 3 3-3H7V4h2z'], drawn: FILLED },
	// A box to tick, as a checkbox is drawn: empty, and ticked
	box: { viewBox: '0 0 12 12', paths: ['M2 2h8v8h-8z'], drawn: { kind: 'traced', width: 1 } },
	ticked: {
		viewBox: '0 0 12 12',
		paths: ['M2 2h8v8h-8z', 'M3.8 6.1l1.5 1.5 2.9-3.2'],
		drawn: { kind: 'traced', width: 1.2 }
	},
	cross: { viewBox: '0 0 12 12', paths: ['M3 3l6 6M9 3l-6 6'], drawn: { kind: 'traced', width: 1.6 } },
	// One version against another: what the diff is taken against
	compare: {
		viewBox: '0 0 16 16',
		paths: ['M2.5 5h9', 'M9 2.5L11.5 5 9 7.5', 'M13.5 11h-9', 'M7 8.5L4.5 11 7 13.5'],
		drawn: TRACED
	},
	reply: { viewBox: '0 0 16 16', paths: ['M4 3v5.5a2 2 0 0 0 2 2h6', 'M9.5 8l3 2.5-3 2.5'], drawn: TRACED },
	conversation: { viewBox: '0 0 16 16', paths: ['M2.5 4.5h11v7h-6l-3 2.5v-2.5h-2z'], drawn: TRACED },
	notice: {
		viewBox: '0 0 16 16',
		paths: ['M8 4.5v4', 'M8 11.2v.3', 'M2 8a6 6 0 1 0 12 0a6 6 0 1 0 -12 0'],
		drawn: TRACED
	},
	compass: {
		viewBox: '0 0 20 20',
		paths: ['M2.5 10a7.5 7.5 0 1 0 15 0a7.5 7.5 0 1 0 -15 0', 'M12.8 7.2l-1.7 3.9-3.9 1.7 1.7-3.9z'],
		drawn: TRACED
	},
	plus: { viewBox: '0 0 20 20', paths: ['M10 3v14M3 10h14'], drawn: TRACED },
	settings: {
		viewBox: '0 0 24 24',
		paths: [
			'M9 12a3 3 0 1 0 6 0a3 3 0 1 0 -6 0',
			'M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z'
		],
		drawn: { kind: 'traced', width: 1.8 }
	}
} as const satisfies Record<string, IconShape>;

export type IconName = keyof typeof ICONS;
