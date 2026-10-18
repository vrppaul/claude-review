<script lang="ts">
	import { useReview } from '$lib/review/context';
	import Button from '$lib/ui/Button.svelte';
	import IconButton from '$lib/ui/IconButton.svelte';
	import Icon from './Icon.svelte';
	import { HELP_BUTTON_ROLE, keysOf } from './keymap';
	import Popover from './Popover.svelte';

	// What the pane is called, said to whoever cannot see it, and what heads it
	const CALLED = 'Getting around, and the keyboard';
	const HEADING = 'Help';

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
	 * does not open it once more; the pane gives the keyboard back to where
	 * it was, as Escape does.
	 */
	function closeOnQuestionMark(event: KeyboardEvent) {
		if (event.key !== '?') return;
		event.preventDefault();
		review.guide.setHelpOpen(false);
	}
</script>

<!-- The way back to the tour and the news, and the keys: a pane under Help, as Settings is under its control.
	? opens it from anywhere, and the ? key may belong to a browser extension, so it has a button too -->
<Popover
	bind:open={() => review.guide.helpOpen, (open: boolean) => review.guide.setHelpOpen(open)}
	label={CALLED}
	placement="below-start"
	data-testid="help-menu"
	class="w-80"
	onkeydown={closeOnQuestionMark}
>
	{#snippet trigger(control)}
		<Button
			{...control}
			tone="quiet"
			size="xs"
			testId="open-help"
			data-role={HELP_BUTTON_ROLE}
			title="The tour, what is new, and the keys (?)"
		>
			<kbd class="cr-guide-key">?</kbd> Help
		</Button>
	{/snippet}

	<div class="flex flex-col p-4">
		<header class="mb-3 flex items-center gap-3">
			<h2 class="text-xs font-semibold">{HEADING}</h2>
			<div class="flex-1"></div>
			<IconButton
				tone="quiet"
				size="xs"
				label="Close {HEADING}"
				testId="close-help"
				onclick={() => review.guide.setHelpOpen(false)}
			>
				<Icon name="cross" />
			</IconButton>
		</header>
		<div class="mb-5 flex flex-col gap-1">
			<button type="button" data-testid="take-tour" class="cr-guide-entry cr-pressable" onclick={takeTour}>
				<Icon name="compass" class="cr-guide-compass" />
				<span class="flex-1 text-left">Take the tour again</span>
				<span class="cr-faint text-xs">{review.guide.stepCount} stops</span>
			</button>
			{#if review.guide.latestNews}
				<button type="button" data-testid="read-news" class="cr-guide-entry cr-pressable" onclick={readNews}>
					<Icon name="plus" class="cr-guide-plus" />
					<span class="flex-1 text-left">What's new in {review.guide.latestNews.release}</span>
				</button>
			{/if}
		</div>
		<h3 class="mb-3 text-sm font-semibold">Keyboard</h3>
		<dl data-testid="shortcuts-list" class="space-y-2">
			{#each keysOf(review) as row (row.keys)}
				<div class="flex items-baseline gap-4">
					<dt class="w-32 shrink-0 font-mono text-xs text-(--cr-control-text)">{row.keys}</dt>
					<dd class="text-sm">{row.does}</dd>
				</div>
			{/each}
			<!-- The list's own key, and every open pane's: not one the review answers -->
			<div class="flex items-baseline gap-4">
				<dt class="w-32 shrink-0 font-mono text-xs text-(--cr-control-text)">Esc</dt>
				<dd class="text-sm">Close it</dd>
			</div>
		</dl>
	</div>
</Popover>
