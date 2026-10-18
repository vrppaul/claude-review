<script lang="ts">
	import { useReview } from '$lib/review/context';
	import { formatWeight } from '$lib/review/weight';
	import Button from '$lib/ui/Button.svelte';
	import Dialog from './Dialog.svelte';
	import type { Closing } from './dialog-closing';
	import Icon from './Icon.svelte';
	import StorySketch from './StorySketch.svelte';

	interface Props {
		/** What turning stories on does, once the dialog has closed and given the keyboard back. */
		onTurnOn: () => void;
		/** Called once it closes, either way, for whoever drew it to stop drawing it. */
		onClose: () => void;
	}

	// What the dialog asks, as it says it and is named by
	const QUESTION = 'Turn on stories?';

	let { onTurnOn, onClose }: Props = $props();
	const review = useReview();
</script>

<!-- Asked before the first story is written: a story spends the agent's tokens, so whether to have them is
	the reader's to say, knowing what this review would cost. The way on comes first, and takes the
	keyboard; Escape and a press outside are "Not now" -->
<Dialog label={QUESTION} data-testid="story-opt-in" class="w-full max-w-lg" {onClose}>
	{#snippet children({ close, closeThen }: Closing)}
		<div class="flex flex-col gap-3.5 text-sm">
			<div class="flex items-center gap-2.5">
				<Icon name="story" class="h-4.5 w-4.5 text-(--cr-agent)" />
				<h2 class="text-base font-semibold">{QUESTION}</h2>
			</div>
			<StorySketch />
			<p>
				The agent that made the change tells it as a story: a short overview, then chapters with its reason above each
				piece of code.
			</p>
			<p data-testid="story-cost" class="cr-cost-note">
				<Icon name="notice" class="mt-0.5 h-4 w-4 text-warning" />
				<span>
					It spends the agent's tokens. The agent reads the whole diff again and writes the story: here up to
					<b>{formatWeight(review.weight)}</b> to read and a few thousand to write. Bigger changes cost more.
				</span>
			</p>
			<p class="cr-muted text-xs">
				Stories stay on for every review on this machine. Turn them off in Settings, the gear in the header.
			</p>
			<div class="flex flex-wrap gap-2.5 pt-1">
				<Button tone="primary" size="sm" data-testid="turn-on-stories" onclick={() => closeThen(onTurnOn)}>
					Turn on stories
				</Button>
				<Button tone="secondary" size="sm" data-testid="stories-not-now" onclick={close}>Not now</Button>
			</div>
		</div>
	{/snippet}
</Dialog>
