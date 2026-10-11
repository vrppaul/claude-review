<script lang="ts">
	import { SvelteSet } from 'svelte/reactivity';
	import type { DiffFile, FileStatus, ReviewMode } from '$lib/types';
	import { fileTree, type TreeNode } from '$lib/utils/file-tree';
	import { counted } from '$lib/utils/words';
	import { useReview } from '$lib/review/context';
	import ChangedLines from './ChangedLines.svelte';
	import EdgeGrip from './EdgeGrip.svelte';
	import Icon from './Icon.svelte';

	// A letter in the change's own colour, rather than a filled disc: the file
	// name is what the eye should land on in this list. A moved file says so
	// quietly — blue is the reader's own mark, and nothing else's.
	const STATUS_LETTERS: Record<FileStatus, { letter: string; colour: string }> = {
		modified: { letter: 'M', colour: 'text-(--cr-status-modified)' },
		added: { letter: 'A', colour: 'text-(--cr-add-text)' },
		deleted: { letter: 'D', colour: 'text-(--cr-del-text)' },
		renamed: { letter: 'R', colour: 'cr-muted' }
	};
	// What the tree counts, in each kind of review
	const COUNTED_AS: Record<ReviewMode, { one: string; many: string }> = {
		diff: { one: 'changed file', many: 'changed files' },
		files: { one: 'file', many: 'files' },
		transcript: { one: 'message', many: 'messages' }
	};

	const review = useReview();

	let filter = $state('');
	const foldedFolders = new SvelteSet<string>();

	const isDiffMode = $derived(review.mode === 'diff');
	const query = $derived(filter.trim().toLowerCase());
	const matching = $derived(
		query === '' ? review.diff.files : review.diff.files.filter((file) => file.path.toLowerCase().includes(query))
	);
	// Only a diff is a tree: the files of a plan, or the messages of a transcript, are a list
	const tree = $derived(isDiffMode ? fileTree(matching) : []);

	const heading = $derived.by(() => {
		const noun = COUNTED_AS[review.mode];
		const total = review.diff.files.length;
		const shown = matching.length;
		const listed = shown === total ? counted(total, noun.one, noun.many) : `${shown} of ${total}`;
		return review.reading.viewedCount > 0 ? `${listed} · ${review.reading.viewedCount} viewed` : listed;
	});

	function toggleFolder(path: string) {
		if (foldedFolders.has(path)) foldedFolders.delete(path);
		else foldedFolders.add(path);
	}
</script>

{#snippet fileRow(file: DiffFile, name: string, depth: number)}
	{@const status = STATUS_LETTERS[file.status]}
	{@const threadCount = review.threads.onLinesOf(file.path).length}
	{@const viewed = review.reading.isViewed(file.path)}
	<li>
		<button
			type="button"
			data-testid="file-item"
			class={[
				'cr-tree-row btn btn-ghost btn-sm w-full justify-start gap-1 text-left font-mono text-xs',
				viewed && 'cr-viewed',
				review.sections.fileInView === file.path && 'cr-current'
			]}
			style:--cr-depth={depth}
			onclick={() => review.sections.scrollToFile(file.path)}
		>
			{#if isDiffMode}
				<span class={['w-3 shrink-0 text-center font-semibold', status.colour]}>{status.letter}</span>
			{/if}
			<span class="flex-1 truncate">{name}</span>
			{#if !review.diff.narrowed && review.lastRetake.isChanged(file.path)}
				<!-- The same fact the file header spells out, where there is no
					room to spell it -->
				<span
					data-testid="file-changed-mark"
					class="h-1.5 w-1.5 shrink-0 rounded-full bg-(--cr-mark)"
					title="Changed since round {review.lastRetake.changedSince}"
				></span>
			{/if}
			{#if viewed}
				<Icon name="check" data-testid="file-viewed-mark" class="h-3 w-3 text-(--cr-done)" label="Viewed" />
			{/if}
			{#if threadCount > 0}
				<span class="badge badge-xs badge-primary">{threadCount}</span>
			{/if}
			{#if isDiffMode}
				<ChangedLines {file} />
			{/if}
		</button>
	</li>
{/snippet}

{#snippet treeNode(node: TreeNode, depth: number)}
	{#if node.kind === 'file'}
		{@render fileRow(node.file, node.name, depth)}
	{:else}
		{@const folded = foldedFolders.has(node.path)}
		<li>
			<button
				type="button"
				data-testid="folder-item"
				class="cr-tree-row flex w-full items-center gap-1 py-1 pr-2 text-left font-mono text-xs font-semibold text-(--cr-muted) hover:text-base-content"
				style:--cr-depth={depth}
				aria-expanded={!folded}
				onclick={() => toggleFolder(node.path)}
			>
				<Icon name="chevron" class={['h-2.5 w-2.5 transition-transform', folded && '-rotate-90']} />
				{node.name}/
			</button>
			{#if !folded}
				<ul>
					{#each node.children as child (child.path)}
						{@render treeNode(child, depth + 1)}
					{/each}
				</ul>
			{/if}
		</li>
	{/if}
{/snippet}

<aside
	data-testid="sidebar"
	data-tour="file-tree"
	class="cr-tree relative flex shrink-0 flex-col border-r border-base-300 bg-base-100"
	style:--cr-tree-width="{review.layout.fileTree.width}px"
>
	<!-- The tree is on the left, so it grows rightward -->
	<EdgeGrip column={review.layout.fileTree} grows="right" label="Resize the file tree" testId="sidebar-resize" />
	<div class="min-h-0 flex-1 overflow-y-auto p-3">
		<div class="mb-2 flex items-center gap-2">
			<h2 data-testid="sidebar-heading" class="text-sm font-semibold">{heading}</h2>
			<div class="flex-1"></div>
			<button
				type="button"
				data-testid="hide-sidebar"
				class="btn btn-ghost btn-xs px-1"
				title="Put the tree away"
				aria-label="Put the file tree away"
				onclick={() => review.layout.fileTree.toggle()}
			>
				<Icon name="caret" class="h-3 w-3 rotate-180" />
			</button>
		</div>

		<input
			data-testid="file-filter"
			type="search"
			class="mb-2 w-full rounded border border-base-300 bg-base-200 px-2 py-1 font-mono text-xs"
			placeholder="Jump to a file"
			aria-label="Find a file by its path"
			bind:value={filter}
		/>

		{#if matching.length === 0}
			<p data-testid="no-matches" class="cr-muted px-2 py-4 text-xs">
				No file matches “{filter}”.
			</p>
		{:else if isDiffMode}
			<ul>
				{#each tree as node (node.path)}
					{@render treeNode(node, 0)}
				{/each}
			</ul>
		{:else}
			<ul>
				{#each matching as file (file.path)}
					{@render fileRow(file, file.path, 0)}
				{/each}
			</ul>
		{/if}
	</div>
</aside>
