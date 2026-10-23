<script lang="ts">
	import { useReview } from '$lib/review/context';
	import { formatWeight } from '$lib/review/weight';
	import Actions from '$lib/ui/Actions.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Callout from '$lib/ui/Callout.svelte';
	import Checkbox from '$lib/ui/Checkbox.svelte';
	import Dialog from '$lib/ui/Dialog.svelte';
	import type { Closing } from '$lib/ui/dialog-closing';
	import Icon from '$lib/ui/Icon.svelte';
	import PaneQuestion from '$lib/ui/PaneQuestion.svelte';
	import StorySketch from './StorySketch.svelte';

	interface Props {
		/**
		 * What writing the story does, once the dialog has closed and given the keyboard back: with whether every
		 * later story is to be written without asking.
		 */
		onWrite: (withoutAskingFromNowOn: boolean) => void;
		/** Called once it closes, either way, for whoever drew it to stop drawing it. */
		onClose: () => void;
	}

	// What the dialog asks, as it says it and is named by
	const QUESTION = 'Write a story of this change?';
	// What a story costs, said first
	const SPENDS_TOKENS = "It spends the agent's tokens.";
	// Where the choice to be asked no more is kept, and turned back
	const KEPT_IN_SETTINGS = 'In every review from now on. Settings, the gear in the header, turns it off.';

	let { onWrite, onClose }: Props = $props();
	const review = useReview();
	// Whether the reader ticked to have every later story written without asking: theirs until they answer
	let withoutAskingFromNowOn = $state(false);
</script>

<!-- Asked before a story is written: a story spends the agent's tokens, so whether to have one is the reader's
	to say, knowing what this review would cost; under the cost, the setting that asks them no more, as Settings
	names it. The way on comes last, as every row of acts ends, and takes the keyboard as the question opens;
	Escape and a press outside are "Not now" -->
<Dialog label={QUESTION} width="wide" testId="story-opt-in" {onClose}>
	{#snippet children({ close, closeThen }: Closing)}
		<div class="flex flex-col gap-3 p-4 text-sm">
			<!-- A question has no head of its own: it is asked first, and its answers close it -->
			<div class="flex items-center gap-2">
				<Icon name="story" size="sm" tone="agent" />
				<PaneQuestion question={QUESTION} testId="story-opt-in-question" />
			</div>
			<StorySketch />
			<p>
				The agent that made the change tells it as a story: a short overview, then chapters with its reason above each
				piece of code.
			</p>
			<!-- What it costs, to weigh before answering: a warning, as a chapter changed since it was told says it -->
			<Callout tone="warning" lead={SPENDS_TOKENS} testId="story-cost">
				The agent reads the whole diff again and writes the story: here up to
				<b>{formatWeight(review.weight)}</b> to read and a few thousand to write. Bigger changes cost more.
			</Callout>
			<Checkbox
				drawn="box"
				note={KEPT_IN_SETTINGS}
				checked={withoutAskingFromNowOn}
				testId="write-without-asking-from-now-on"
				onToggle={(checked: boolean) => (withoutAskingFromNowOn = checked)}
			>
				Write stories without asking
			</Checkbox>
			<Actions testId="story-opt-in-actions">
				{#snippet others()}
					<Button tone="quiet" size="sm" testId="stories-not-now" onclick={close}>Not now</Button>
				{/snippet}
				{#snippet main()}
					<!-- The control a modal gives the keyboard to as it opens, by the browser's own word for it -->
					<Button
						autofocus
						tone="primary"
						size="sm"
						testId="write-story"
						onclick={() => closeThen(() => onWrite(withoutAskingFromNowOn))}
					>
						Write the story
					</Button>
				{/snippet}
			</Actions>
		</div>
	{/snippet}
</Dialog>
