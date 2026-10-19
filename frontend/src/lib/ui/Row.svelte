<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLButtonAttributes } from 'svelte/elements';
	import FoldChevron from './FoldChevron.svelte';

	/**
	 * What a row's label names, which sets the face it is drawn in and whether it may take more than a line:
	 * - path: a place in what is reviewed — a file, a folder, the line a thread hangs on, a base — in the code's
	 *   face, on one line, cut where the row ends
	 * - title: what is called by words — a part of a story, what a fold holds, the tour — in the page's own face,
	 *   wrapped onto as many lines as it takes and read whole
	 */
	type Names = 'path' | 'title';

	// The class of each in the library's stylesheet
	const NAMED: Record<Names, string | null> = { path: 'cr-ui-row-path', title: null };

	interface Props extends Omit<HTMLButtonAttributes, 'class' | 'style' | 'type' | 'children' | 'aria-expanded'> {
		names: Names;
		testId: string;
		/** For a row that folds what is under it: whether that is folded away, which the chevron at its end says. */
		folded?: boolean | undefined;
		/** How many folders deep it stands in the tree of files, which sets it in; none in any other list. */
		depth?: number;
		/** Whether it is the one of its list the reader is at. */
		current?: boolean;
		/** Whether the reader has finished with what it leads to: it steps back. */
		viewed?: boolean;
		/** What stands before its label: a file's letter, a part's node, a check, a dot, an icon. */
		leading?: Snippet | undefined;
		/** What it is called: a path cut where the row ends, a title whole. */
		label: Snippet;
		/** What it says of what it names, after its label in quieter words: a thread's, after the line it hangs on. */
		said?: Snippet;
		/** What stands at its end: a count, the lines a file changes, how long ago. */
		trailing?: Snippet;
	}

	let {
		names,
		testId,
		folded,
		depth = 0,
		current = false,
		viewed = false,
		leading,
		label,
		said,
		trailing,
		...attributes
	}: Props = $props();
</script>

<!-- A row of a list, one press to where it leads: what stands before it, what it is called and what it says of
	that, what stands at its end, and, where it folds what is under it, the chevron that says whether that is open -->
<button
	type="button"
	{...attributes}
	aria-expanded={folded === undefined ? undefined : !folded}
	data-testid={testId}
	class={['cr-ui-row cr-pressable', NAMED[names], current && 'cr-ui-row-current', viewed && 'cr-ui-row-viewed']}
	style:--cr-depth={depth}
>
	{#if leading}
		<span class="cr-ui-row-leading">{@render leading()}</span>
	{/if}
	<span class="cr-ui-row-label">{@render label()}</span>
	{#if said}
		<span class="cr-ui-row-said">{@render said()}</span>
	{/if}
	{#if trailing || folded !== undefined}
		<span class="cr-ui-row-end">
			{@render trailing?.()}
			{#if folded !== undefined}
				<FoldChevron {folded} />
			{/if}
		</span>
	{/if}
</button>
