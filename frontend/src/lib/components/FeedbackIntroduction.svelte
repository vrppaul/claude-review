<script lang="ts">
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import { useReview } from '$lib/review/context';
	import Actions from '$lib/ui/Actions.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import { arrowOffsetTo } from '$lib/ui/pane';
	import PassingNote from '$lib/ui/PassingNote.svelte';
	import PopoverPanel from '$lib/ui/PopoverPanel.svelte';
	import FeedbackSketch from './FeedbackSketch.svelte';

	interface Props {
		/** Whether Send feedback is introduced now, as Help, which it rings, says. */
		introducing: boolean;
		/** Help's button, which the introduction stands under and points at. */
		pointsAt: HTMLElement | undefined;
	}

	// What the introduction says first, and is named by; and what its close does, beside "Don't show again"
	const TITLE = 'Tell us what to change';
	const CLOSE_FOR_NOW = 'Close for now';

	let { introducing, pointsAt }: Props = $props();
	const review = useReview();

	let pane: HTMLDivElement | undefined = $state();
	let sendFeedback: HTMLButtonElement | undefined = $state();
	let undo: HTMLButtonElement | undefined = $state();
	// Whether the notice that Send feedback will not be introduced again stands in the introduction's place
	let hiddenForGood = $state(false);

	const arrowOffset = $derived(arrowOffsetTo(pointsAt));

	// The introduction that appears offers Send feedback, unless the reader is busy: it takes the keyboard from no one
	$effect(() => {
		if (introducing) focusWhatRemains(() => sendFeedback);
	});

	// Taken away from elsewhere while it holds the keyboard — the note of a story that arrived stands under the
	// header in its place — it hands the keyboard to Help, which it pointed at. Looked at before the page redraws,
	// while the keyboard is still in it; what its own acts give the keyboard to keeps it
	$effect.pre(() => {
		if (!introducing && pane?.contains(document.activeElement)) focusWhatRemains(() => pointsAt);
	});

	/** Put it away for this page alone; the keyboard goes to Help, which it pointed at. */
	function putAwayForNow() {
		review.guide.putIntroductionAway();
		focusWhatRemains(() => pointsAt);
	}

	/** Introduce Send feedback no more, here or in any review; the notice says so in its place, and takes the keyboard to Undo. */
	function hideForGood() {
		review.guide.noteFeedbackIntroduced();
		hiddenForGood = true;
		focusWhatRemains(() => undo);
	}

	/** Undo "Don't show again": the notice goes, and the introduction is back. */
	function showAgain() {
		hiddenForGood = false;
		review.guide.introduceFeedbackAgain();
	}
</script>

<!-- Send feedback, introduced once, under Help, pointing at it, in the reader's colour, as what it invites is their
	word: put there by the page, not opened from a control, so a pane and no popover. The cross puts it away for this
	review; "Don't show again" for good, with Undo for a slip; Send feedback opens the card, which keeps the keyboard -->
{#if introducing}
	<PopoverPanel
		bind:pane
		role="dialog"
		label={TITLE}
		placement="below-start"
		width="medium"
		arrow
		{arrowOffset}
		edge="reader"
		head={{ heading: TITLE, close: putAwayForNow, closing: CLOSE_FOR_NOW }}
		testId="feedback-introduction"
	>
		<div class="flex flex-col gap-2 p-3">
			<FeedbackSketch />
			<p class="text-sm">
				Point at the part of the page you mean, read all that goes, then open an issue on GitHub or hand it to your
				agent. It waits in Help, under the tour.
			</p>
			<p class="cr-muted text-xs">None of your code goes, and nothing of your review.</p>
			<Actions testId="feedback-introduction-actions">
				{#snippet others()}
					<Button tone="quiet" size="sm" testId="feedback-introduction-hide" onclick={hideForGood}>
						Don't show again
					</Button>
				{/snippet}
				{#snippet main()}
					<Button
						bind:element={sendFeedback}
						tone="primary"
						size="sm"
						testId="feedback-introduction-send"
						onclick={() => review.guide.showFeedback()}>Send feedback</Button
					>
				{/snippet}
			</Actions>
		</div>
	</PopoverPanel>
{:else if hiddenForGood}
	<PassingNote
		{pointsAt}
		label="Send feedback will not be shown again"
		placement="below-start"
		arrow={false}
		fades
		testId="feedback-introduction-hidden"
		onGone={() => (hiddenForGood = false)}
	>
		<!-- Said, with the way back among its words: a slip's undoing, which must not outweigh them -->
		<div class="flex flex-wrap items-center gap-x-3 gap-y-2 py-2 pr-2 pl-3 text-sm">
			<Icon name="check" size="sm" tone="done" />
			<span>Won't show again, in any review. Send feedback is still in Help.</span>
			<Button bind:element={undo} tone="quiet" size="xs" testId="feedback-introduction-undo" onclick={showAgain}>
				Undo
			</Button>
		</div>
	</PassingNote>
{/if}
