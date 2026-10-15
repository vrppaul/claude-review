<script lang="ts">
	import type { DiffFile, ReviewMode } from '$lib/types';
	import { fileStats } from '$lib/utils/file-stats';
	import { fileTree, type TreeNode } from '$lib/utils/file-tree';
	import { isComposingText } from '$lib/dom/keyboard';
	import { formerName } from '$lib/utils/paths';
	import { counted, type CountedWords, FILES } from '$lib/utils/words';
	import { useReview } from '$lib/review/context';
	import { fileSectionKey } from '$lib/review/reading-view';
	import ChangedLines from './ChangedLines.svelte';
	import FileRow from './FileRow.svelte';
	import FoldChevron from './FoldChevron.svelte';
	import Icon from './Icon.svelte';
	import SideColumn from './SideColumn.svelte';

	/** What the tree lists, in words: counted in its heading, looked for in its filter. */
	interface Listed extends CountedWords {
		/** One of them, as the filter looks for it, and what of it the filter reads. */
		sought: string;
		soughtBy: string;
	}

	// What the tree lists, in each kind of review
	const COUNTED_AS: Record<ReviewMode, Listed> = {
		diff: { one: 'changed file', many: 'changed files', sought: 'file', soughtBy: 'path' },
		files: { ...FILES, sought: 'file', soughtBy: 'path' },
		transcript: { one: 'message', many: 'messages', sought: 'message', soughtBy: 'name' }
	};
	// What every row that names a file carries, so the filter can hand the keyboard to the first of them
	const FILE_ROW_ROLE = 'file-row';

	const review = useReview();

	// What the tree is filtered by and which folders are folded are the layout's: they outlive the tree being put away
	const layout = review.layout.fileTree;

	const isDiffMode = $derived(review.mode === 'diff');
	const listed = $derived(COUNTED_AS[review.mode]);
	const query = $derived(layout.filter.trim().toLowerCase());
	const matching = $derived(
		query === '' ? review.diff.files : review.diff.files.filter((file) => file.path.toLowerCase().includes(query))
	);
	// Only a diff is a tree: the files of a plan, or the messages of a transcript, are a list
	const tree = $derived(isDiffMode ? fileTree(matching) : []);

	const headedBy = $derived.by(() => {
		const total = review.diff.files.length;
		const shown = matching.length;
		const count = shown === total ? counted(total, listed) : `${shown} of ${total}`;
		return review.reading.viewedCount > 0 ? `${count} · ${review.reading.viewedCount} viewed` : count;
	});

	// What the filter leaves, drawn: where it looks for the first file to go to
	let list: HTMLElement | undefined = $state();

	/**
	 * Enter goes to the first file the filter leaves, as a click on it would;
	 * the down arrow hands the keyboard to it, to go on from there.
	 */
	function onFilterKey(event: KeyboardEvent) {
		if (isComposingText(event) || (event.key !== 'Enter' && event.key !== 'ArrowDown')) return;
		const first = list?.querySelector<HTMLElement>(`[data-role="${FILE_ROW_ROLE}"]`);
		if (!first) return;
		event.preventDefault();
		if (event.key === 'Enter') first.click();
		else first.focus();
	}
</script>

{#snippet fileRow(file: DiffFile, shownAs: string, depth: number)}
	{@const viewed = review.reading.isViewed(file.path)}
	<FileRow
		testId="file-item"
		role={FILE_ROW_ROLE}
		{depth}
		status={isDiffMode ? file.status : null}
		current={review.sections.fileInView === file.path}
		{viewed}
		threads={review.threads.onLinesOf(file.path).length}
		onclick={() => review.sections.scrollTo(fileSectionKey(file.path))}
	>
		{#snippet name()}
			{#if file.old_path}
				<!-- Moved: what it was called, quieter than what it is called now -->
				<span class="cr-muted">{formerName(file.old_path, file.path)} →</span>
			{/if}
			{shownAs}
		{/snippet}
		{#snippet marks()}
			{#if !review.diff.narrowed && review.lastRetake.isChanged(file.path)}
				<!-- The same fact the file header spells out, where there is no
					room to spell it -->
				<span
					data-testid="file-changed-mark"
					class="h-1.5 w-1.5 shrink-0 rounded-full bg-(--cr-mark)"
					title="Changed since round {review.lastRetake.changedSince}"
				></span>
				<span class="sr-only">changed since round {review.lastRetake.changedSince}</span>
			{/if}
			{#if viewed}
				<Icon name="check" data-testid="file-viewed-mark" class="h-3 w-3 text-(--cr-done)" label="Viewed" />
			{/if}
		{/snippet}
		{#snippet end()}
			{#if isDiffMode}
				<ChangedLines changed={fileStats(file)} />
			{/if}
		{/snippet}
	</FileRow>
{/snippet}

{#snippet treeNode(node: TreeNode, depth: number)}
	{#if node.kind === 'file'}
		{@render fileRow(node.file, node.name, depth)}
	{:else}
		{@const folded = layout.isFolderFolded(node.path)}
		<li>
			<button
				type="button"
				data-testid="folder-item"
				class="cr-tree-row flex w-full items-center gap-1 py-1 pr-2 text-left font-mono text-xs font-semibold text-(--cr-muted) hover:text-base-content"
				style:--cr-depth={depth}
				aria-expanded={!folded}
				onclick={() => layout.toggleFolder(node.path)}
			>
				<FoldChevron {folded} class="h-2.5 w-2.5" />
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

<!-- The files of the review, in the column beside them: the frame, its width and being put away are the column's -->
<SideColumn
	column={layout}
	landmark="aside"
	label="Files"
	called="the file tree"
	tour="file-tree"
	class="bg-base-100"
	testIds={{ column: 'sidebar', resize: 'sidebar-resize', putAway: 'hide-sidebar', bringBack: 'show-sidebar' }}
>
	{#snippet heading()}
		<h2 data-testid="sidebar-heading" class="text-sm font-semibold">{headedBy}</h2>
	{/snippet}

	<input
		data-testid="file-filter"
		type="search"
		class="mb-2 w-full rounded border border-base-300 bg-base-200 px-2 py-1 font-mono text-xs"
		placeholder="Jump to a {listed.sought}"
		aria-label="Find a {listed.sought} by its {listed.soughtBy}"
		bind:value={() => layout.filter, (next: string) => layout.setFilter(next)}
		onkeydown={onFilterKey}
	/>

	{#if review.diff.files.length === 0}
		<!-- An empty diff, the work undone, say: there is nothing a filter could have missed -->
		<p data-testid="no-files" class="cr-muted px-2 py-4 text-xs">No {listed.many}.</p>
	{:else if matching.length === 0}
		<p data-testid="no-matches" class="cr-muted px-2 py-4 text-xs">
			No {listed.sought} matches “{layout.filter}”.
		</p>
	{:else}
		<ul bind:this={list}>
			{#if isDiffMode}
				{#each tree as node (node.path)}
					{@render treeNode(node, 0)}
				{/each}
			{:else}
				{#each matching as file (file.path)}
					{@render fileRow(file, file.path, 0)}
				{/each}
			{/if}
		</ul>
	{/if}
</SideColumn>
