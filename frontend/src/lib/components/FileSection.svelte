<script lang="ts">
	import type { ContentViewMode, DiffFile } from '$lib/types';
	import { commentStore } from '$lib/stores/comments.svelte';
	import { diffStore } from '$lib/stores/diff.svelte';
	import { fileStats } from '$lib/utils/file-stats';
	import { detectLanguage } from '$lib/utils/highlight';
	import { isRenderable } from '$lib/utils/renderable';
	import ContentViewToggle from './ContentViewToggle.svelte';
	import PreviewView from './PreviewView.svelte';
	import RawView from './RawView.svelte';
	import SideBySideView from './SideBySideView.svelte';

	interface Props {
		file: DiffFile;
	}

	let { file }: Props = $props();

	const isDiffMode = $derived(diffStore.mode === 'diff');
	const isTranscriptMode = $derived(diffStore.mode === 'transcript');
	// Transcript entries are labels like "user (22:41) #1", so they carry no
	// extension. Their text is Claude's prose, which reads best as markdown.
	const language = $derived(isTranscriptMode ? 'markdown' : detectLanguage(file.path));
	const hasRenderablePreview = $derived(isRenderable(language));
	// Content with nothing to render always shows raw, whatever the preference
	const viewMode = $derived<ContentViewMode>(
		hasRenderablePreview ? diffStore.contentViewMode : 'raw'
	);

	const stats = $derived(fileStats(file));
	const commentCount = $derived(commentStore.getForFile(file.path).length);
	const collapsed = $derived(diffStore.isCollapsed(file.path));
	const viewed = $derived(diffStore.isViewed(file.path));
</script>

<section data-testid="file-section" data-path={file.path} class="border-b border-base-300">
	<div
		class="sticky top-0 z-10 flex items-center gap-3 border-b border-base-300 bg-base-200 px-3 py-2"
	>
		<button
			data-testid="collapse-file"
			class="btn btn-ghost btn-xs px-1"
			aria-expanded={!collapsed}
			aria-label={collapsed ? `Expand ${file.path}` : `Collapse ${file.path}`}
			onclick={() => diffStore.toggleCollapsed(file.path)}
		>
			<svg
				class="h-3 w-3 transition-transform {collapsed ? '-rotate-90' : ''}"
				viewBox="0 0 12 12"
				fill="currentColor"
				aria-hidden="true"
			>
				<path d="M2 4l4 4 4-4z" />
			</svg>
		</button>

		<span class="font-mono text-sm font-semibold">{file.path}</span>

		{#if isDiffMode}
			<span class="badge badge-sm badge-ghost">{file.status}</span>
			<span class="font-mono text-xs">
				<span class="text-success">+{stats.additions}</span>
				<span class="text-error">−{stats.deletions}</span>
			</span>
		{/if}

		{#if commentCount > 0}
			<span data-testid="section-comment-count" class="badge badge-sm badge-primary">
				{commentCount}
			</span>
		{/if}

		<div class="flex-1"></div>

		{#if hasRenderablePreview && !collapsed}
			<ContentViewToggle />
		{/if}

		<label class="flex cursor-pointer items-center gap-1.5 text-xs text-base-content/70">
			<input
				data-testid="viewed-toggle"
				type="checkbox"
				class="checkbox checkbox-xs"
				checked={viewed}
				onchange={() => diffStore.toggleViewed(file.path)}
			/>
			Viewed
		</label>
	</div>

	{#if !collapsed}
		{#if viewMode === 'preview'}
			<PreviewView {file} />
		{:else if viewMode === 'side-by-side'}
			<SideBySideView {file} {language} />
		{:else}
			<RawView {file} {language} />
		{/if}
	{/if}
</section>
