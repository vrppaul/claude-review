<script lang="ts">
	import type { DiffFile } from '$lib/types';
	import { fileStats } from '$lib/utils/file-stats';
	import { messageOf } from '$lib/utils/errors';
	import { languageOf } from '$lib/utils/highlight';
	import { isRenderable } from '$lib/utils/renderable';
	import { whenNearViewport } from '$lib/dom/scroll';
	import { useReview } from '$lib/review/context';
	import ContentViewToggle from './ContentViewToggle.svelte';
	import FileBody, { type FileView } from './FileBody.svelte';
	import Icon from './Icon.svelte';

	// What a file's header and each of its rows take up, in pixels, as drawn
	const HEADER_HEIGHT = 41;
	const ROW_HEIGHT = 21;
	// What the file says when the round's diff could not be taken and nothing said why
	const CHANGES_NOT_TAKEN = 'Could not take the diff against that round';

	interface Props {
		file: DiffFile;
		/** The area the review scrolls in, which a file comes near to be built; null for the page itself. */
		scrollRoot: HTMLElement | null;
	}

	let { file, scrollRoot }: Props = $props();
	const review = useReview();

	const isDiffMode = $derived(review.mode === 'diff');
	const language = $derived(languageOf(review.mode, file.path));
	const hasRenderablePreview = $derived(isRenderable(language));
	const view = $derived(viewOf());

	// Files reads the review's own diff unless a narrower base is chosen, whose removed lines are that base's
	const reviewOwnsRemovedLines = $derived(!review.diff.narrowed);

	const stats = $derived(fileStats(file));
	const commentCount = $derived(review.threads.onFile(file.path).length);
	const collapsed = $derived(review.reading.isFolded(file.path));
	const viewed = $derived(review.reading.isViewed(file.path));

	// Rough height so the browser can leave an off-screen file undrawn without
	// the scrollbar lurching once it renders for real. One row plus the header.
	const rowCount = $derived(file.hunks.reduce((count, hunk) => count + hunk.lines.length, 0));
	const bodyHeight = $derived(collapsed ? 0 : Math.max(rowCount, 1) * ROW_HEIGHT);

	let changedSinceFailed = $state<string | null>(null);

	/**
	 * How the file is drawn, as the reader chose: content with nothing to
	 * render shows its lines whatever the preference, and only a diff with
	 * lines in it reads across two columns.
	 */
	function viewOf(): FileView {
		const contentView = review.layout.contentView.mode;
		if (hasRenderablePreview && contentView !== 'raw') return contentView;
		const twoColumns = isDiffMode && review.settings.current.diff_layout === 'split' && file.hunks.length > 0;
		return twoColumns ? 'split' : 'raw';
	}

	async function showChangesSince() {
		changedSinceFailed = null;
		try {
			await review.showChangesSinceRetake();
		} catch (error) {
			changedSinceFailed = messageOf(error, CHANGES_NOT_TAKEN);
		}
	}

	let element: HTMLElement | undefined = $state();
	// Rows are built when the file comes within reach, and kept from then on
	let built = $state(false);

	$effect(() => (element ? review.sections.register(file.path, element) : undefined));

	$effect(() => {
		if (!element || built) return;
		return whenNearViewport(element, scrollRoot, () => (built = true));
	});
</script>

<section
	bind:this={element}
	data-testid="file-section"
	data-path={file.path}
	class="cr-section border-b border-base-300"
	style="contain-intrinsic-size: auto {HEADER_HEIGHT + bodyHeight}px"
>
	<div
		class="cr-file-header flex items-center gap-3 border-b border-base-300 bg-base-200 px-3 py-2 {viewed
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
			<Icon name="chevron" class="h-3 w-3 transition-transform {collapsed ? '-rotate-90' : ''}" />
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
			<Icon name={viewed ? 'check' : 'ring'} class="h-3 w-3" />
			Viewed
		</label>
	</div>

	{#if !collapsed}
		{#if built}
			<FileBody {file} {language} {view} {reviewOwnsRemovedLines} revealed={review.diff.revealed} />
		{:else}
			<div data-testid="file-placeholder" style="height: {bodyHeight}px"></div>
		{/if}
	{/if}
</section>
