<script lang="ts">
	import { SvelteSet } from 'svelte/reactivity';
	import type { DiffFile, FileStatus } from '$lib/types';
	import { diffStore } from '$lib/stores/diff.svelte';
	import { commentStore } from '$lib/stores/comments.svelte';
	import { fileStats } from '$lib/utils/file-stats';
	import { scrollToFile } from '$lib/utils/scroll';

	const statusBadge: Record<FileStatus, { label: string; class: string }> = {
		modified: { label: 'M', class: 'badge-warning' },
		added: { label: 'A', class: 'badge-success' },
		deleted: { label: 'D', class: 'badge-error' },
		renamed: { label: 'R', class: 'badge-info' }
	};

	interface TreeNode {
		name: string;
		path: string;
		file?: DiffFile;
		children: TreeNode[];
	}

	let filter = $state('');
	const foldedFolders = new SvelteSet<string>();

	const isDiffMode = $derived(diffStore.mode === 'diff');
	const matching = $derived(
		filter.trim() === ''
			? diffStore.files
			: diffStore.files.filter((file) =>
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
		const noun = sidebarNoun[diffStore.mode] ?? 'file';
		const total = diffStore.files.length;
		const shown = matching.length;
		const counted = shown === total ? `${total} ${noun}${total === 1 ? '' : 's'}` : `${shown} of ${total}`;
		return diffStore.viewedCount > 0 ? `${counted} · ${diffStore.viewedCount} viewed` : counted;
	});
</script>

{#snippet fileRow(file: DiffFile, name: string, depth: number)}
	{@const badge = statusBadge[file.status]}
	{@const fileComments = commentStore.getForFile(file.path)}
	{@const stats = fileStats(file)}
	{@const viewed = diffStore.isViewed(file.path)}
	<li>
		<button
			data-testid="file-item"
			class="btn btn-ghost btn-sm w-full justify-start gap-1 text-left font-mono text-xs {viewed
				? 'opacity-45'
				: ''}"
			class:btn-active={diffStore.selectedPath === file.path}
			style="padding-left: {depth * 12 + 8}px"
			onclick={() => scrollToFile(file.path)}
		>
			{#if isDiffMode}
				<span class="badge badge-xs {badge.class}">{badge.label}</span>
			{/if}
			<span class="flex-1 truncate">{name}</span>
			{#if viewed}
				<svg
					data-testid="file-viewed-mark"
					class="h-3 w-3 text-success"
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
				<span class="text-success/80">+{stats.additions}</span>
				<span class="text-error/80">−{stats.deletions}</span>
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
				class="flex w-full items-center gap-1 px-2 py-1 text-left font-mono text-xs font-semibold text-base-content/50 hover:text-base-content"
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

<aside data-testid="sidebar" class="w-96 overflow-y-auto border-r border-base-300 bg-base-100">
	<div class="p-3">
		<div class="mb-2 flex items-baseline gap-2">
			<h2 data-testid="sidebar-heading" class="text-sm font-semibold">{heading}</h2>
		</div>

		<input
			data-testid="file-filter"
			type="search"
			class="input input-sm mb-2 w-full font-mono text-xs"
			placeholder="Filter by path"
			bind:value={filter}
		/>

		{#if matching.length === 0}
			<p data-testid="no-matches" class="px-2 py-4 text-xs text-base-content/50">
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
