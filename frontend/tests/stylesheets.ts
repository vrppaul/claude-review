/**
 * The review's stylesheets read as the files they are, for the tests that
 * ask what colour something is drawn in: jsdom applies none of them, and a
 * stylesheet imported into a test comes back empty.
 *
 * A token is followed through tokens.css to the colour it is in a theme. An
 * element's colour is the token its own classes name: a `cr-` class by its
 * rule in main.css — the last such rule wins, as the classes are of one
 * weight — and otherwise a utility that names a token, `text-(--…)` or
 * `bg-(--…)`, which a `cr-` class always outranks.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const STYLES = join(__dirname, '../src/styles');
const tokens = readFileSync(join(STYLES, 'tokens.css'), 'utf8');
// Its comments taken out, so that what stands before a rule is its selectors alone
const main = readFileSync(join(STYLES, 'main.css'), 'utf8').replaceAll(/\/\*[\s\S]*?\*\//g, '');

export const THEMES = ['light', 'dark'] as const;
export type Theme = (typeof THEMES)[number];

type Channels = [number, number, number];
/** A colour as tokens.css writes one: its channels, and how much of it covers what lies under it. */
export interface Paint {
	channels: Channels;
	alpha: number;
}

/** What of an element is drawn in a colour: its words, or the ground under them. */
export type Drawn = 'color' | 'background';

// The utility that draws each part in a token, and the token it names
const UTILITIES: Record<Drawn, RegExp> = { color: /^text-\((--[a-z0-9-]+)\)$/, background: /^bg-\((--[a-z0-9-]+)\)$/ };

/** The declarations of one block of tokens.css. */
function block(selector: string): Map<string, string> {
	const start = tokens.indexOf(`${selector} {`);
	const body = tokens.slice(start, tokens.indexOf('\n}', start));
	return new Map([...body.matchAll(/(--[a-z0-9-]+):\s*([^;]+);/g)].map((found) => [found[1], found[2].trim()]));
}

const ROOT = block(':root');
const THEME_BLOCKS: Record<Theme, Map<string, string>> = {
	light: block("[data-theme='light']"),
	dark: block("[data-theme='dark']")
};

/** A token's paint in a theme, following the names it is written in terms of. */
export function paint(token: string, theme: Theme): Paint {
	const value = THEME_BLOCKS[theme].get(token) ?? ROOT.get(token);
	if (value === undefined) throw new Error(`${token} is not in tokens.css`);
	const mixed = /^color-mix\(in srgb, var\((--[a-z0-9-]+)\) ([\d.]+)%, transparent\)$/.exec(value);
	if (mixed) return { channels: paint(mixed[1], theme).channels, alpha: Number(mixed[2]) / 100 };
	const named = /^var\((--[a-z0-9-]+)\)$/.exec(value);
	if (named) return paint(named[1], theme);
	if (value.startsWith('#')) {
		const [red, green, blue] = [1, 3, 5].map((at) => parseInt(value.slice(at, at + 2), 16));
		return { channels: [red, green, blue], alpha: 1 };
	}
	const [red, green, blue, alpha = 1] = [...value.matchAll(/[\d.]+/g)].map((number) => Number(number[0]));
	return { channels: [red, green, blue], alpha };
}

/** Every rule of main.css that sets a part's colour by a token, for a selector of one class alone: the class and the token, in the file's order. */
function classRules(drawn: Drawn): { className: string; token: string }[] {
	const rules = [...main.matchAll(/([^{}]+)\{([^{}]*)\}/g)];
	return rules.flatMap(([, selectors, body]) => {
		const token = new RegExp(`(?:^|[;\\s])${drawn}:\\s*var\\((--[a-z0-9-]+)\\)`).exec(body)?.[1];
		if (token === undefined) return [];
		return selectors
			.split(',')
			.map((selector) => /^\.([a-z0-9-]+)$/.exec(selector.trim())?.[1])
			.filter((className) => className !== undefined)
			.map((className) => ({ className, token }));
	});
}

/** The token an element's own classes draw a part of it in. */
function tokenDrawn(element: Element, drawn: Drawn): string {
	const classes = [...element.classList];
	const byRule = classRules(drawn).findLast(({ className }) => classes.includes(className));
	if (byRule) return byRule.token;
	const byUtility = classes.map((className) => UTILITIES[drawn].exec(className)?.[1]).find((token) => token);
	if (byUtility === undefined) throw new Error(`nothing draws the ${drawn} of ${element.outerHTML} in a token`);
	return byUtility;
}

/** The colour a part of an element is drawn in, in a theme. */
export function colourDrawn(element: Element, drawn: Drawn, theme: Theme): Paint {
	return paint(tokenDrawn(element, drawn), theme);
}
