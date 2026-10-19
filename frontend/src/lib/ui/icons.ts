/**
 * Every icon the review draws, drawn once.
 *
 * An icon is a few lines of a drawing, and copies of the same drawing drift
 * apart one edit at a time; here each has one entry, and `Icon` draws it by
 * name. A circle is written as two arcs, so every icon is paths alone.
 */

/** How an icon is drawn: filled in, or traced with a line this wide. */
type HowDrawn = { kind: 'filled' } | { kind: 'traced'; width: number };

export interface IconShape {
	viewBox: string;
	paths: readonly string[];
	drawn: HowDrawn;
}

const FILLED: HowDrawn = { kind: 'filled' };
// The line most icons are traced with
const TRACED: HowDrawn = { kind: 'traced', width: 1.5 };
// The finer line of what can be done to a thread, at the size it is drawn at there
const TRACED_FINE: HowDrawn = { kind: 'traced', width: 1.4 };

export const ICONS = {
	// An arrow coming round to where it began: a round of the review, and the one a story was told in
	round: { viewBox: '0 0 16 16', paths: ['M13 8a5 5 0 1 1-1.5-3.6', 'M13 2.5v3h-3'], drawn: TRACED },
	// An open book: the change read as the story told of it, and the agent that tells it, where it speaks in a thread
	story: {
		viewBox: '0 0 16 16',
		paths: ['M8 4.5C6.6 3.4 4.6 3 2 3v9.5c2.6 0 4.6.4 6 1.5 1.4-1.1 3.4-1.5 6-1.5V3c-2.6 0-4.6.4-6 1.5Z', 'M8 4.5V14'],
		drawn: TRACED
	},
	// A head and shoulders: the reader, where they speak in a thread
	person: {
		viewBox: '0 0 16 16',
		paths: ['M5.4 5.5a2.6 2.6 0 1 0 5.2 0a2.6 2.6 0 1 0 -5.2 0', 'M3 13.5c.8-2.6 2.7-3.8 5-3.8s4.2 1.2 5 3.8'],
		drawn: TRACED
	},
	// A pencil: rewriting what was said
	pencil: { viewBox: '0 0 16 16', paths: ['M10.5 3 13 5.5 6 12.5H3.5V10z'], drawn: TRACED_FINE },
	// A bin: deleting what was said
	trash: { viewBox: '0 0 16 16', paths: ['M3 4.5h10M6.5 4.5V3h3v1.5M4.5 4.5l.7 8.5h5.6l.7-8.5'], drawn: TRACED_FINE },
	// A stack of files: the change read file by file
	files: { viewBox: '0 0 16 16', paths: ['M5.5 2.5h4.5l3 3v8H5.5z', 'M10 2.5v3h3', 'M3 5v9.5h7'], drawn: TRACED },
	// Points down; turned for up, left or right, or to say something is folded
	chevron: { viewBox: '0 0 12 12', paths: ['M2 4l4 4 4-4z'], drawn: FILLED },
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
	// A ring of six dashes: what has not happened yet, and is waited for
	awaited: {
		viewBox: '0 0 16 16',
		paths: [
			'M13.5 8A5.5 5.5 0 0 1 12.76 10.75',
			'M10.75 12.76A5.5 5.5 0 0 1 8 13.5',
			'M5.25 12.76A5.5 5.5 0 0 1 3.24 10.75',
			'M2.5 8A5.5 5.5 0 0 1 3.24 5.25',
			'M5.25 3.24A5.5 5.5 0 0 1 8 2.5',
			'M10.75 3.24A5.5 5.5 0 0 1 12.76 5.25'
		],
		drawn: { kind: 'traced', width: 1.6 }
	},
	// One version against another: what the diff is taken against
	compare: {
		viewBox: '0 0 16 16',
		paths: ['M2.5 5h9', 'M9 2.5L11.5 5 9 7.5', 'M13.5 11h-9', 'M7 8.5L4.5 11 7 13.5'],
		drawn: TRACED
	},
	reply: { viewBox: '0 0 16 16', paths: ['M4 3v5.5a2 2 0 0 0 2 2h6', 'M9.5 8l3 2.5-3 2.5'], drawn: TRACED },
	// A speech bubble: a word with the agent, in its panel or about a block of the story
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

/**
 * What an icon says by its colour, where it says more than the words it stands in:
 * - done: something done — a file viewed, a thread settled, a step taken
 * - danger: what destroys, on the button that does it
 * - agent: the agent's own, and what it is still to do
 * - warning: what the reader is warned of
 * - reader: in the colour of the reader's controls — the one of a list in force, the way into the tour
 * - absent: a mark standing for what is not there yet, on a surface's grey
 */
export type IconTone = 'done' | 'danger' | 'agent' | 'warning' | 'reader' | 'absent';
