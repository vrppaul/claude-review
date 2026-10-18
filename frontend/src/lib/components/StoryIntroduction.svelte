<script lang="ts">
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import { useReview } from '$lib/review/context';
	import Button from '$lib/ui/Button.svelte';
	import IconButton from '$lib/ui/IconButton.svelte';
	import Icon from './Icon.svelte';
	import { arrowOffsetTo } from './pane-placement';
	import PassingNote from './PassingNote.svelte';
	import PopoverPanel from './PopoverPanel.svelte';
	import StorySketch from './StorySketch.svelte';

	interface Props {
		/** Whether Story is introduced now, as the switch, which rings Story with it, says. */
		introducing: boolean;
		/** Story's segment of the switch, which the introduction stands under and points at. */
		pointsAt: HTMLElement | undefined;
		/** What trying Story does: how the review is read is its to change who draws the introduction. */
		onTry: () => void;
	}

	// What the introduction says first, and is named by
	const TITLE = 'Read the change as a story';

	let { introducing, pointsAt, onTry }: Props = $props();
	const review = useReview();

	let tryStory: HTMLButtonElement | undefined = $state();
	let undo: HTMLButtonElement | undefined = $state();
	// Whether the notice that Story will not be introduced again stands in the introduction's place
	let hiddenForGood = $state(false);

	const arrowOffset = $derived(arrowOffsetTo(pointsAt));

	// The introduction that appears offers Try Story, unless the reader is busy: it takes the keyboard from no one
	$effect(() => {
		if (introducing) focusWhatRemains(() => tryStory);
	});

	/** Put it away for this page alone; the keyboard goes to Story, which it pointed at. */
	function putAwayForNow() {
		review.guide.putIntroductionAway();
		focusWhatRemains(() => pointsAt);
	}

	/** Introduce Story no more, here or in any review; the notice says so in its place, and takes the keyboard to Undo. */
	function hideForGood() {
		review.guide.noteStoryIntroduced();
		hiddenForGood = true;
		focusWhatRemains(() => undo);
	}

	/** Undo "Don't show again": the notice goes, and the introduction is back. */
	function showAgain() {
		hiddenForGood = false;
		review.guide.introduceStoryAgain();
	}
</script>

<!-- Story, introduced once to a reader who has never tried it, under the switch, pointing at it, in the
	agent's colour: put there by the page, not opened from a control, so a pane and no popover. The cross puts
	it away for this review; "Don't show again" for good, with Undo for a slip -->
{#if introducing}
	<PopoverPanel
		role="dialog"
		label={TITLE}
		placement="below-start"
		{arrowOffset}
		data-testid="story-introduction"
		class="cr-popover-note cr-popover-agent cr-story-introduction"
	>
		<div class="flex flex-col gap-2.5 px-4 py-3.5">
			<div class="flex items-start gap-2">
				<h2 class="flex-1 text-sm font-semibold">{TITLE}</h2>
				<IconButton
					tone="quiet"
					size="xs"
					label="Close for now"
					data-testid="story-introduction-close"
					onclick={putAwayForNow}
				>
					<Icon name="cross" />
				</IconButton>
			</div>
			<StorySketch />
			<p class="text-sm leading-relaxed">
				The agent that made it walks you through: a short overview, then chapters, with its reason above each piece of
				code. Your threads and rounds work the same.
			</p>
			<p class="cr-muted text-xs">It spends the agent's tokens, so it asks before it starts.</p>
			<div class="flex items-center gap-1.5 pt-0.5">
				<Button bind:element={tryStory} tone="primary" size="sm" data-testid="try-story" onclick={onTry}>
					Try Story
				</Button>
				<Button tone="quiet" size="sm" data-testid="story-introduction-hide" onclick={hideForGood}>
					Don't show again
				</Button>
			</div>
		</div>
	</PopoverPanel>
{:else if hiddenForGood}
	<PassingNote
		{pointsAt}
		label="Story will not be shown again"
		data-testid="story-introduction-hidden"
		class="cr-popover-arrowless cr-note-fading"
		onGone={() => (hiddenForGood = false)}
	>
		<div class="flex flex-wrap items-center gap-x-3 gap-y-2 py-2 pr-2.5 pl-3.5 text-sm">
			<Icon name="check" class="h-3.5 w-3.5 text-(--cr-done)" />
			<span>Won't show again, in any review. Story is still in the header.</span>
			<Button bind:element={undo} tone="secondary" size="xs" data-testid="story-introduction-undo" onclick={showAgain}>
				Undo
			</Button>
		</div>
	</PassingNote>
{/if}
