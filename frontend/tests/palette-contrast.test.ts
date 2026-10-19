import { describe, it, expect } from 'vitest';
import { paint, type Paint, type Theme, THEMES } from './stylesheets';

// WCAG AA for text below 18pt: what every word on the page has to reach, in every state it is seen in
const SMALL_TEXT = 4.5;
// How far what the pointer is on, and the one of a set the reader is at, stand off their ground: in both themes, so
// a dark ground is lit too
const LIT = 1.15;
// What a reader needs to see to know where they are, and where the keyboard is (WCAG 1.4.11, 2.4.13)
const NEEDED = 3;

type Channels = Paint['channels'];

/**
 * What is drawn on what: a text colour, the page's surface under it, and the
 * tints laid over that surface, in order. Each pair is one the stylesheet
 * draws — the token named for the words, on the grounds those words sit on.
 */
const DRAWN: { said: string; text: string; grounds: string[] }[] = [
	{ said: 'what a thread asks for, on its card', text: '--cr-mark-text', grounds: ['--color-base-200'] },
	{ said: "a comment's place, over the field being written", text: '--cr-mark-text', grounds: ['--color-base-200'] },
	{ said: "a marked row's number", text: '--cr-mark-text', grounds: ['--color-base-100', '--cr-selected'] },
	{
		said: 'the changed-since chip, on a file header',
		text: '--cr-mark-text',
		grounds: ['--color-base-200', '--cr-mark-tint']
	},
	{
		said: "a thread chip, in the reader's message",
		text: '--cr-mark-text',
		grounds: ['--color-base-100', '--cr-mark-tint', '--cr-mark-chip']
	},
	{
		said: 'M on the current row of the tree',
		text: '--cr-status-modified',
		grounds: ['--color-base-100', '--cr-selected']
	},
	{ said: 'a placeholder, in the panel', text: '--cr-placeholder', grounds: ['--color-base-100'] },
	{ said: 'a placeholder, in a field being written', text: '--cr-placeholder', grounds: ['--color-base-200'] },
	{ said: "a placeholder, on a thread's card", text: '--cr-placeholder', grounds: ['--color-base-200'] },
	{
		said: 'a placeholder, in the field a thread offers a reply in',
		text: '--cr-placeholder',
		grounds: ['--color-base-100']
	},
	{ said: "faint words, on a thread's card", text: '--cr-faint', grounds: ['--color-base-200'] },
	{
		said: "the agent's name, and what a thread it raised asks for, on its card",
		text: '--cr-agent',
		grounds: ['--color-base-200']
	},
	{
		said: 'faint words, on the folded line of a thread the agent raised',
		text: '--cr-faint',
		grounds: ['--color-base-100', '--cr-agent-tint']
	},
	{
		said: "the agent's place, on the folded line of a thread it raised",
		text: '--cr-agent',
		grounds: ['--color-base-100', '--cr-agent-tint']
	},
	{ said: "an agent's chip, in the panel", text: '--cr-agent', grounds: ['--color-base-100', '--cr-agent-chip'] },
	{
		said: "an agent's chip in the panel, pointed at",
		text: '--cr-agent',
		grounds: ['--color-base-100', '--cr-agent-chip', '--cr-hover']
	},
	{
		said: "an agent's chip, on the card of its answer or its work",
		text: '--cr-agent',
		grounds: ['--color-base-200', '--cr-agent-chip']
	},
	{
		said: "an agent's chip on the card of its answer or its work, pointed at",
		text: '--cr-agent',
		grounds: ['--color-base-200', '--cr-agent-chip', '--cr-hover']
	},
	{
		said: "a thread chip in the reader's message, pointed at",
		text: '--cr-mark-text',
		grounds: ['--color-base-100', '--cr-mark-tint', '--cr-mark-chip', '--cr-hover']
	},
	{
		said: 'the changed-since chip on a file header, pointed at',
		text: '--cr-mark-text',
		grounds: ['--color-base-200', '--cr-mark-tint', '--cr-hover']
	},
	{
		said: "the other chapters that tell a file, on the header of a story's piece",
		text: '--cr-agent',
		grounds: ['--color-base-200']
	},
	{ said: "a chapter's number, on its node in the contents", text: '--cr-faint', grounds: ['--color-base-200'] },
	{ said: 'what is said of a file in the contents', text: '--cr-faint', grounds: ['--color-base-100'] },
	{ said: 'what a story leaves out, named in its contents', text: '--color-warning', grounds: ['--color-base-200'] },
	{
		said: 'where to doubt a chapter, heading its warning, pointed at',
		text: '--color-warning',
		grounds: ['--color-base-100', '--cr-warning-tint', '--cr-hover']
	},
	{
		said: 'where to doubt a chapter, heading its warning, a thread hanging under it',
		text: '--color-warning',
		grounds: ['--color-base-100', '--cr-warning-tint', '--cr-selected']
	},
	{
		said: 'what to doubt in a chapter, a thread hanging under it',
		text: '--color-base-content',
		grounds: ['--color-base-100', '--cr-warning-tint', '--cr-selected']
	},
	{ said: 'the title of a part read through, in the contents', text: '--cr-muted', grounds: ['--color-base-200'] },
	{
		said: 'the check of a part read through, on its node in the contents',
		text: '--cr-done',
		grounds: ['--color-base-200', '--cr-done-soft']
	},
	{ said: "unread, on a thread's card", text: '--cr-unread', grounds: ['--color-base-200'] },
	{ said: 'the one act a pane leads to, on its button', text: '--color-primary-content', grounds: ['--cr-control'] },
	{
		said: 'the one act a pane leads to, on its button pointed at',
		text: '--color-primary-content',
		grounds: ['--cr-control', '--cr-hover-on-fill']
	},
	{
		said: 'an act that loses what was written, on its button',
		text: '--color-error-content',
		grounds: ['--color-error']
	},
	{
		said: 'an act that loses what was written, on its button pointed at',
		text: '--color-error-content',
		grounds: ['--color-error', '--cr-hover-on-fill']
	},
	{
		said: 'a filled button, while it cannot be pressed',
		text: '--cr-muted',
		grounds: ['--color-base-300']
	},
	{
		said: 'the narrowed base picked against, its list open',
		text: '--cr-mark-text',
		grounds: ['--color-base-200', '--cr-mark-tint', '--cr-selected']
	},
	{ said: "a control, on a gap's bar", text: '--cr-control-text', grounds: ['--color-base-200'] },
	{
		said: "a control on a gap's bar, pointed at",
		text: '--cr-control-text',
		grounds: ['--color-base-200', '--cr-hover']
	},
	{
		said: "the guide's release, on its card",
		text: '--cr-control-text',
		grounds: ['--color-base-200', '--cr-control-tint']
	},
	{ said: "a blocker's tag, on the warning's fill", text: '--color-warning-content', grounds: ['--color-warning'] },
	{ said: "a count of the reader's threads, on their mark", text: '--color-primary-content', grounds: ['--cr-mark'] }
];

// Every colour words are drawn in, by what they say in it
const WORDS = [
	{ said: 'words', text: '--color-base-content' },
	{ said: 'muted words', text: '--cr-muted' },
	{ said: 'faint words', text: '--cr-faint' },
	{ said: 'a line number', text: '--cr-gutter-fg' },
	{ said: "the reader's mark in words", text: '--cr-mark-text' },
	{ said: "the agent's words", text: '--cr-agent' },
	{ said: 'what was added', text: '--cr-add-text' },
	{ said: 'what was taken away', text: '--cr-del-text' },
	{ said: "a modified file's letter", text: '--cr-status-modified' },
	{ said: 'a warning', text: '--color-warning' },
	{ said: 'an error', text: '--color-error' }
];
// The surfaces words stand on: the page's own, and the one a bar, a pane or a card is raised on
const SURFACES = [
	{ said: "the page's ground", surface: '--color-base-100' },
	{ said: 'a raised surface', surface: '--color-base-200' }
];
// What a state lays over a surface under the words of what is in it: nothing at rest, the pointer's light, and
// the reader's mark on the one of a set they are at, which the pointer leaves as it is
const AT_REST_OR_POINTED_AT = [
	{ said: 'at rest', fills: [] },
	{ said: 'pointed at', fills: ['--cr-hover'] }
];
const STATES = [...AT_REST_OR_POINTED_AT, { said: 'selected', fills: ['--cr-selected'] }];
// Every colour of words, on every surface, in every state
const WORDS_IN_EVERY_STATE = WORDS.flatMap(({ said, text }) =>
	SURFACES.flatMap(({ said: on, surface }) =>
		STATES.map(({ said: state, fills }) => ({
			said: `${said}, on ${on}, ${state}`,
			text,
			grounds: [surface, ...fills]
		}))
	)
);
// A segmented control's track, under the words of its segments: muted, and plain on the one pressed
const ON_A_TRACK = ['--cr-muted', '--color-base-content'].flatMap((text) =>
	STATES.map(({ said: state, fills }) => ({
		said: `a segment's words ${text}, on its track, ${state}`,
		text,
		grounds: ['--color-base-300', ...fills]
	}))
);
// A line's number, on the row it numbers, in the row's colour; pointed at, it is lit as whatever can be pressed
const NUMBERED_ROWS = [
	{ row: 'an unchanged row', text: '--cr-gutter-fg', tints: [] },
	{ row: 'an added row', text: '--cr-add-text', tints: ['--cr-add-tint'] },
	{ row: 'a removed row', text: '--cr-del-text', tints: ['--cr-del-tint'] },
	{ row: 'a marked row', text: '--cr-mark-text', tints: ['--cr-selected'] }
];
const LINE_NUMBERS = NUMBERED_ROWS.flatMap(({ row, text, tints }) =>
	AT_REST_OR_POINTED_AT.map(({ said: state, fills }) => ({
		said: `the number of ${row}, ${state}`,
		text,
		grounds: ['--color-base-100', ...tints, ...fills]
	}))
);

// The grounds of a notice that are washes, over the page's: a warning's, and one of the reader's own doing. On each
// stand its words and what can be done about it, a quiet button in the same words, at rest and under the pointer;
// and why doing it failed, in the error's words, which nothing lights
const NOTICE_WASHES = [
	{ said: "a warning's notice", grounds: ['--color-base-100', '--cr-warning-tint'] },
	{ said: "a notice of the reader's own doing", grounds: ['--color-base-100', '--cr-mark-soft'] }
];
const ON_A_NOTICE = NOTICE_WASHES.flatMap(({ said: on, grounds }) => [
	...AT_REST_OR_POINTED_AT.map(({ said: state, fills }) => ({
		said: `the words of ${on} and of a quiet button on it, ${state}`,
		text: '--color-base-content',
		grounds: [...grounds, ...fills]
	})),
	{ said: `why doing something about ${on} failed`, text: '--color-error', grounds }
]);

// Every colour code is highlighted in, by what it colours
const SYNTAX = ['keyword', 'string', 'comment', 'number', 'type', 'function', 'variable', 'meta'];
// Every ground code is drawn on, by the tints laid over the page under it: a
// marked row's tint takes the place of its change's, it does not stack on it;
// the band behind a changed word lies over its row's tint, marked or not
const ROWS = [
	{ row: 'an unchanged row', tints: [] },
	{ row: 'an added row', tints: ['--cr-add-tint'] },
	{ row: 'a removed row', tints: ['--cr-del-tint'] },
	{ row: 'a marked row', tints: ['--cr-selected'] },
	{ row: 'the band of a word an added row changed', tints: ['--cr-add-tint', '--cr-add-word'] },
	{ row: 'the band of a word a removed row changed', tints: ['--cr-del-tint', '--cr-del-word'] },
	{ row: 'the band of a word a marked added row changed', tints: ['--cr-selected', '--cr-add-word'] },
	{ row: 'the band of a word a marked removed row changed', tints: ['--cr-selected', '--cr-del-word'] }
];
// Highlighted code, on every ground it is drawn on
const CODE_DRAWN = SYNTAX.flatMap((colour) =>
	ROWS.map(({ row, tints }) => ({
		said: `code coloured as ${colour}, on ${row}`,
		text: `--cr-syn-${colour}`,
		grounds: ['--color-base-100', ...tints]
	}))
);

/**
 * A tint laid over a ground, in whole channels, as a browser paints each
 * layer: a pair that reads at 4.5:1 only before rounding is drawn below it.
 */
function over(top: Paint, ground: Channels): Channels {
	return ground.map((channel, at) => Math.round(top.channels[at] * top.alpha + channel * (1 - top.alpha))) as Channels;
}

function luminance(channels: Channels): number {
	const [red, green, blue] = channels.map((channel) => {
		const share = channel / 255;
		return share <= 0.04045 ? share / 12.92 : ((share + 0.055) / 1.055) ** 2.4;
	});
	return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

function contrast(one: Channels, other: Channels): number {
	const [lighter, darker] = [luminance(one), luminance(other)].sort((first, second) => second - first);
	return (lighter + 0.05) / (darker + 0.05);
}

/** A surface with the tints laid over it, in order, as the page paints them. */
function laid(grounds: string[], theme: Theme): Channels {
	const [surface, ...tints] = grounds;
	return tints.reduce((under, tint) => over(paint(tint, theme), under), paint(surface, theme).channels);
}

describe('the palette', () => {
	for (const theme of THEMES) {
		for (const pair of [
			...DRAWN,
			...WORDS_IN_EVERY_STATE,
			...ON_A_TRACK,
			...LINE_NUMBERS,
			...CODE_DRAWN,
			...ON_A_NOTICE
		]) {
			it(`reads at ${SMALL_TEXT}:1 in the ${theme} theme: ${pair.said}`, () => {
				expect(contrast(paint(pair.text, theme).channels, laid(pair.grounds, theme))).toBeGreaterThanOrEqual(
					SMALL_TEXT
				);
			});
		}
	}
});

// A warning's wash on the page, which a chapter's doubt stands on
const WARNING_WASH = ['--color-base-100', '--cr-warning-tint'];
// Every surface a state is drawn on: the page's, a raised one, and a segmented control's track
const STATE_SURFACES = [...SURFACES, { said: 'a track', surface: '--color-base-300' }];
// What the pointer lights, and the light it lays: whatever stands on a surface, and a filled button, whose
// saturated fill moves less under the same light and so takes more of it
const POINTED_AT = [
	...STATE_SURFACES.map(({ said, surface }) => ({ said, surface, light: '--cr-hover' })),
	{ said: "the primary button's own fill", surface: '--cr-control', light: '--cr-hover-on-fill' },
	{ said: 'the fill of a button that loses what was written', surface: '--color-error', light: '--cr-hover-on-fill' }
];

describe('the states of whatever can be pressed', () => {
	for (const theme of THEMES) {
		for (const { said: on, surface, light } of POINTED_AT) {
			it(`what the pointer is on stands off ${on} at ${LIT}:1 in the ${theme} theme`, () => {
				expect(contrast(laid([surface, light], theme), laid([surface], theme))).toBeGreaterThanOrEqual(LIT);
			});
		}

		for (const { said: on, surface } of STATE_SURFACES) {
			it(`the one of a set the reader is at stands off ${on} at ${LIT}:1 in the ${theme} theme`, () => {
				expect(contrast(laid([surface, '--cr-selected'], theme), laid([surface], theme))).toBeGreaterThanOrEqual(LIT);
			});

			it(`the edge of the one of a set the reader is at reads at ${NEEDED}:1 against its fill and ${on}, in the ${theme} theme`, () => {
				const edge = paint('--cr-selected-edge', theme).channels;

				expect(contrast(edge, laid([surface, '--cr-selected'], theme))).toBeGreaterThanOrEqual(NEEDED);
				expect(contrast(edge, laid([surface], theme))).toBeGreaterThanOrEqual(NEEDED);
			});

			it(`the ring round what holds the keyboard reads at ${NEEDED}:1 on ${on}, in the ${theme} theme`, () => {
				expect(contrast(paint('--cr-focus-ring', theme).channels, laid([surface], theme))).toBeGreaterThanOrEqual(
					NEEDED
				);
			});
		}

		it(`a block a thread hangs under inside a warning stands off the warning's wash at ${LIT}:1, its edge at ${NEEDED}:1, in the ${theme} theme`, () => {
			const wash = laid(WARNING_WASH, theme);
			const selected = laid([...WARNING_WASH, '--cr-selected'], theme);
			const edge = paint('--cr-selected-edge', theme).channels;

			expect(contrast(selected, wash)).toBeGreaterThanOrEqual(LIT);
			expect(Math.min(contrast(edge, selected), contrast(edge, wash))).toBeGreaterThanOrEqual(NEEDED);
		});

		for (const { said: on, grounds } of NOTICE_WASHES) {
			it(`what the pointer is on stands off ${on} at ${LIT}:1 in the ${theme} theme`, () => {
				expect(contrast(laid([...grounds, '--cr-hover'], theme), laid(grounds, theme))).toBeGreaterThanOrEqual(LIT);
			});

			it(`the ring round what holds the keyboard reads at ${NEEDED}:1 on ${on}, in the ${theme} theme`, () => {
				expect(contrast(paint('--cr-focus-ring', theme).channels, laid(grounds, theme))).toBeGreaterThanOrEqual(NEEDED);
			});
		}
	}
});
