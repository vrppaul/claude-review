<script lang="ts">
	import type { DiffFile } from '$lib/types';
	import { messageOf } from '$lib/utils/errors';
	import { languageOf } from '$lib/utils/highlight';
	import { isRenderable } from '$lib/utils/renderable';
	import { whenNearViewport } from '$lib/dom/scroll';
	import { useReview } from '$lib/review/context';
	import ChangedLines from './ChangedLines.svelte';
	import ContentViewToggle from './ContentViewToggle.svelte';
	import FileBody from './FileBody.svelte';
	import type { FileView } from './file-drawing.svelte';
	import FoldToggle from './FoldToggle.svelte';
	import Icon from './Icon.svelte';

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

	const commentCount = $derived(review.threads.onLinesOf(file.path).length);
	const collapsed = $derived(review.reading.isFolded(file.path));
	const viewed = $derived(review.reading.isViewed(file.path));

	// How many rows the file will draw, so the browser can leave it undrawn off
	// screen without the scrollbar lurching once it is drawn for real: the
	// stylesheet turns the count into a height. At least one, unless folded.
	const rowCount = $derived(file.hunks.reduce((count, hunk) => count + hunk.lines.length, 0));
	const rowsDrawn = $derived(collapsed ? 0 : Math.max(rowCount, 1));

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
			changedSinceFailed = messageOf(error);
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
	style:--cr-rows={rowsDrawn}
>
	<div
		data-testid="file-header"
		class={[
			'cr-file-header flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-base-300 bg-base-200 px-3 py-2',
			viewed && 'cr-viewed'
		]}
	>
		<FoldToggle
			folded={collapsed}
			subject={file.path}
			testId="collapse-file"
			onToggle={() => review.reading.toggleFolded(file.path)}
		/>

		<!-- A heading each, so a file can be reached by its name as well as scrolled to -->
		<h2 data-testid="file-heading" class="min-w-0 font-mono text-sm font-semibold wrap-anywhere">
			{#if file.old_path}
				<!-- Moved: where it was, quieter than where it is -->
				<span class="cr-muted font-normal">{file.old_path} →</span>
			{/if}
			{file.path}
		</h2>
		{#if !review.diff.narrowed && review.lastRetake.isChanged(file.path)}
			<button
				type="button"
				data-testid="file-changed-since"
				class="cr-chip cr-chip-marked"
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
			<ChangedLines {file} />
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
			<Icon name={viewed ? 'ticked' : 'box'} class="h-3 w-3" />
			<!-- One box per file, so the box says which file it is about -->
			Viewed<span class="sr-only">: {file.path}</span>
		</label>
	</div>

	{#if !collapsed}
		{#if built}
			<FileBody {file} {language} {view} {reviewOwnsRemovedLines} revealed={review.diff.revealed} piece={false} />
		{:else}
			<div data-testid="file-placeholder" class="cr-file-placeholder"></div>
		{/if}
	{/if}
</section>
