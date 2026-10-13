import { describe, it, expect } from 'vitest';
import { paint, type Paint, THEMES } from './stylesheets';

// WCAG AA for text below 18pt: what every word on the page has to reach
const SMALL_TEXT = 4.5;

type Channels = Paint['channels'];

/**
 * What is drawn on what: a text colour, the page's surface under it, and the
 * tints laid over that surface, in order. Each pair is one the stylesheet
 * draws — the token named for the words, on the grounds those words sit on.
 */
const DRAWN: { said: string; text: string; grounds: string[] }[] = [
	{
		said: "a comment's place, on the comment",
		text: '--cr-mark-text',
		grounds: ['--color-base-100', '--cr-mark-tint']
	},
	{ said: "a comment's place, over the field being written", text: '--cr-mark-text', grounds: ['--color-base-200'] },
	{ said: "a marked row's number", text: '--cr-mark-text', grounds: ['--color-base-100', '--cr-mark-tint'] },
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
		grounds: ['--color-base-100', '--cr-mark-tint']
	},
	{ said: 'a placeholder, in the panel', text: '--cr-placeholder', grounds: ['--color-base-100'] },
	{ said: 'a placeholder, in a field being written', text: '--cr-placeholder', grounds: ['--color-base-200'] },
	{ said: 'a placeholder, under a comment', text: '--cr-placeholder', grounds: ['--color-base-100', '--cr-mark-tint'] },
	{
		said: 'a placeholder, under a raised thread',
		text: '--cr-placeholder',
		grounds: ['--color-base-100', '--cr-agent-tint']
	},
	{ said: 'faint words in a comment', text: '--cr-faint', grounds: ['--color-base-100', '--cr-mark-tint'] },
	{ said: 'faint words in a raised thread', text: '--cr-faint', grounds: ['--color-base-100', '--cr-agent-tint'] },
	{
		said: "the agent's place, in its raised thread",
		text: '--cr-agent',
		grounds: ['--color-base-100', '--cr-agent-tint']
	},
	{ said: "an agent's chip, in the panel", text: '--cr-agent', grounds: ['--color-base-100', '--cr-agent-chip'] },
	{
		said: "the other chapters that tell a file, on the header of a story's piece",
		text: '--cr-agent',
		grounds: ['--color-base-200']
	},
	{ said: "a chapter's number, on its node in the contents", text: '--cr-faint', grounds: ['--color-base-200'] },
	{ said: 'what is said of a file in the contents', text: '--cr-faint', grounds: ['--color-base-100'] },
	{ said: 'what a story leaves out, named in its contents', text: '--color-warning', grounds: ['--color-base-200'] },
	{ said: 'the title of a part read through, in the contents', text: '--cr-muted', grounds: ['--color-base-200'] },
	{
		said: 'the check of a part read through, on its node in the contents',
		text: '--cr-done',
		grounds: ['--color-base-200', '--cr-done-soft']
	},
	{ said: 'unread, in a comment', text: '--cr-unread', grounds: ['--color-base-100', '--cr-mark-tint'] },
	{ said: "a control, on a gap's bar", text: '--cr-control', grounds: ['--color-base-200'] },
	{
		said: "the guide's release, on its card",
		text: '--cr-control-text',
		grounds: ['--color-base-200', '--cr-control-tint']
	}
];

// Every colour code is highlighted in, by what it colours
const SYNTAX = ['keyword', 'string', 'comment', 'number', 'type', 'function', 'variable', 'meta'];
// Every ground code is drawn on, by the tints laid over the page under it: a
// marked row's tint takes the place of its change's, it does not stack on it;
// the band behind a changed word lies over its row's tint, marked or not
const ROWS = [
	{ row: 'an unchanged row', tints: [] },
	{ row: 'an added row', tints: ['--cr-add-tint'] },
	{ row: 'a removed row', tints: ['--cr-del-tint'] },
	{ row: 'a marked row', tints: ['--cr-mark-tint'] },
	{ row: 'the band of a word an added row changed', tints: ['--cr-add-tint', '--cr-add-word'] },
	{ row: 'the band of a word a removed row changed', tints: ['--cr-del-tint', '--cr-del-word'] },
	{ row: 'the band of a word a marked added row changed', tints: ['--cr-mark-tint', '--cr-add-word'] },
	{ row: 'the band of a word a marked removed row changed', tints: ['--cr-mark-tint', '--cr-del-word'] }
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

describe('the palette', () => {
	for (const theme of THEMES) {
		for (const pair of [...DRAWN, ...CODE_DRAWN]) {
			it(`reads at ${SMALL_TEXT}:1 in the ${theme} theme: ${pair.said}`, () => {
				const [surface, ...tints] = pair.grounds;
				const ground = tints.reduce((under, tint) => over(paint(tint, theme), under), paint(surface, theme).channels);

				expect(contrast(paint(pair.text, theme).channels, ground)).toBeGreaterThanOrEqual(SMALL_TEXT);
			});
		}
	}
});
