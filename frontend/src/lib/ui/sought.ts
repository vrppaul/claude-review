/**
 * What the reader asked for, where it stands (Sought): a name looked up, on
 * each line the lookup lists it on, and what the tree's filter found in a
 * name. One look wherever it stands, the reader's chip, edged; laid on plain
 * words by Sought, and into a line's highlighted markup by `markedSought`,
 * so only the library lays its class.
 */

import { markRanges, type TextRange } from '$lib/utils/markup-marks';

// The class the stretch asked for is drawn in, in the library's stylesheet
export const SOUGHT_MARK = 'cr-ui-sought';

/** A line's highlighted markup with the stretch of its words the reader asked for marked, as Sought marks words. */
export function markedSought(markup: string, stretch: TextRange): string {
	return markRanges(markup, [stretch], SOUGHT_MARK);
}
