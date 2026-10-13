import { describe, it, expect } from 'vitest';
import { styleRules } from './stylesheets';

// How a rule makes its box scroll down the page: `overflow`, or `overflow-y`,
// set to scroll. `overflow-x` alone is a wide line scrolling sideways
const SCROLLS_DOWN = /(?:^|[;\s])overflow(?:-y)?:[^;]*\b(?:auto|scroll)\b/;
// The same, found as often as the stylesheet writes it
const EVERY_SCROLL_DOWN = new RegExp(SCROLLS_DOWN, 'gm');
// How a rule makes its box the one its contents are placed in: any `position` but the default
const PLACES_ITS_CONTENTS = /(?:^|[;\s])position:\s*(?:relative|absolute|fixed|sticky)\s*;/;
// The two rules that may make a box scroll down the page: the scroller's, and the reading area's own
const SCROLLERS = ['.cr-scroller', '.cr-diff-area'];

// What every rule of the stylesheet declares, one rule to a line, and what each declares by its selectors
const everyDeclaration = styleRules()
	.map(({ declarations }) => declarations.replaceAll('\n', ' '))
	.join('\n');
const declaredBy = new Map(styleRules().map(({ selectors, declarations }) => [selectors, declarations]));

/**
 * Words kept for a screen reader are out of the flow: in a box that scrolls
 * and is not the box they are placed in, they stay put while the rest
 * scrolls, on a page that grows to hold them. The page was broken that way
 * once; and with the reading area no longer that box every browser test
 * still passes, so the stylesheet is asked itself.
 */
describe('a rule of the stylesheet that makes a box scroll down the page', () => {
	it('is one of two: no rule but the scroller’s and the reading area’s own makes one', () => {
		expect(everyDeclaration.match(EVERY_SCROLL_DOWN)).toHaveLength(SCROLLERS.length);
	});

	it.each(SCROLLERS)('is the one for %s, which is the box its contents are placed in', (selectors) => {
		expect(declaredBy.get(selectors)).toMatch(SCROLLS_DOWN);
		expect(declaredBy.get(selectors)).toMatch(PLACES_ITS_CONTENTS);
	});
});
