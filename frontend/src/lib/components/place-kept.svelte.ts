/**
 * The reader kept on the line they read while what a reading area draws is
 * drawn anew: a new diff, a file read again for a new take.
 *
 * What is drawn anew redraws what lies above the reader as well: they stay
 * on the line they were reading, not at the same distance from the top,
 * which would put them elsewhere. Called as a component is made, by the one
 * that draws the reading area.
 */

import { tick, untrack } from 'svelte';
import type { FileSections } from '$lib/dom/file-sections';
import { namesTheFileAsItStands } from '$lib/utils/line-places';

/**
 * Keep the reader on their line whenever what `drawnAnew` reads changes:
 * the place is read before it is drawn, and gone back to once it is; nothing
 * else starts it.
 */
export function keepPlaceRead(sections: FileSections, drawnAnew: () => unknown): void {
	$effect.pre(() => {
		drawnAnew();
		const place = untrack(() => sections.readingPlace(namesTheFileAsItStands));
		if (place === null) return;
		void tick().then(() => sections.returnTo(place));
	});
}
