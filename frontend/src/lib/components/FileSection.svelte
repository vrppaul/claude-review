<script lang="ts">
	import type { DiffFile } from '$lib/types';
	import { messageOf } from '$lib/utils/errors';
	import { fileStats } from '$lib/utils/file-stats';
	import { languageOf } from '$lib/utils/highlight';
	import { isRenderable } from '$lib/utils/renderable';
	import { useReview } from '$lib/review/context';
	import { fileSectionKey } from '$lib/review/reading-view';
	import ChangedLines from './ChangedLines.svelte';
	import ContentViewToggle from './ContentViewToggle.svelte';
	import FilePath from './FilePath.svelte';
	import { type Extent, type FileView, linesView } from './file-drawing.svelte';
	import FoldToggle from './FoldToggle.svelte';
	import Icon from './Icon.svelte';
	import LinesSection from './LinesSection.svelte';
	import SectionHeader from './SectionHeader.svelte';

	interface Props {
		file: DiffFile;
	}

	let { file }: Props = $props();
	const review = useReview();

	const isDiffMode = $derived(review.mode === 'diff');
	const language = $derived(languageOf(review.mode, file.path));
	const hasRenderablePreview = $derived(isRenderable(language));
	const view = $derived(viewOf());

	// The file is drawn whole, its lines numbered as the diff on screen was taken
	const extent = $derived<Extent>({
		kind: 'whole',
		numbering: review.diff.numbering,
		revealed: review.diff.revealed
	});

	const commentCount = $derived(review.threads.onLinesOf(file.path).length);
	const collapsed = $derived(review.reading.isFolded(file.path));
	const viewed = $derived(review.reading.isViewed(file.path));

	let changedSinceFailed = $state<string | null>(null);

	/**
	 * How the file is drawn, as the reader chose: content with nothing to
	 * render shows its lines whatever the preference, and only a diff with
	 * lines in it reads across two columns.
	 */
	function viewOf(): FileView {
		const contentView = review.layout.contentView.mode;
		if (hasRenderablePreview && contentView !== 'raw') return contentView;
		return isDiffMode ? linesView(review.settings.current.diff_layout, file) : 'raw';
	}

	async function showChangesSince() {
		changedSinceFailed = null;
		try {
			await review.showChangesSinceRetake();
		} catch (error) {
			changedSinceFailed = messageOf(error);
		}
	}
</script>

<!-- A file of the review in a section of its own, under a rule that parts it from the next -->
<LinesSection
	sectionKey={fileSectionKey(file.path)}
	{file}
	{language}
	{view}
	{extent}
	folded={collapsed}
	testId="file-section"
	class="border-b border-base-300"
>
	{#snippet header()}
		<SectionHeader testId="file-header" class={{ 'cr-viewed': viewed }}>
			<FoldToggle
				folded={collapsed}
				subject={file.path}
				testId="collapse-file"
				onToggle={() => review.reading.toggleFolded(file.path)}
			/>

			<!-- A heading each, so a file can be reached by its name as well as scrolled to -->
			<h2 data-testid="file-heading" class="min-w-0 font-mono text-sm font-semibold wrap-anywhere">
				<FilePath {file} />
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
				<ChangedLines changed={fileStats(file)} />
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
		</SectionHeader>
	{/snippet}
</LinesSection>
