<script lang="ts">
	import { SvelteSet } from 'svelte/reactivity';
	import type { DiffFile, FileStatus } from '$lib/types';
	import { fileStats } from '$lib/utils/file-stats';
	import { useReview } from '$lib/review/context';
	import { dragEdge, stepEdge } from '$lib/utils/resize';

	const review = useReview();

	// A letter in the change's own colour, rather than a filled disc: the file
	// name is what the eye should land on in this list.
	const statusMark: Record<FileStatus, { label: string; colour: string }> = {
		modified: { label: 'M', colour: 'var(--color-warning)' },
		added: { label: 'A', colour: 'var(--cr-add-text)' },
		deleted: { label: 'D', colour: 'var(--cr-del-text)' },
		renamed: { label: 'R', colour: 'var(--cr-mark)' }
	};

	interface TreeNode {
		name: string;
		path: string;
		file?: DiffFile;
		children: TreeNode[];
	}

	let filter = $state('');
	const foldedFolders = new SvelteSet<string>();

	const isDiffMode = $derived(review.mode === 'diff');
	const matching = $derived(
		filter.trim() === ''
			? review.diff.files
			: review.diff.files.filter((file) =>
					file.path.toLowerCase().includes(filter.trim().toLowerCase())
				)
	);
	const tree = $derived(isDiffMode ? buildTree(matching) : []);

	function buildTree(files: DiffFile[]): TreeNode[] {
		const root: TreeNode[] = [];

		for (const file of files) {
			const parts = file.path.split('/');
			let current = root;

			for (let i = 0; i < parts.length; i++) {
				const name = parts[i];
				const isFile = i === parts.length - 1;
				const existingNode = current.find((n) => n.name === name);

				if (existingNode) {
					current = existingNode.children;
				} else {
					const node: TreeNode = {
						name,
						path: parts.slice(0, i + 1).join('/'),
						file: isFile ? file : undefined,
						children: []
					};
					current.push(node);
					current = node.children;
				}
			}
		}

		return collapseSingleChildren(root);
	}

	function collapseSingleChildren(nodes: TreeNode[]): TreeNode[] {
		return nodes.map((node) => {
			if (!node.file && node.children.length === 1 && !node.children[0].file) {
				const child = node.children[0];
				return {
					...child,
					name: `${node.name}/${child.name}`,
					children: collapseSingleChildren(child.children)
				};
			}
			return { ...node, children: collapseSingleChildren(node.children) };
		});
	}

	function toggleFolder(path: string) {
		if (foldedFolders.has(path)) foldedFolders.delete(path);
		else foldedFolders.add(path);
	}

	const sidebarNoun: Record<string, string> = {
		diff: 'changed file',
		files: 'file',
		transcript: 'message'
	};

	const heading = $derived.by(() => {
		const noun = sidebarNoun[review.mode] ?? 'file';
		const total = review.diff.files.length;
		const shown = matching.length;
		const counted = shown === total ? `${total} ${noun}${total === 1 ? '' : 's'}` : `${shown} of ${total}`;
		return review.reading.viewedCount > 0 ? `${counted} · ${review.reading.viewedCount} viewed` : counted;
	});
</script>

{#snippet fileRow(file: DiffFile, name: string, depth: number)}
	{@const mark = statusMark[file.status]}
	{@const fileComments = review.threads.onFile(file.path)}
	{@const stats = fileStats(file)}
	{@const viewed = review.reading.isViewed(file.path)}
	<li>
		<button
			data-testid="file-item"
			class="btn btn-ghost btn-sm w-full justify-start gap-1 text-left font-mono text-xs {viewed
				? 'opacity-45'
				: ''}"
			class:cr-current={review.diff.fileInView === file.path}
			style="padding-left: {depth * 12 + 8}px"
			onclick={() => review.sections.scrollToFile(file.path)}
		>
			{#if isDiffMode}
				<span class="w-3 shrink-0 text-center font-semibold" style="color: {mark.colour}"
					>{mark.label}</span
				>
			{/if}
			<span class="flex-1 truncate">{name}</span>
			{#if !review.diff.narrowed && review.lastRetake.isChanged(file.path)}
				<!-- The same fact the file header spells out, where there is no
					room to spell it -->
				<span
					data-testid="file-changed-mark"
					class="h-1.5 w-1.5 shrink-0 rounded-full"
					style="background: var(--cr-mark)"
					title="Changed since round {review.lastRetake.changedSince}"
				></span>
			{/if}
			{#if viewed}
				<svg
					data-testid="file-viewed-mark"
					class="h-3 w-3"
					style="color: var(--cr-mark)"
					viewBox="0 0 12 12"
					fill="currentColor"
					aria-label="Viewed"
				>
					<path d="M4.6 8.8L2 6.2l.9-.9 1.7 1.7L9.1 2.4l.9.9z" />
				</svg>
			{/if}
			{#if fileComments.length > 0}
				<span class="badge badge-xs badge-primary">{fileComments.length}</span>
			{/if}
			{#if isDiffMode}
				<span style="color: var(--cr-add-text)">+{stats.additions}</span>
				<span style="color: var(--cr-del-text)">−{stats.deletions}</span>
			{/if}
		</button>
	</li>
{/snippet}

{#snippet renderNode(node: TreeNode, depth: number)}
	{#if node.file}
		{@render fileRow(node.file, node.name, depth)}
	{:else}
		{@const folded = foldedFolders.has(node.path)}
		<li>
			<button
				data-testid="folder-item"
				class="cr-muted flex w-full items-center gap-1 px-2 py-1 text-left font-mono text-xs font-semibold hover:text-base-content"
				style="padding-left: {depth * 12 + 8}px"
				aria-expanded={!folded}
				onclick={() => toggleFolder(node.path)}
			>
				<svg
					class="h-2.5 w-2.5 transition-transform {folded ? '-rotate-90' : ''}"
					viewBox="0 0 12 12"
					fill="currentColor"
					aria-hidden="true"
				>
					<path d="M2 4l4 4 4-4z" />
				</svg>
				{node.name}/
			</button>
			{#if !folded}
				<ul>
					{#each node.children as child (child.path)}
						{@render renderNode(child, depth + 1)}
					{/each}
				</ul>
			{/if}
		</li>
	{/if}
{/snippet}

<aside
	data-testid="sidebar" data-tour="file-tree"
	class="relative flex shrink-0 flex-col border-r border-base-300 bg-base-100"
	style="width: {review.layout.fileTree.width}px"
>
	<!-- The reader's own width, dragged or stepped with the arrow keys -->
	<button
		data-testid="sidebar-resize"
		class="cr-tree-grip"
		aria-label="Resize the file tree"
		onpointerdown={(e) =>
			dragEdge(e, {
				width: review.layout.fileTree.width,
				grows: 'right',
				onWidth: (px) => review.layout.fileTree.setWidth(px)
			})}
		onkeydown={(e) =>
			stepEdge(e, {
				width: review.layout.fileTree.width,
				grows: 'right',
				onWidth: (px) => review.layout.fileTree.setWidth(px)
			})}
	></button>
	<div class="min-h-0 flex-1 overflow-y-auto p-3">
		<div class="mb-2 flex items-center gap-2">
			<h2 data-testid="sidebar-heading" class="text-sm font-semibold">{heading}</h2>
			<div class="flex-1"></div>
			<button
				data-testid="hide-sidebar"
				class="btn btn-ghost btn-xs px-1"
				title="Put the tree away"
				aria-label="Put the file tree away"
				onclick={() => review.layout.fileTree.toggle()}
			>
				<svg class="h-3 w-3" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
					<path d="M7.5 2L4 6l3.5 4z" />
				</svg>
			</button>
		</div>

		<input
			data-testid="file-filter"
			type="search"
			class="mb-2 w-full rounded border border-base-300 bg-base-200 px-2 py-1 font-mono text-xs"
			placeholder="Jump to a file"
			bind:value={filter}
		/>

		{#if matching.length === 0}
			<p data-testid="no-matches" class="cr-muted px-2 py-4 text-xs">
				No file matches “{filter}”.
			</p>
		{:else if isDiffMode}
			<ul>
				{#each tree as node (node.path)}
					{@render renderNode(node, 0)}
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
