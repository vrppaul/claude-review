<script lang="ts">
	import type { DiffFile, FileStatus } from '$lib/types';
	import { diffStore } from '$lib/stores/diff.svelte';
	import { commentStore } from '$lib/stores/comments.svelte';

	const statusBadge: Record<FileStatus, { label: string; class: string }> = {
		modified: { label: 'M', class: 'badge-warning' },
		added: { label: 'A', class: 'badge-success' },
		deleted: { label: 'D', class: 'badge-error' },
		renamed: { label: 'R', class: 'badge-info' }
	};

	function fileStats(file: DiffFile): { additions: number; deletions: number } {
		let additions = 0;
		let deletions = 0;
		for (const hunk of file.hunks) {
			for (const line of hunk.lines) {
				if (line.type === 'add') additions++;
				else if (line.type === 'delete') deletions++;
			}
		}
		return { additions, deletions };
	}

	interface TreeNode {
		name: string;
		path: string;
		file?: DiffFile;
		children: TreeNode[];
	}

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

	const sidebarTitle: Record<string, string> = {
		diff: 'Changed Files',
		files: 'Files',
		transcript: 'Messages'
	};

	const modeBadgeClass: Record<string, string> = {
		diff: 'badge-info',
		files: 'badge-warning',
		transcript: 'badge-secondary'
	};

	const isDiffMode = $derived(diffStore.mode === 'diff');
	const tree = $derived(isDiffMode ? buildTree(diffStore.files) : []);
</script>

{#snippet renderNode(node: TreeNode, depth: number)}
	{#if node.file}
		{@const badge = statusBadge[node.file.status]}
		{@const fileComments = commentStore.getForFile(node.file.path)}
		{@const stats = fileStats(node.file)}
		<li>
			<button
				data-testid="file-item"
				class="btn btn-ghost btn-sm w-full justify-start gap-1 text-left font-mono text-xs"
				class:btn-active={diffStore.selectedPath === node.file.path}
				style="padding-left: {depth * 12 + 8}px"
				onclick={() => diffStore.selectFile(node.file!.path)}
			>
				<span class="badge badge-xs {badge.class}">{badge.label}</span>
				<span class="truncate flex-1">{node.name}</span>
				{#if fileComments.length > 0}
					<span class="badge badge-xs badge-neutral">{fileComments.length}</span>
				{/if}
				<span class="text-success/70">+{stats.additions}</span>
				<span class="text-error/70">-{stats.deletions}</span>
			</button>
		</li>
	{:else}
		<li>
			<div
				class="px-2 py-1 font-mono text-xs text-base-content/50 font-semibold"
				style="padding-left: {depth * 12 + 8}px"
			>
				{node.name}/
			</div>
			<ul>
				{#each node.children as child (child.path)}
					{@render renderNode(child, depth + 1)}
				{/each}
			</ul>
		</li>
	{/if}
{/snippet}

{#snippet renderFileItem(file: DiffFile)}
	{@const fileComments = commentStore.getForFile(file.path)}
	<li>
		<button
			data-testid="file-item"
			class="btn btn-ghost btn-sm w-full justify-start gap-1 text-left font-mono text-xs"
			class:btn-active={diffStore.selectedPath === file.path}
			onclick={() => diffStore.selectFile(file.path)}
		>
			<span class="truncate flex-1">{file.path}</span>
			{#if fileComments.length > 0}
				<span class="badge badge-xs badge-neutral">{fileComments.length}</span>
			{/if}
		</button>
	</li>
{/snippet}

<aside data-testid="sidebar" class="w-96 border-r border-base-300 overflow-y-auto bg-base-100">
	<div class="p-3">
		<h2 class="font-semibold text-sm text-base-content/60 uppercase tracking-wide mb-2 flex items-center gap-2">
			<span class="badge badge-sm {modeBadgeClass[diffStore.mode] ?? 'badge-ghost'}">{diffStore.mode}</span>
			{sidebarTitle[diffStore.mode] ?? 'Files'} ({diffStore.files.length})
		</h2>
		{#if isDiffMode}
			<ul>
				{#each tree as node (node.path)}
					{@render renderNode(node, 0)}
				{/each}
			</ul>
		{:else}
			<ul>
				{#each diffStore.files as file (file.path)}
					{@render renderFileItem(file)}
				{/each}
			</ul>
		{/if}
	</div>
</aside>
