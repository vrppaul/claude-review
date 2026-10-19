import { describe, it, expect } from 'vitest';
import { styleRules } from './stylesheets';

// What of a selector says what a rule is drawn without, which is set aside before asking what the rule draws:
// `:not(:disabled)` draws nothing of what cannot be pressed
const DRAWN_WITHOUT = /:not\((?:[^()]|\([^()]*\))*\)/g;

/**
 * Each state of whatever can be pressed or picked: what in a selector says a
 * rule draws it, and every token it is painted with, each written once in
 * tokens.css for both themes. A rule is taken to draw the first state its
 * selector names, so a part that is lit its own way stands before the state
 * it is lit in.
 */
const STATES = [
	{
		state: 'a filled button under the pointer, lit by the light for a saturated fill',
		named: /\.cr-ui-filled\b.*:hover\b/,
		tokens: ['--cr-hover-on-fill']
	},
	{
		state: "a column's grip under the pointer, a target too thin to find by a light: in the selected edge's colour",
		named: /\.cr-grip\b.*:hover\b/,
		tokens: ['--cr-selected-edge']
	},
	{
		state: 'under the pointer, or holding the keyboard somewhere inside',
		named: /:hover\b|:focus-within\b/,
		tokens: ['--cr-hover']
	},
	{
		state: 'holding the keyboard',
		named: /:focus(?:-visible)?(?![\w-])/,
		tokens: ['--cr-focus-ring']
	},
	{
		state: 'a filled button whose pane is open: its edge in its own words, which the mark would vanish on',
		named: /\.cr-ui-filled\b.*\[aria-(?:pressed|expanded)\b/,
		tokens: ['--cr-shadow-selected-foot-on-fill']
	},
	{
		state: 'pressed down, or its pane open: the tint over its ground, the edge at its foot, a segment in plain words',
		named: /\[aria-(?:pressed|expanded)\b/,
		tokens: ['--cr-selected', '--cr-shadow-selected-foot', '--color-base-content']
	},
	{
		state: 'the one of a set the reader is at: the tint, the edge at its start, a marked line its number in the mark',
		named: /\.cr-(?:ui-row-current|ui-band-current|row-marked|cell-marked|edge-marked)\b/,
		tokens: ['--cr-selected', '--cr-selected-edge', '--cr-shadow-selected-start', '--cr-mark-text']
	},
	{
		state: 'what cannot be pressed: muted words, and a filled button on a surface',
		named: /:disabled\b|\[aria-disabled\b/,
		tokens: ['--cr-muted', '--color-base-300']
	},
	{
		state: 'what the reader has finished with, stepping back in faint words',
		named: /\.cr-(?:viewed|ui-row-viewed|step-changed)\b/,
		tokens: ['--cr-faint']
	},
	{
		state: 'a box ticked: something done',
		named: /:checked\b/,
		tokens: ['--cr-done']
	}
];

// A declaration that paints — a box's ground, a shadow, an outline or an edge, on any side, or its words — and
// what it is set to
const PAINTING =
	/(?:^|[;{\s])(color|background(?:-color|-image)?|box-shadow|outline(?:-color)?|border(?:-(?:top|right|bottom|left|block|inline)(?:-(?:start|end))?)?(?:-color)?)\s*:\s*([^;]+)/g;
// A token a value names
const TOKEN = /var\((--[a-z0-9-]+)\)/g;

// Every token a rule drawing a state paints with: the rule, the first state it names, and what it paints
const paintedInStates = styleRules().flatMap(({ selectors, declarations }) =>
	STATES.filter(({ named }) => named.test(selectors.replaceAll(DRAWN_WITHOUT, '')))
		.slice(0, 1)
		.flatMap((drawn) =>
			[...declarations.matchAll(PAINTING)].flatMap(([, property, value]) =>
				[...value.matchAll(TOKEN)].map(([, token]) => ({
					selectors: selectors.replaceAll(/\s+/g, ' '),
					...drawn,
					property,
					token
				}))
			)
		)
);

/**
 * A state is painted only by its own token, so whatever draws one is seen in
 * both themes and means one thing: the hover the page took from DaisyUI
 * darkened its ground, and a dark ground darkened stays dark (1.02:1); a
 * pressed segment, a current row or a viewed file painted with a token of
 * another state passes every other check. So the stylesheet is asked itself.
 */
describe('a rule of the stylesheet that draws a state', () => {
	it.each(paintedInStates)('$selectors, $state, paints its $property with $token', ({ tokens, token }) => {
		expect(tokens).toContain(token);
	});
});
