<script lang="ts">
	import type { DiffFile, ReviewMode } from '$lib/types';
	import { fileStats } from '$lib/utils/file-stats';
	import { fileTree, type TreeNode } from '$lib/utils/file-tree';
	import { isComposingText } from '$lib/dom/keyboard';
	import { formerName } from '$lib/utils/paths';
	import { counted, type CountedWords, FILES } from '$lib/utils/words';
	import { tourStop } from '$lib/guide/tour';
	import { useReview } from '$lib/review/context';
	import { fileSectionKey } from '$lib/review/reading-view';
	import Dot from '$lib/ui/Dot.svelte';
	import EmptyNote from '$lib/ui/EmptyNote.svelte';
	import Filter from '$lib/ui/Filter.svelte';
	import Heading from '$lib/ui/Heading.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import Row from '$lib/ui/Row.svelte';
	import SideColumn from '$lib/ui/SideColumn.svelte';
	import ChangedLines from './ChangedLines.svelte';
	import FileRow from './FileRow.svelte';
	import { COLUMN_KEY } from './keymap';

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
	// The folder the reader last unfolded, which opens over a fold's time: the tree drawn at first opens no folder,
	// since nothing moves but in answer to the reader
	let unfoldedLast = $state<string | null>(null);

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

	/** Fold a folder away or open it, an opened one opening over a fold's time. */
	function toggleFolder(path: string) {
		unfoldedLast = layout.isFolderFolded(path) ? path : null;
		layout.toggleFolder(path);
	}

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
				<Dot tone="reader" title="Changed since round {review.lastRetake.changedSince}" testId="file-changed-mark" />
				<span class="sr-only">changed since round {review.lastRetake.changedSince}</span>
			{/if}
			{#if viewed}
				<Icon name="check" size="xs" tone="done" label="Viewed" testId="file-viewed-mark" />
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
			<!-- A folder, quieter than the files it folds under it -->
			<Row names="path" testId="folder-item" {depth} {folded} onclick={() => toggleFolder(node.path)}>
				{#snippet label()}
					<span class="cr-muted">{node.name}/</span>
				{/snippet}
			</Row>
			{#if !folded}
				<ul class={[node.path === unfoldedLast && 'cr-tree-unfolding']}>
					{#each node.children as child (child.path)}
						{@render treeNode(child, depth + 1)}
					{/each}
				</ul>
			{/if}
		</li>
	{/if}
{/snippet}

<!-- The files of the review, in the column beside them: the frame, its width and being put away are the column's;
	its rail counts the files -->
<SideColumn
	column={layout}
	side="left"
	landmark="aside"
	label="Files"
	called="the file tree"
	resizing="Resize the file tree"
	key={COLUMN_KEY}
	holds="list"
	data-tour={tourStop('file-tree')}
	testIds={{
		column: 'sidebar',
		head: 'sidebar-head',
		resize: 'sidebar-resize',
		putAway: 'hide-sidebar',
		bringBack: 'show-sidebar'
	}}
>
	{#snippet heading()}
		<Heading tag="h2" heads="pane" testId="sidebar-heading">{headedBy}</Heading>
	{/snippet}
	{#snippet marks()}
		<Icon name="files" size="xs" />
		<span data-testid="sidebar-rail-count" class="text-2xs font-semibold">{review.diff.files.length}</span>
	{/snippet}

	<div class="mb-2">
		<Filter
			bind:value={() => layout.filter, (next: string) => layout.setFilter(next)}
			label="Find a {listed.sought} by its {listed.soughtBy}"
			testId="file-filter"
			placeholder="Jump to a {listed.sought}"
			onkeydown={onFilterKey}
		/>
	</div>

	{#if review.diff.files.length === 0}
		<!-- An empty diff, the work undone, say: there is nothing a filter could have missed -->
		<EmptyNote within="list" testId="no-files">No {listed.many}.</EmptyNote>
	{:else if matching.length === 0}
		<EmptyNote within="list" testId="no-matches">No {listed.sought} matches “{layout.filter}”.</EmptyNote>
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
