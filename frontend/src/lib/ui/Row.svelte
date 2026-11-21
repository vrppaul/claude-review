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
	 * - code-name: a name in the code — a function, a class — as a path is drawn, at the weight of what is read
	 */
	type Names = 'path' | 'title' | 'code-name';

	// The classes of each in the library's stylesheet
	const NAMED: Record<Names, string | null> = {
		path: 'cr-ui-row-path',
		title: null,
		'code-name': 'cr-ui-row-path cr-ui-row-code-name'
	};

	/**
	 * Where a row hangs as a branch off the row above it, in the tree of files: the first under what it hangs on,
	 * its branch drawn from under that row's mark; or the next, its branch going on from the one above.
	 */
	type Branch = 'first' | 'next';

	// The class of each in the library's stylesheet
	const BRANCHES: Record<Branch, string> = { first: 'cr-ui-row-branch-first', next: 'cr-ui-row-branch-next' };

	interface Props extends Omit<HTMLButtonAttributes, 'class' | 'style' | 'type' | 'children' | 'aria-expanded'> {
		names: Names;
		testId: string;
		/** For a row that folds what is under it: whether that is folded away, which the chevron at its end says. */
		folded?: boolean | undefined;
		/** How many folders deep it stands in the tree of files, which sets it in; none in any other list. */
		depth?: number;
		/** Where it hangs as a branch off the row above it; nowhere in a list that is no such tree. */
		branch?: Branch | undefined;
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
		/** The row itself, for whoever hands the keyboard to it. */
		element?: HTMLButtonElement | undefined;
	}

	let {
		names,
		testId,
		folded,
		depth = 0,
		branch,
		current = false,
		viewed = false,
		leading,
		label,
		said,
		trailing,
		element = $bindable(),
		...attributes
	}: Props = $props();
</script>

<!-- A row of a list, one press to where it leads: on its line what stands before it, what it is called and what it
	says of that, what stands at its end, and, where it folds what is under it, the chevron that says whether that
	is open -->
<button
	bind:this={element}
	type="button"
	{...attributes}
	aria-expanded={folded === undefined ? undefined : !folded}
	data-testid={testId}
	class={[
		'cr-ui-row cr-pressable',
		NAMED[names],
		branch && BRANCHES[branch],
		current && 'cr-ui-row-current',
		viewed && 'cr-ui-row-viewed'
	]}
	style:--cr-depth={depth}
>
	<span class="cr-ui-row-line">
		{#if leading}
			<span class="cr-ui-row-leading">{@render leading()}</span>
		{/if}
		<span class="cr-ui-row-label">{@render label()}</span>
		{#if said}
			<span data-testid="{testId}-said" class="cr-ui-row-said">{@render said()}</span>
		{/if}
		{#if trailing || folded !== undefined}
			<span class="cr-ui-row-end">
				{@render trailing?.()}
				{#if folded !== undefined}
					<FoldChevron {folded} />
				{/if}
			</span>
		{/if}
	</span>
</button>
