/**
 * How a thread says what it hangs on, at the head of the thread, for each
 * kind of anchor: the lines of a file say their side and their numbers, a
 * block of the story what the story heads it with. A kind left out here does
 * not type-check.
 */

import type { Component } from 'svelte';
import type { AnchorKind } from '$lib/types';
import type { AnchorOfKind } from '$lib/anchors/views';
import LineAnchorHeading from './LineAnchorHeading.svelte';
import StoryAnchorHeading from './StoryAnchorHeading.svelte';

const HEADINGS: { [Kind in AnchorKind]: Component<{ anchor: AnchorOfKind[Kind] }> } = {
	line: LineAnchorHeading,
	story: StoryAnchorHeading
};

/** What draws the heading of a thread on this anchor: its own kind's, which is only ever given that anchor. */
export function headingOf<Kind extends AnchorKind>(
	anchor: AnchorOfKind[Kind]
): Component<{ anchor: AnchorOfKind[Kind] }> {
	return HEADINGS[anchor.kind];
}
