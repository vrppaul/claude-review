<script lang="ts">
	import type { ContentViewMode } from '$lib/reader/page-layout.svelte';
	import type { DiffFile } from '$lib/types';
	import { fileStats } from '$lib/utils/file-stats';
	import { detectLanguage } from '$lib/utils/highlight';
	import { isRenderable } from '$lib/utils/renderable';
	import { whenNearViewport } from '$lib/dom/scroll';
	import { useReview } from '$lib/review/context';
	import ContentViewToggle from './ContentViewToggle.svelte';
	import FileNotes from './FileNotes.svelte';
	import PreviewView from './PreviewView.svelte';
	import RawView from './RawView.svelte';
	import SplitView from './SplitView.svelte';
	import SideBySideView from './SideBySideView.svelte';

	interface Props {
		file: DiffFile;
		/** The area the review scrolls in, which a file comes near to be built; null for the page itself. */
		scrollRoot: HTMLElement | null;
	}

	let { file, scrollRoot }: Props = $props();
	const review = useReview();

	const isDiffMode = $derived(review.mode === 'diff');
	const isTranscriptMode = $derived(review.mode === 'transcript');
	// Transcript entries are labels like "user (22:41) #1", so they carry no
	// extension. Their text is Claude's prose, which reads best as markdown.
	const language = $derived(isTranscriptMode ? 'markdown' : detectLanguage(file.path));
	const hasRenderablePreview = $derived(isRenderable(language));
	// Content with nothing to render always shows raw, whatever the preference
	const viewMode = $derived<ContentViewMode>(hasRenderablePreview ? review.layout.contentView.mode : 'raw');

	// Files reads the review's own diff unless a narrower base is chosen, whose removed lines are that base's
	const reviewOwnsRemovedLines = $derived(!review.diff.narrowed);

	const stats = $derived(fileStats(file));
	const commentCount = $derived(review.threads.onFile(file.path).length);
	const collapsed = $derived(review.reading.isFolded(file.path));
	const viewed = $derived(review.reading.isViewed(file.path));

	// Rough height so the browser can leave an off-screen file undrawn without
	// the scrollbar lurching once it renders for real. One row plus the header.
	const rowCount = $derived(file.hunks.reduce((n, hunk) => n + hunk.lines.length, 0));
	const estimatedHeight = $derived(collapsed ? 41 : 41 + Math.max(rowCount, 1) * 21);

	let changedSinceFailed = $state<string | null>(null);

	async function showChangesSince() {
		changedSinceFailed = null;
		try {
			await review.showChangesSinceRetake();
		} catch (error) {
			changedSinceFailed = error instanceof Error ? error.message : 'Could not take the diff against that round';
		}
	}

	let element: HTMLElement | undefined = $state();
	// Rows are built when the file comes within reach, and kept from then on
	let built = $state(false);

	$effect(() => (element ? review.sections.register(file.path, element) : undefined));

	$effect(() => {
		if (!element || built) return;
		return whenNearViewport(element, scrollRoot, () => {
			built = true;
		});
	});
</script>

<section
	bind:this={element}
	data-testid="file-section"
	data-path={file.path}
	class="cr-section border-b border-base-300"
	style="contain-intrinsic-size: auto {estimatedHeight}px"
>
	<div
		class="sticky top-0 z-10 flex items-center gap-3 border-b border-base-300 bg-base-200 px-3 py-2 {viewed
			? 'opacity-55'
			: ''}"
	>
		<button
			data-testid="collapse-file"
			class="btn btn-ghost btn-xs px-1.5"
			aria-expanded={!collapsed}
			aria-label={collapsed ? `Expand ${file.path}` : `Collapse ${file.path}`}
			onclick={() => review.reading.toggleFolded(file.path)}
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
		{#if !review.diff.narrowed && review.lastRetake.isChanged(file.path)}
			<button
				data-testid="file-changed-since"
				class="cr-chip"
				style="background: var(--cr-mark-tint); color: var(--cr-mark)"
				title="Show only what changed since then"
				onclick={showChangesSince}
			>
				changed since round {review.lastRetake.changedSince}
			</button>
			{#if changedSinceFailed}
				<span data-testid="changed-since-error" class="text-error text-xs">{changedSinceFailed}</span>
			{/if}
		{/if}

		{#if isDiffMode}
			<span class="cr-muted text-xs">{file.status}</span>
			<span class="font-mono text-xs">
				<span style="color: var(--cr-add-text)">+{stats.additions}</span>
				<span style="color: var(--cr-del-text)">−{stats.deletions}</span>
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

		<label class="cr-chip">
			<input
				data-testid="viewed-toggle"
				type="checkbox"
				checked={viewed}
				onchange={() => review.reading.toggleViewed(file.path)}
			/>
			<svg class="h-3 w-3" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
				{#if viewed}
					<path d="M4.6 8.8L2 6.2l.9-.9 1.7 1.7L9.1 2.4l.9.9z" />
				{:else}
					<circle cx="6" cy="6" r="4.5" fill="none" stroke="currentColor" stroke-width="1" />
				{/if}
			</svg>
			Viewed
		</label>
	</div>

	{#if !collapsed}
		{#if built}
			<FileNotes {file} />
			{#if viewMode === 'preview'}
				<PreviewView {file} />
			{:else if viewMode === 'side-by-side'}
				<SideBySideView {file} {language} {reviewOwnsRemovedLines} revealed={review.diff.revealed} />
			{:else if isDiffMode && review.settings.current.diff_layout === 'split' && file.hunks.length > 0}
				<SplitView {file} {language} {reviewOwnsRemovedLines} revealed={review.diff.revealed} />
			{:else}
				<RawView {file} {language} {reviewOwnsRemovedLines} revealed={review.diff.revealed} />
			{/if}
		{:else}
			<div data-testid="file-placeholder" style="height: {estimatedHeight - 41}px"></div>
		{/if}
	{/if}
</section>
