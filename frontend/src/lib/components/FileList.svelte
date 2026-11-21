<script lang="ts">
	import type { ReviewMode, TouchedName } from '$lib/types';
	import { fileStats } from '$lib/utils/file-stats';
	import { filesFound, fileTree, type ListedFile, type TreeNode } from '$lib/utils/file-tree';
	import { isComposingText } from '$lib/dom/keyboard';
	import { formerName } from '$lib/utils/paths';
	import { counted, type CountedWords, FILES } from '$lib/utils/words';
	import { tourStop } from '$lib/guide/tour';
	import { useReview } from '$lib/review/context';
	import { fileSectionKey } from '$lib/review/reading-view';
	import Dot from '$lib/ui/Dot.svelte';
	import EmptyNote from '$lib/ui/EmptyNote.svelte';
	import FailureCount from '$lib/ui/FailureCount.svelte';
	import Filter from '$lib/ui/Filter.svelte';
	import Heading from '$lib/ui/Heading.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import IconButton from '$lib/ui/IconButton.svelte';
	import SideColumn from '$lib/ui/SideColumn.svelte';
	import ChangedLines from './ChangedLines.svelte';
	import FileNames from './FileNames.svelte';
	import FileRow from './FileRow.svelte';
	import FileTreeFolder from './FileTreeFolder.svelte';
	import OutsideFiles from './OutsideFiles.svelte';
	import { chordName, COLUMN_CHORD } from './keymap';
	import { LookupFromTheTree } from './tree-name-lookup';
	import TreeNameLookup from './TreeNameLookup.svelte';
	import { wayBackOf } from './way-back';

	/** What the tree's filter says it finds: in the field, to whoever cannot see the field, and where nothing answers. */
	interface FilterWords {
		placeholder: string;
		label: string;
		/** What it looks for, as it says nothing of it matches. */
		sought: string;
	}

	// What the tree lists, counted in its heading, in each kind of review
	const COUNTED_AS: Record<ReviewMode, CountedWords> = {
		diff: { one: 'changed file', many: 'changed files' },
		files: FILES,
		transcript: { one: 'message', many: 'messages' }
	};
	// What its filter finds by, in each kind of review, while the tree lists no names
	const BY_PATH: FilterWords = { placeholder: 'Jump to a file', label: 'Find a file by its path', sought: 'file' };
	const FILTERED_BY: Record<ReviewMode, FilterWords> = {
		diff: BY_PATH,
		files: BY_PATH,
		transcript: { placeholder: 'Jump to a message', label: 'Find a message by its name', sought: 'message' }
	};
	// What it finds by while the tree lists names under its files
	const FILTERED_BY_NAMES: FilterWords = {
		placeholder: 'Find a file or name',
		label: 'Find a file by its path or by a name in it',
		sought: 'file or name'
	};
	// What the toggle beside the filter is called, pressed or not: its state is said apart, as pressed
	const LIST_NAMES = 'List the names under each file';
	// What a file lists under it while the tree lists no names
	const NO_NAMES: readonly TouchedName[] = [];
	// What the mark of the checks' failures on a file's row says, counted
	const PLACES_FAILED: CountedWords = { one: 'place the checks failed', many: 'places the checks failed' };
	const OUT_OF_DATE_SAID = ', out of date';
	// What every row that names a file carries, so the filter can hand the keyboard to the first of them
	const FILE_ROW_ROLE = 'file-row';

	const review = useReview();

	// What the tree is filtered by and which folders are folded are the layout's: they outlive the tree being put away
	const layout = review.layout.fileTree;

	const isDiffMode = $derived(review.mode === 'diff');
	// Names are listed under the files where the reader wants them and the diff on screen has any
	const namesListed = $derived(layout.namesListed && review.names.any);
	const filteredBy = $derived(namesListed ? FILTERED_BY_NAMES : FILTERED_BY[review.mode]);
	const query = $derived(layout.filter.trim().toLowerCase());
	const found = $derived(
		filesFound(review.diff.files, namesListed ? (path: string) => review.names.of(path) : () => NO_NAMES, query)
	);
	// Only a diff is a tree: the files of a plan, or the messages of a transcript, are a list
	const tree = $derived(isDiffMode ? fileTree(found) : []);

	const headedBy = $derived.by(() => {
		const total = review.diff.files.length;
		const shown = found.length;
		const count = shown === total ? counted(total, COUNTED_AS[review.mode]) : `${shown} of ${total}`;
		return review.reading.viewedCount > 0 ? `${count} · ${review.reading.viewedCount} viewed` : count;
	});

	// The names the change touched are read once the tree is drawn, and again for every diff that comes on screen
	$effect(() => {
		void review.names.follow();
	});

	// The name of the line the reader reads from, where the tree lists it, unfolded: its row is the current one
	const nameInView = $derived.by(() => {
		const read = review.sections.linesRead;
		if (read === null || layout.areNamesFolded(read.path)) return null;
		const standing = review.names.standingOn(read.path, read.lines);
		const listedThere = found.find((listed) => listed.file.path === read.path)?.names ?? NO_NAMES;
		return standing !== null && listedThere.includes(standing) ? standing : null;
	});

	// What the filter leaves, drawn: where it looks for the first file to go to
	let list: HTMLElement | undefined = $state();

	// Where a name the tree lists is defined and used, asked from the icon on its row; its pane lies over the column
	const lookup = new LookupFromTheTree(review.diff);

	/** Go to a file of the change, among the change's files: a file read alone gives way to them. */
	function goToFile(path: string) {
		review.views.show('files');
		review.sections.scrollTo(fileSectionKey(path));
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

{#snippet fileRow({ file, names }: ListedFile, shownAs: string, depth: number)}
	{@const viewed = review.reading.isViewed(file.path)}
	{@const namesFolded = layout.areNamesFolded(file.path)}
	<FileRow
		testId="file-item"
		role={FILE_ROW_ROLE}
		{depth}
		status={isDiffMode ? file.status : null}
		current={review.sections.fileInView === file.path && nameInView === null}
		{viewed}
		threads={review.threads.onLinesOf(file.path).length}
		onclick={() => goToFile(file.path)}
		namesFold={names.length === 0 ? undefined : { folded: namesFolded, toggle: () => layout.toggleNames(file.path) }}
	>
		{#snippet name()}
			{#if file.old_path}
				<!-- Moved: what it was called, quieter than what it is called now -->
				<span class="cr-muted">{formerName(file.old_path, file.path)} →</span>
			{/if}
			{shownAs}
		{/snippet}
		{#snippet marks()}
			{@const failed = review.checks.failuresIn(file.path)}
			{#if failed.length > 0}
				<!-- Where the checks failed in it, in ink once every check that found them is out of date -->
				{@const outOfDate = failed.every((found) => found.outOfDate)}
				<FailureCount
					count={failed.length}
					{outOfDate}
					label="{counted(failed.length, PLACES_FAILED)}{outOfDate ? OUT_OF_DATE_SAID : ''}"
					testId="file-failures"
				/>
			{/if}
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
		{#snippet under(row: HTMLButtonElement | undefined)}
			<FileNames
				path={file.path}
				names={namesFolded ? NO_NAMES : names}
				sought={query}
				depth={depth + 1}
				{nameInView}
				{viewed}
				fileRow={row}
				{lookup}
			/>
		{/snippet}
	</FileRow>
{/snippet}

{#snippet treeNode(node: TreeNode, depth: number)}
	{#if node.kind === 'file'}
		{@render fileRow(node.listed, node.name, depth)}
	{:else}
		<FileTreeFolder
			folder={node}
			{depth}
			folded={layout.isFolderFolded(node.path)}
			toggle={() => layout.toggleFolder(node.path)}
			node={treeNode}
		/>
	{/if}
{/snippet}

<!-- The files of the review, in the column beside them: the frame, its width and being put away are the column's;
	its rail counts the files. At its foot, and its rail's, the way back, while there is one -->
<SideColumn
	column={layout}
	side="left"
	landmark="aside"
	label="Files"
	called="the file tree"
	resizing="Resize the file tree"
	key={chordName(COLUMN_CHORD)}
	holds="list"
	back={wayBackOf(review)}
	data-tour={tourStop('file-tree')}
	testIds={{
		column: 'sidebar',
		head: 'sidebar-head',
		resize: 'sidebar-resize',
		putAway: 'hide-sidebar',
		bringBack: 'show-sidebar',
		back: 'go-back',
		backOnRail: 'go-back-on-rail'
	}}
>
	{#snippet heading()}
		<Heading tag="h2" heads="pane" testId="sidebar-heading">{headedBy}</Heading>
	{/snippet}
	{#snippet marks()}
		<Icon name="files" size="xs" />
		<span data-testid="sidebar-rail-count" class="text-2xs font-semibold">{review.diff.files.length}</span>
	{/snippet}
	<!-- Where a name of the tree is defined and used, in a pane by its icon over the column and the code beside it -->
	{#snippet over()}
		<TreeNameLookup {lookup} />
	{/snippet}

	<!-- The filter, and beside it, where the diff on screen has names to list, the way to list the files alone -->
	<div data-testid="file-filter-row" class="mb-2 flex items-center gap-1.5">
		<div class="flex min-w-0 flex-1">
			<Filter
				bind:value={() => layout.filter, (next: string) => layout.setFilter(next)}
				label={filteredBy.label}
				testId="file-filter"
				placeholder={filteredBy.placeholder}
				onkeydown={onFilterKey}
			/>
		</div>
		{#if review.names.any}
			<IconButton
				tone="quiet"
				size="xs"
				shape="square"
				label={LIST_NAMES}
				testId="tree-names-toggle"
				aria-pressed={layout.namesListed}
				onclick={() => layout.toggleNamesListed()}
			>
				<Icon name="steps" size="sm" />
			</IconButton>
		{/if}
	</div>

	{#if review.diff.files.length === 0}
		<!-- An empty diff, the work undone, say: there is nothing a filter could have missed -->
		<EmptyNote within="list" testId="no-files">No {COUNTED_AS[review.mode].many}.</EmptyNote>
	{:else if found.length === 0}
		<EmptyNote within="list" testId="no-matches">No {filteredBy.sought} matches “{layout.filter}”.</EmptyNote>
	{:else}
		<ul bind:this={list}>
			{#if isDiffMode}
				{#each tree as node (node.path)}
					{@render treeNode(node, 0)}
				{/each}
			{:else}
				{#each found as listed (listed.file.path)}
					{@render fileRow(listed, listed.file.path, 0)}
				{/each}
			{/if}
		</ul>
	{/if}

	<OutsideFiles />
</SideColumn>
