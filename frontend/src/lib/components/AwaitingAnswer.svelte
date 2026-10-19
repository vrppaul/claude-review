<script lang="ts">
	import { useReview } from '$lib/review/context';
	import BreathingDots from '$lib/ui/BreathingDots.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Failure from '$lib/ui/Failure.svelte';
	import { messageOf } from '$lib/utils/errors';
	import { AGENT } from '$lib/utils/speakers';
	import { timeAgo } from '$lib/utils/time';
	import { AGENT_STOPPED_LISTENING, TAKE_BACK } from './agent-waits';
	import ThreadTurn from './ThreadTurn.svelte';

	interface Props {
		/** The thread the question was asked in. */
		threadId: string;
		/** The question waited on: the comment that opened the thread, or a reply in it. */
		questionId: string;
		/** When the question was handed over. */
		askedAt: number;
	}

	let { threadId, questionId, askedAt }: Props = $props();
	const review = useReview();

	let failed = $state<string | null>(null);

	// Whether the agent is still there to answer: once it has stopped
	// listening the row says so, as the panel does of a message, rather than
	// go on promising an answer
	const listening = $derived(review.answerer.attached);

	/** Take the question back; the agent decides what to do about it. */
	async function takeBack() {
		failed = null;
		try {
			await review.threads.takeBack(threadId, questionId);
		} catch (error) {
			failed = messageOf(error);
		}
	}
</script>

<!-- A turn that has not arrived is still a turn, the agent's: it holds its place, and says how long it has
	been waited on, so silence reads as silence rather than as something broken -->
<ThreadTurn voice={AGENT} testId="awaiting-answer" tour="awaited-answer">
	{#snippet head()}
		{#if listening}
			<BreathingDots tone="quiet" testId="awaiting-dots" />
		{/if}
		<span class="flex-1"></span>
		<span class="cr-muted">
			{listening
				? `asked ${timeAgo(askedAt, review.clock.now)} — keep reading, the answer lands here`
				: AGENT_STOPPED_LISTENING}
		</span>
		<Button tone="secondary" size="xs" testId="take-back-question" onclick={takeBack}>{TAKE_BACK}</Button>
	{/snippet}
	{#if failed}
		<Failure stands="apart" testId="take-back-error" said={failed} />
	{/if}
</ThreadTurn>
