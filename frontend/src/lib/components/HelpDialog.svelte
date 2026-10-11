<script lang="ts">
	import { useReview } from '$lib/review/context';
	import Dialog from './Dialog.svelte';
	import Icon from './Icon.svelte';
	import { KEYMAP } from './keymap';

	const review = useReview();

	/** Leave the list for the tour, which needs the review uncovered. */
	function takeTour() {
		review.guide.setHelpOpen(false);
		review.guide.startTour();
	}

	function readNews() {
		review.guide.setHelpOpen(false);
		review.guide.showNews();
	}

	/**
	 * ? opened the list, and closes it again — answered here, so the review
	 * does not open it once more. Closed as Escape closes it, so the browser
	 * gives the keyboard back to where it was.
	 */
	function closeOnQuestionMark(event: KeyboardEvent & { currentTarget: HTMLDialogElement }) {
		if (event.key !== '?') return;
		event.preventDefault();
		event.currentTarget.close();
	}
</script>

<Dialog
	label="Getting around, and the keyboard"
	data-testid="help-dialog"
	class="w-full max-w-md"
	onClose={() => review.guide.setHelpOpen(false)}
	onkeydown={closeOnQuestionMark}
>
	<!-- The way back to the tour and the news, once their card is put away -->
	<div class="mb-5 flex flex-col gap-1">
		<button type="button" data-testid="take-tour" class="cr-guide-entry cr-guide-entry-lead" onclick={takeTour}>
			<Icon name="compass" class="cr-guide-compass" />
			<span class="flex-1 text-left">Take the tour again</span>
			<span class="cr-faint text-xs">{review.guide.stepCount} stops</span>
		</button>
		{#if review.guide.latestNews}
			<button type="button" data-testid="read-news" class="cr-guide-entry" onclick={readNews}>
				<Icon name="plus" class="cr-guide-plus" />
				<span class="flex-1 text-left">What's new in {review.guide.latestNews.release}</span>
			</button>
		{/if}
	</div>
	<h3 class="mb-4 text-lg font-semibold">Keyboard</h3>
	<dl data-testid="shortcuts-list" class="space-y-2">
		{#each KEYMAP as row (row.keys)}
			<div class="flex items-baseline gap-4">
				<dt class="w-40 shrink-0 font-mono text-xs text-(--cr-control)">{row.keys}</dt>
				<dd class="text-sm">{row.does}</dd>
			</div>
		{/each}
		<!-- The list's own key, and every open pane's: not one the review answers -->
		<div class="flex items-baseline gap-4">
			<dt class="w-40 shrink-0 font-mono text-xs text-(--cr-control)">Esc</dt>
			<dd class="text-sm">Close it</dd>
		</div>
	</dl>
</Dialog>
