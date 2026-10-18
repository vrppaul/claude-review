import { describe, it, expect } from 'vitest';
import { styleRules } from './stylesheets';

// What in a selector says it draws a state: under the pointer, pressed, holding the keyboard or holding it
// inside, and what the page says of one of a set — pressed down, picked, open, where the reader is
const STATE = /:(?:hover|active|focus|focus-visible|focus-within)\b|\[aria-(?:pressed|selected|expanded|current)\b/;
// A declaration that paints a box — its ground, a shadow, an outline or an edge, on any side — and what it is set to
const PAINTING =
	/(?:^|[;{\s])(background(?:-color|-image)?|box-shadow|outline(?:-color)?|border(?:-(?:top|right|bottom|left|block|inline)(?:-(?:start|end))?)?(?:-color)?)\s*:\s*([^;]+)/g;
// A token a value names
const TOKEN = /var\((--[a-z0-9-]+)\)/g;
// The tokens a state is painted with, each written once in tokens.css for both themes
const STATE_TOKENS = [
	'--cr-hover',
	'--cr-selected',
	'--cr-shadow-selected-start',
	'--cr-shadow-selected-foot',
	'--cr-focus-ring'
];

// Every token a rule drawing a state paints with, with the rule and what it paints
const paintedInStates = styleRules()
	.filter(({ selectors }) => STATE.test(selectors))
	.flatMap(({ selectors, declarations }) =>
		[...declarations.matchAll(PAINTING)].flatMap(([, property, value]) =>
			[...value.matchAll(TOKEN)].map(([, token]) => ({ selectors: selectors.replaceAll(/\s+/g, ' '), property, token }))
		)
	);

/**
 * A state is painted only by its token, so whatever draws one is seen in both
 * themes: the hover the page took from DaisyUI darkened its ground, and a
 * dark ground darkened stays dark (1.02:1). A rule that paints a state with a
 * colour of its own would pass every other check, so the stylesheet is asked
 * itself.
 */
describe('a rule of the stylesheet that draws a state', () => {
	it.each(paintedInStates)('$selectors paints its $property with a state token, not $token', ({ token }) => {
		expect(STATE_TOKENS).toContain(token);
	});
});
