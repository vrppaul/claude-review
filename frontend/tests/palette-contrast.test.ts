import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

// Read as the file it is: a stylesheet imported into a test comes back empty
const tokens = readFileSync(join(__dirname, '../src/styles/tokens.css'), 'utf8');

// WCAG AA for text below 18pt: what every word on the page has to reach
const SMALL_TEXT = 4.5;
const THEMES = ['light', 'dark'] as const;

type Channels = [number, number, number];
/** A colour as tokens.css writes one: its channels, and how much of it covers what lies under it. */
interface Paint {
	channels: Channels;
	alpha: number;
}

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
	{ said: 'a syntax comment, on an unchanged row', text: '--cr-syn-comment', grounds: ['--color-base-100'] },
	{
		said: 'a syntax comment, on an added row',
		text: '--cr-syn-comment',
		grounds: ['--color-base-100', '--cr-add-tint']
	},
	{
		said: 'a syntax comment, on a removed row',
		text: '--cr-syn-comment',
		grounds: ['--color-base-100', '--cr-del-tint']
	},
	{
		said: 'a syntax comment, on a marked row',
		text: '--cr-syn-comment',
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
	{ said: 'unread, in a comment', text: '--cr-unread', grounds: ['--color-base-100', '--cr-mark-tint'] },
	{ said: "a control, on a gap's bar", text: '--cr-control', grounds: ['--color-base-200'] },
	{
		said: "the guide's release, on its card",
		text: '--cr-control-text',
		grounds: ['--color-base-200', '--cr-control-tint']
	}
];

/** The declarations of one block of tokens.css. */
function block(selector: string): Map<string, string> {
	const start = tokens.indexOf(`${selector} {`);
	const body = tokens.slice(start, tokens.indexOf('\n}', start));
	return new Map([...body.matchAll(/(--[a-z0-9-]+):\s*([^;]+);/g)].map((found) => [found[1], found[2].trim()]));
}

/** A token's paint in a theme, following the names it is written in terms of. */
function paint(name: string, theme: Map<string, string>, root: Map<string, string>): Paint {
	const value = theme.get(name) ?? root.get(name);
	if (value === undefined) throw new Error(`${name} is not in tokens.css`);
	const mixed = /^color-mix\(in srgb, var\((--[a-z0-9-]+)\) ([\d.]+)%, transparent\)$/.exec(value);
	if (mixed) return { channels: paint(mixed[1], theme, root).channels, alpha: Number(mixed[2]) / 100 };
	const named = /^var\((--[a-z0-9-]+)\)$/.exec(value);
	if (named) return paint(named[1], theme, root);
	if (value.startsWith('#')) {
		const [red, green, blue] = [1, 3, 5].map((at) => parseInt(value.slice(at, at + 2), 16));
		return { channels: [red, green, blue], alpha: 1 };
	}
	const [red, green, blue, alpha = 1] = [...value.matchAll(/[\d.]+/g)].map((number) => Number(number[0]));
	return { channels: [red, green, blue], alpha };
}

function over(top: Paint, ground: Channels): Channels {
	return ground.map((channel, at) => top.channels[at] * top.alpha + channel * (1 - top.alpha)) as Channels;
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
	const root = block(':root');
	for (const themeName of THEMES) {
		const theme = block(`[data-theme='${themeName}']`);
		for (const pair of DRAWN) {
			it(`reads at ${SMALL_TEXT}:1 in the ${themeName} theme: ${pair.said}`, () => {
				const [surface, ...tints] = pair.grounds;
				const ground = tints.reduce(
					(under, tint) => over(paint(tint, theme, root), under),
					paint(surface, theme, root).channels
				);

				expect(contrast(paint(pair.text, theme, root).channels, ground)).toBeGreaterThanOrEqual(SMALL_TEXT);
			});
		}
	}
});
