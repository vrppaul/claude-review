<script lang="ts">
	import { useReview } from '$lib/review/context';
	import Button from '$lib/ui/Button.svelte';
	import Heading from '$lib/ui/Heading.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import Key from '$lib/ui/Key.svelte';
	import KeyList from '$lib/ui/KeyList.svelte';
	import Popover from '$lib/ui/Popover.svelte';
	import { HELP_BUTTON_ROLE, keysOf } from './keymap';

	// What the pane is called, said to whoever cannot see it, and what heads it
	const CALLED = 'Getting around, and the keyboard';
	const HEADING = 'Help';
	// The list's own key, and every open pane's: not one the review answers, so listed after those it does
	const CLOSING_KEY = { keys: ['Esc'], does: 'Close it' };
	// What Send feedback says at its end while words written in the card wait there
	const DRAFT_KEPT = 'draft kept';

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

	/** Leave the list for the card the reader writes their feedback in, in the guide's corner. */
	function writeFeedback() {
		review.guide.setHelpOpen(false);
		review.guide.showFeedback();
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

<!-- The way back to the tour and the news, the way to send feedback, and the keys: a pane under Help, as Settings is
	under its control.
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
			size="sm"
			testId="open-help"
			data-role={HELP_BUTTON_ROLE}
			title="The tour, what is new, feedback, and the keys (?)"
		>
			<!-- Its key alone once the window narrows, its name kept for a screen reader and on the pointer -->
			<Key keys="?" stands="inline" testId="help-key" />
			<span class="max-cr-header-narrow:sr-only">Help</span>
		</Button>
	{/snippet}

	<div class="flex flex-col p-3">
		<!-- The ways back to the tour and the news, and the way to send feedback, a button each, one under the other -->
		<div class="mb-4 flex flex-col gap-1.5">
			<Button
				tone="secondary"
				size="sm"
				listed
				note="{review.guide.stepCount} stops"
				testId="take-tour"
				onclick={takeTour}
			>
				<Icon name="compass" size="sm" tone="reader" />
				Take the tour again
			</Button>
			{#if review.guide.latestNews}
				<Button tone="secondary" size="sm" listed testId="read-news" onclick={readNews}>
					<Icon name="plus" size="sm" tone="reader" />
					What's new in {review.guide.latestNews.release}
				</Button>
			{/if}
			<!-- What was written and put away waits in the card, which says so at its way in -->
			<Button
				tone="secondary"
				size="sm"
				listed
				note={review.feedback.written ? DRAFT_KEPT : undefined}
				testId="send-feedback"
				onclick={writeFeedback}
			>
				<Icon name="feedback" size="sm" tone="reader" />
				Send feedback
			</Button>
		</div>
		<section class="flex flex-col gap-3">
			<Heading tag="h3" heads="list">Keyboard</Heading>
			<KeyList rows={[...keysOf(review), CLOSING_KEY]} testId="shortcuts-list" keyTestId="shortcut-key" />
		</section>
	</div>
</Popover>
