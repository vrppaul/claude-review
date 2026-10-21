<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { TreeFolder, TreeNode } from '$lib/utils/file-tree';
	import Row from '$lib/ui/Row.svelte';

	interface Props {
		folder: TreeFolder;
		/** How many folders deep it stands in the tree. */
		depth: number;
		/** Whether the reader folded it away, which the tree's layout keeps. */
		folded: boolean;
		/** Fold it away, or open it. */
		toggle: () => void;
		/** What draws each thing it holds, a file or a folder, at the depth it stands at. */
		node: Snippet<[TreeNode, number]>;
	}

	let { folder, depth, folded, toggle, node }: Props = $props();

	// Whether the reader unfolded it while it has been drawn: only then do its files come down over a fold's time.
	// Held by the folder's own drawing, so a tree drawn again — brought back, or read again in Files — opens nothing,
	// since nothing moves but in answer to the reader
	let unfoldedByReader = $state(false);

	/** Fold it away or open it, one the reader opens opening over a fold's time. */
	function foldOrUnfold() {
		unfoldedByReader = folded;
		toggle();
	}
</script>

<!-- A folder of the tree of files, and what it holds under it while it is open -->
<li>
	<!-- Its row, quieter than the files it folds under it -->
	<Row names="path" testId="folder-item" {depth} {folded} onclick={foldOrUnfold}>
		{#snippet label()}
			<span class="cr-muted">{folder.name}/</span>
		{/snippet}
	</Row>
	{#if !folded}
		<ul class={[unfoldedByReader && 'cr-tree-unfolding']}>
			{#each folder.children as child (child.path)}
				{@render node(child, depth + 1)}
			{/each}
		</ul>
	{/if}
</li>
