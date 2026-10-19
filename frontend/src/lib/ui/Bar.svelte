<script lang="ts">
	import type { Snippet } from 'svelte';
	import { KEPT_IN_SIGHT_ROLE } from '$lib/dom/in-sight';

	/**
	 * What a bar heads, which sets its room:
	 * - page: the review, across the whole page, at least as tall as a row of its controls, which wrap onto
	 *   another row on a narrow screen rather than be cut off
	 * - section: a section of a file's lines, kept in sight while the lines scroll under it, its name and what
	 *   is said and offered beside it wrapping as the page's do
	 * - column: a column beside what is read, above what scrolls in it, as tall as a small button with room
	 *   round it
	 */
	type Heads = 'page' | 'section' | 'column';

	// The class of each in the library's stylesheet
	const HEADS: Record<Heads, string> = {
		page: 'cr-ui-bar-page',
		section: 'cr-ui-bar-section',
		column: 'cr-ui-bar-column'
	};

	/** Whether the reader has finished with what it heads, a file viewed, whose bar steps back: a section's alone. */
	type Headed = { heads: 'section'; viewed?: boolean } | { heads: Exclude<Heads, 'section'>; viewed?: never };

	type Props = Headed & {
		testId: string;
		/** What heads it, and its controls. */
		children: Snippet;
	};

	let { heads, viewed = false, testId, children }: Props = $props();
</script>

<!-- A bar across the top of what it heads, the same for each of a kind: on a raised ground, ruled off from what
	is under it. A section's bar is kept in sight as the section scrolls (dom/in-sight.ts) -->
<header
	data-testid={testId}
	data-role={heads === 'section' ? KEPT_IN_SIGHT_ROLE : undefined}
	class={['cr-ui-bar', HEADS[heads], viewed && 'cr-ui-bar-viewed']}
>
	{@render children()}
</header>
