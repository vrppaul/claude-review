<script lang="ts">
	import { focusWhatRemains } from '$lib/dom/keyboard';
	import { useReview } from '$lib/review/context';
	import Button from '$lib/ui/Button.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import { arrowOffsetTo } from '$lib/ui/pane';
	import PopoverPanel from '$lib/ui/PopoverPanel.svelte';
	import PassingNote from './PassingNote.svelte';
	import StorySketch from './StorySketch.svelte';

	interface Props {
		/** Whether Story is introduced now, as the switch, which rings Story with it, says. */
		introducing: boolean;
		/** Story's segment of the switch, which the introduction stands under and points at. */
		pointsAt: HTMLElement | undefined;
		/** What trying Story does: how the review is read is its to change who draws the introduction. */
		onTry: () => void;
	}

	// What the introduction says first, and is named by; and what its close does, beside "Don't show again"
	const TITLE = 'Read the change as a story';
	const CLOSE_FOR_NOW = 'Close for now';

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
		width="medium"
		arrow
		{arrowOffset}
		edge="agent"
		head={{ heading: TITLE, close: putAwayForNow, closing: CLOSE_FOR_NOW }}
		testId="story-introduction"
	>
		<div class="flex flex-col gap-2 p-3">
			<StorySketch />
			<p class="text-sm">
				The agent that made it walks you through: a short overview, then chapters, with its reason above each piece of
				code. Your threads and rounds work the same.
			</p>
			<p class="cr-muted text-xs">It spends the agent's tokens, so it asks before it starts.</p>
			<div class="flex items-center gap-1.5 pt-0.5">
				<Button bind:element={tryStory} tone="primary" size="sm" testId="try-story" onclick={onTry}>Try Story</Button>
				<Button tone="quiet" size="sm" testId="story-introduction-hide" onclick={hideForGood}>Don't show again</Button>
			</div>
		</div>
	</PopoverPanel>
{:else if hiddenForGood}
	<PassingNote
		{pointsAt}
		label="Story will not be shown again"
		arrow={false}
		fades
		testId="story-introduction-hidden"
		onGone={() => (hiddenForGood = false)}
	>
		<div class="flex flex-wrap items-center gap-x-3 gap-y-2 py-2 pr-2 pl-3 text-sm">
			<Icon name="check" size="sm" tone="done" />
			<span>Won't show again, in any review. Story is still in the header.</span>
			<Button bind:element={undo} tone="secondary" size="xs" testId="story-introduction-undo" onclick={showAgain}>
				Undo
			</Button>
		</div>
	</PassingNote>
{/if}
