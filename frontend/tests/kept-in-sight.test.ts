import { describe, it, expect } from 'vitest';
import { KEPT_IN_SIGHT_ROLE } from '$lib/dom/in-sight';
import { styleRules } from './stylesheets';

// How a rule keeps its box in sight while what it heads scrolls under it
const KEEPS_IN_SIGHT = /(?:^|[;\s])position:\s*sticky\s*;/;
// The same, found as often as the stylesheet writes it
const EVERY_KEEPING_IN_SIGHT = new RegExp(KEEPS_IN_SIGHT, 'gm');
// The one rule that may: the rule of whatever says by its role that it is kept in sight
const OF_THE_ROLE = `[data-role='${KEPT_IN_SIGHT_ROLE}']`;

// What every rule of the stylesheet declares, one rule to a line, and what each declares by its selectors
const everyDeclaration = styleRules()
	.map(({ declarations }) => declarations.replaceAll('\n', ' '))
	.join('\n');
const declaredBy = new Map(styleRules().map(({ selectors, declarations }) => [selectors, declarations]));

/**
 * A line behind what is kept in sight is drawn, and the reader does not see
 * it: the page knows what is kept in sight by a role, and puts the keyboard
 * on no line behind it. Kept there by a class's own rule, a header would be
 * in sight to the eye and not to the page, and nothing would say the two had
 * come apart. So the stylesheet keeps in sight what carries the role, and
 * nothing else.
 */
describe('a rule of the stylesheet that keeps a box in sight while the rest scrolls', () => {
	it('is one: the rule of whatever says by its role that it is kept in sight', () => {
		expect(everyDeclaration.match(EVERY_KEEPING_IN_SIGHT)).toHaveLength(1);
		expect(declaredBy.get(OF_THE_ROLE)).toMatch(KEEPS_IN_SIGHT);
	});
});
