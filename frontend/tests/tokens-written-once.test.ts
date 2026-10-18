import { describe, it, expect } from 'vitest';
import { customPropertiesOf, rulesOf, styleRules, tokenNames } from './stylesheets';

const TOKENS = [...tokenNames()];
// Every custom property a stylesheet besides tokens.css declares, with the sheet and the rule it is declared in
const DECLARED_OUTSIDE = styleRules().flatMap((rule) =>
	customPropertiesOf(rule).map((name) => ({
		sheet: rule.sheet,
		selectors: rule.selectors.replaceAll(/\s+/g, ' '),
		name
	}))
);

/**
 * A token is written once, in tokens.css, for both themes, and every other
 * stylesheet only names it: the palette test reads it there, and the state
 * test holds which token each state is painted with. A rule that declares a
 * token anew gives it another value wherever the rule reaches, unseen by
 * either, as the primary button relit the pointer's light for itself by
 * declaring --cr-hover again.
 */
describe('a token', () => {
	it.each(DECLARED_OUTSIDE)('is not declared again by $selectors, in $sheet, as $name', ({ name }) => {
		expect(TOKENS).not.toContain(name);
	});

	it("is all the library's stylesheet draws with: it declares no custom property of its own", () => {
		expect(rulesOf('ui.css').flatMap(customPropertiesOf)).toEqual([]);
	});
});
