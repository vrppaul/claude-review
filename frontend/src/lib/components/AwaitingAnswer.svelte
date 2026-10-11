<script lang="ts">
	import { useReview } from '$lib/review/context';
	import { messageOf } from '$lib/utils/errors';
	import { timeAgo } from '$lib/utils/time';
	import { AGENT_STOPPED_LISTENING, TAKE_BACK } from './agent-waits';
	import TypingIndicator from './TypingIndicator.svelte';

	interface Props {
		/** The thread the question was asked in. */
		threadId: string;
		/** The question waited on: the comment that opened the thread, or a reply in it. */
		questionId: string;
		/** When the question was handed over. */
		askedAt: number;
		/** Whether it is the first thing under its question, which the tie joins to it. */
		first: boolean;
	}

	let { threadId, questionId, askedAt, first }: Props = $props();
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

<!-- A turn that has not arrived is still a turn: it holds its place, and says
	how long it has been waited on, so silence reads as silence rather than as
	something broken -->
<div class="cr-reply">
	{#if first}
		<span class="cr-tie" aria-hidden="true"></span>
	{/if}
	<div data-testid="awaiting-answer" data-tour="awaited-answer" class="cr-answer flex items-center gap-3">
		<span class="cr-who"><strong>Agent</strong></span>
		{#if listening}
			<TypingIndicator />
		{/if}
		<div class="flex-1"></div>
		<span class="cr-muted text-xs">
			{listening
				? `asked ${timeAgo(askedAt, review.clock.now)} — keep reading, the answer lands here`
				: AGENT_STOPPED_LISTENING}
		</span>
		<button type="button" data-testid="take-back-question" class="btn btn-outline btn-xs" onclick={takeBack}>
			{TAKE_BACK}
		</button>
	</div>
	{#if failed}
		<p data-testid="take-back-error" class="mt-1 text-xs text-error">{failed}</p>
	{/if}
</div>
