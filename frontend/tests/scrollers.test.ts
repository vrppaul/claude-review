import { describe, it, expect } from 'vitest';
import { styleRules } from './stylesheets';

// How a rule makes its box scroll down the page: `overflow`, or `overflow-y`,
// set to scroll. `overflow-x` alone is a wide line scrolling sideways
const SCROLLS_DOWN = /(?:^|[;\s])overflow(?:-y)?:[^;]*\b(?:auto|scroll)\b/;
// How a rule makes its box the one its contents are placed in: any `position` but the default
const PLACES_ITS_CONTENTS = /(?:^|[;\s])position:\s*(?:relative|absolute|fixed|sticky)\s*;/;

// The rules this is a gate over: which they are is what it asks of the stylesheet
const scrollers = styleRules().filter(({ declarations }) => SCROLLS_DOWN.test(declarations));

/**
 * Words kept for a screen reader are out of the flow: in a box that scrolls
 * and is not the box they are placed in, they stay put while the rest
 * scrolls, on a page that grows to hold them. The page was broken that way
 * once; and with the reading area no longer that box every browser test
 * still passes, so the stylesheet is asked itself.
 */
describe('a rule of the stylesheet that makes a box scroll down the page', () => {
	it('is the scroller’s, or the reading area’s own: no other rule makes one', () => {
		expect(scrollers.map(({ selectors }) => selectors)).toEqual(['.cr-scroller', '.cr-diff-area']);
	});

	it.each(scrollers)('makes $selectors the box its contents are placed in', ({ declarations }) => {
		expect(declarations).toMatch(PLACES_ITS_CONTENTS);
	});
});
