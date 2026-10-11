<script lang="ts">
	import { useReview } from '$lib/review/context';
	import { timeAgo } from '$lib/utils/time';
	import TypingIndicator from './TypingIndicator.svelte';

	interface Props {
		/** When the question was handed over. */
		askedAt: number;
		/** Whether it is the first thing under its question, which the tie joins to it. */
		first: boolean;
	}

	let { askedAt, first }: Props = $props();
	const review = useReview();
</script>

<!-- A turn that has not arrived is still a turn: it holds its place, and says
	how long it has been waited on, so silence reads as silence rather than as
	something broken -->
<div class="cr-reply">
	{#if first}
		<span class="cr-tie" aria-hidden="true"></span>
	{/if}
	<div data-testid="awaiting-answer" data-tour="awaited-answer" class="cr-answer flex items-center gap-3">
		<span class="cr-who"><strong>Agent</strong></span>
		<TypingIndicator />
		<div class="flex-1"></div>
		<span class="cr-muted text-xs">
			asked {timeAgo(askedAt, review.clock.now)} — keep reading, the answer lands here
		</span>
	</div>
</div>
