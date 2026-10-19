<script lang="ts">
	import { useReview } from '$lib/review/context';
	import Button from '$lib/ui/Button.svelte';
	import Heading from '$lib/ui/Heading.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import Key from '$lib/ui/Key.svelte';
	import Popover from '$lib/ui/Popover.svelte';
	import Row from '$lib/ui/Row.svelte';
	import { HELP_BUTTON_ROLE, keysOf } from './keymap';

	// What the pane is called, said to whoever cannot see it, and what heads it
	const CALLED = 'Getting around, and the keyboard';
	const HEADING = 'Help';
	// What stands between two keys that do opposite things: a slash, as what they do is written
	const OPPOSITES_APART = ' / ';

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
	heading={HEADING}
	placement="below-start"
	width="medium"
	testId="help-menu"
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
			<Key keys="?" testId="help-key" /> Help
		</Button>
	{/snippet}

	<div class="flex flex-col p-3">
		<!-- The ways back to the tour and the news, a row each -->
		<div class="mb-4 flex flex-col gap-1">
			<Row names="title" testId="take-tour" onclick={takeTour}>
				{#snippet leading()}
					<span class="cr-guide-compass"><Icon name="compass" size="xl" /></span>
				{/snippet}
				{#snippet label()}
					Take the tour again
				{/snippet}
				{#snippet trailing()}
					<span class="cr-faint">{review.guide.stepCount} stops</span>
				{/snippet}
			</Row>
			{#if review.guide.latestNews}
				{@const news = review.guide.latestNews}
				<Row names="title" testId="read-news" onclick={readNews}>
					{#snippet leading()}
						<span class="cr-guide-plus"><Icon name="plus" size="xl" /></span>
					{/snippet}
					{#snippet label()}
						What's new in {news.release}
					{/snippet}
				</Row>
			{/if}
		</div>
		<section class="flex flex-col gap-3">
			<Heading tag="h3" heads="list">Keyboard</Heading>
			<dl data-testid="shortcuts-list" class="space-y-2">
				{#each keysOf(review) as row (row.does)}
					<div class="flex items-baseline gap-4">
						<dt class="cr-muted w-(--cr-key-column-width) shrink-0 text-xs">
							{#each row.keys as key, position (key)}
								{#if position > 0}{OPPOSITES_APART}{/if}<Key keys={key} testId="shortcut-key" />
							{/each}
						</dt>
						<dd class="text-sm">{row.does}</dd>
					</div>
				{/each}
				<!-- The list's own key, and every open pane's: not one the review answers -->
				<div class="flex items-baseline gap-4">
					<dt class="w-(--cr-key-column-width) shrink-0 text-xs"><Key keys="Esc" testId="shortcut-key" /></dt>
					<dd class="text-sm">Close it</dd>
				</div>
			</dl>
		</section>
	</div>
</Popover>
