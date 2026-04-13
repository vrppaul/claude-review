<script lang="ts">
	import type { ContentViewMode, DiffFile } from '$lib/types';
	import { diffStore } from '$lib/stores/diff.svelte';
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
	// Transcript paths like "user (22:41) #1" have no extension, so detectLanguage returns null.
	// Claude's responses contain markdown, so we force markdown highlighting for readability.
	const language = $derived(isTranscriptMode ? 'markdown' : detectLanguage(file.path));
	const hasRenderablePreview = $derived(isRenderable(language));
	// Non-renderable content always shows raw regardless of the store preference
	const effectiveViewMode = $derived<ContentViewMode>(
		hasRenderablePreview ? diffStore.contentViewMode : 'raw'
	);
</script>

<div data-testid="diff-view" class="flex-1 flex flex-col min-h-0 bg-base-100 {effectiveViewMode === 'side-by-side' ? 'overflow-hidden' : 'overflow-auto'}">
	<div class="sticky top-0 bg-base-200 border-b border-base-300 px-4 py-3 font-mono text-sm z-10">
		<span class="font-semibold">{file.path}</span>
		{#if isDiffMode}
			<span class="badge badge-sm ml-2">{file.status}</span>
		{/if}
		{#if hasRenderablePreview}
			<ContentViewToggle />
		{/if}
	</div>

	{#if effectiveViewMode === 'preview'}
		<PreviewView {file} />
	{:else if effectiveViewMode === 'side-by-side'}
		<SideBySideView {file} {language} />
	{:else}
		<RawView {file} {language} />
	{/if}
</div>
