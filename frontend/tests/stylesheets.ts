/**
 * The review's stylesheets read as the files they are, for the tests that
 * ask what colour something is drawn in, or what a rule declares: jsdom
 * applies none of them, and a stylesheet imported into a test comes back
 * empty.
 *
 * A token is followed through tokens.css to the colour it is in a theme. An
 * element's colour is the token its own classes name: a `cr-` class by its
 * rule in ui.css or main.css — the last such rule wins, as the classes are of one
 * weight — and otherwise a utility that names a token, `text-(--…)` or
 * `bg-(--…)`, which a `cr-` class always outranks.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const STYLES = join(__dirname, '../src/styles');
const tokens = readFileSync(join(STYLES, 'tokens.css'), 'utf8');
// The stylesheets the page is drawn with besides the tokens: the component library's, then the page's own, in the
// order main.css imports them
const DRAWN_WITH = ['ui.css', 'main.css'] as const;
type Sheet = (typeof DRAWN_WITH)[number];
// The custom property a declaration sets
const DECLARED = /(?:^|[;{\s])(--[a-z0-9-]+)\s*:/g;

export const THEMES = ['light', 'dark'] as const;
export type Theme = (typeof THEMES)[number];

type Channels = [number, number, number];
/** A colour as tokens.css writes one: its channels, and how much of it covers what lies under it. */
export interface Paint {
	channels: Channels;
	alpha: number;
}

/** What of an element is drawn in a colour: its words, the ground under them, or the edge round it. */
export type Drawn = 'color' | 'background' | 'border-color';

// The utility that draws each part in a token, and the token it names
const UTILITIES: Record<Drawn, RegExp> = {
	color: /^text-\((--[a-z0-9-]+)\)$/,
	background: /^bg-\((--[a-z0-9-]+)\)$/,
	'border-color': /^border-\((--[a-z0-9-]+)\)$/
};

/** The declarations of one block of tokens.css. */
function block(selector: string): Map<string, string> {
	const start = tokens.indexOf(`${selector} {`);
	const body = tokens.slice(start, tokens.indexOf('\n}', start));
	return new Map([...body.matchAll(/(--[a-z0-9-]+):\s*([^;]+);/g)].map((found) => [found[1], found[2].trim()]));
}

const ROOT = block(':root');
// What tokens.css hands Tailwind's theme: the breakpoints, which the built stylesheet sets on the page's root
const THEME = block('@theme static');
const THEME_BLOCKS: Record<Theme, Map<string, string>> = {
	light: block("[data-theme='light']"),
	dark: block("[data-theme='dark']")
};

/** A variable of the theme tokens.css hands Tailwind, as written there: a breakpoint's width, say. */
export function themeVariable(name: string): string {
	const value = THEME.get(name);
	if (value === undefined) throw new Error(`${name} is not in the theme tokens.css hands Tailwind`);
	return value;
}

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

/** Every custom property tokens.css declares, in either theme or in neither. */
export function tokenNames(): Set<string> {
	return new Set([...tokens.matchAll(DECLARED)].map(([, name]) => name));
}

/** A rule of the stylesheets as it is written: the sheet it is in, what it is a rule for, and what stands between its braces. */
export interface StyleRule {
	sheet: Sheet;
	selectors: string;
	declarations: string;
}

/** The rules of one sheet, in its order: one written inside an `@media` among them. Comments are taken out, so that what stands before a rule is its selectors alone. */
function parsed(sheet: Sheet): StyleRule[] {
	const written = readFileSync(join(STYLES, sheet), 'utf8').replaceAll(/\/\*[\s\S]*?\*\//g, '');
	return [...written.matchAll(/([^{}]+)\{([^{}]*)\}/g)].map(([, selectors, declarations]) => ({
		sheet,
		selectors: selectors.trim(),
		declarations
	}));
}

// Each sheet's rules, read once
const RULES_OF: Record<Sheet, StyleRule[]> = { 'ui.css': parsed('ui.css'), 'main.css': parsed('main.css') };

/** The rules of one sheet, in its order. */
export function rulesOf(sheet: Sheet): StyleRule[] {
	return RULES_OF[sheet];
}

/** Every rule of ui.css and main.css, in the order the page has them. */
export function styleRules(): StyleRule[] {
	return DRAWN_WITH.flatMap(rulesOf);
}

/** The custom properties a rule declares. */
export function customPropertiesOf(rule: StyleRule): string[] {
	return [...rule.declarations.matchAll(DECLARED)].map(([, name]) => name);
}

/** Every rule of the stylesheets that sets a part's colour by a token, for a selector of one class alone: the class and the token, in the file's order. */
function classRules(drawn: Drawn): { className: string; token: string }[] {
	return styleRules().flatMap(({ selectors, declarations }) => {
		const token = new RegExp(`(?:^|[;\\s])${drawn}:\\s*var\\((--[a-z0-9-]+)\\)`).exec(declarations)?.[1];
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
