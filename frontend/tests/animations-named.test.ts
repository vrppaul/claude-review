import { describe, it, expect } from 'vitest';
import { sheetsAsWritten, styleRules } from './stylesheets';

// Where a stylesheet names the motion of its keyframes
const KEYFRAMES = /@keyframes\s+([\w-]+)/g;
// What an animation is set to, by its shorthand or by its name alone
const ANIMATED = /(?:^|[;\s])animation(?:-name)?\s*:\s*([^;]+)/g;
// The name of some keyframes in what an animation is set to: the page names them as it names its classes, `cr-`,
// and a token's name, `--cr-`, is no such name
const KEYFRAMES_NAMED = /(?<![\w-])cr-[\w-]+/g;

// The keyframes the stylesheets define, by name
const defined = new Set(sheetsAsWritten().flatMap((sheet) => [...sheet.matchAll(KEYFRAMES)].map(([, name]) => name)));

// The keyframes each rule animates by, with the rule's selectors
const animatedBy = styleRules().flatMap(({ selectors, declarations }) =>
	[...declarations.matchAll(ANIMATED)].flatMap(([, value]) =>
		[...value.matchAll(KEYFRAMES_NAMED)].map(([name]) => ({ selectors: selectors.replaceAll(/\s+/g, ' '), name }))
	)
);

/**
 * A rule animates by keyframes a stylesheet defines: the page's sketch of a
 * story breathes by the library's breath (`cr-breathe`, ui.css), and a
 * renamed or moved `@keyframes` would leave it still, with no word from the
 * browser.
 */
describe('a rule of the stylesheet that animates', () => {
	it('names some keyframes', () => {
		expect(animatedBy.length).toBeGreaterThan(0);
	});

	it.each(animatedBy)('$selectors animates by $name, which the stylesheets define', ({ name }) => {
		expect(defined).toContain(name);
	});
});
