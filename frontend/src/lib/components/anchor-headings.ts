/**
 * How a thread says what it hangs on, at the head of the thread, for each
 * kind of anchor: the lines of a file say their side and their numbers. A
 * kind left out here does not type-check.
 */

import type { Component } from 'svelte';
import type { Anchor, AnchorKind } from '$lib/types';
import LineAnchorHeading from './LineAnchorHeading.svelte';

const HEADINGS: {
	[Kind in AnchorKind]: Component<{ anchor: Extract<Anchor, { kind: Kind }> }>;
} = {
	line: LineAnchorHeading
};

/** What draws the heading of a thread on this anchor. */
export function headingOf(anchor: Anchor): Component<{ anchor: Anchor }> {
	return HEADINGS[anchor.kind];
}
