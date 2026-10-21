<script lang="ts">
	import type { DiffFile } from '$lib/types';
	import { messageOf } from '$lib/utils/errors';
	import { languageOf } from '$lib/utils/highlight';
	import { isRenderable } from '$lib/utils/renderable';
	import { useReview } from '$lib/review/context';
	import { fileSectionKey } from '$lib/review/reading-view';
	import Bar from '$lib/ui/Bar.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Checkbox from '$lib/ui/Checkbox.svelte';
	import Failure from '$lib/ui/Failure.svelte';
	import FoldToggle from '$lib/ui/FoldToggle.svelte';
	import ContentViewToggle from './ContentViewToggle.svelte';
	import FileTitle from './FileTitle.svelte';
	import { type Extent, type FileView, linesView } from './file-drawing.svelte';
	import LinesSection from './LinesSection.svelte';

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
		<Bar heads="section" {viewed} testId="file-header">
			<!-- A heading each, so a file can be reached by its name as well as scrolled to -->
			<FileTitle {file} element="h2" testId="file-heading" showsChange={isDiffMode} threads={commentCount}>
				{#snippet beside()}
					{#if !review.diff.narrowed && review.lastRetake.isChanged(file.path)}
						<Button
							tone="marked"
							size="xs"
							testId="file-changed-since"
							title="Show only what changed since then"
							onclick={showChangesSince}
						>
							changed since round {review.lastRetake.changedSince}
						</Button>
						{#if changedSinceFailed}
							<Failure stands="inline" testId="changed-since-error" said={changedSinceFailed} />
						{/if}
					{/if}
				{/snippet}
			</FileTitle>

			<div class="flex-1"></div>

			{#if hasRenderablePreview && !collapsed}
				<ContentViewToggle />
			{/if}

			<Checkbox
				drawn="chip"
				checked={viewed}
				testId="viewed-toggle"
				onToggle={() => review.reading.toggleViewed(file.path)}
			>
				<!-- One box per file, so the box says which file it is about -->
				Viewed<span class="sr-only">: {file.path}</span>
			</Checkbox>

			<!-- Its lines fold under the chevron at the header's far end, as everything on the page folds -->
			<FoldToggle
				folded={collapsed}
				subject={file.path}
				testId="collapse-file"
				onToggle={() => review.reading.toggleFolded(file.path)}
			/>
		</Bar>
	{/snippet}
</LinesSection>
