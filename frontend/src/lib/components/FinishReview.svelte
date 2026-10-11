<script lang="ts">
	import { onMount } from 'svelte';
	import type { Thread } from '$lib/types';
	import { anchorPlace } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';
	import { raisedByAgent } from '$lib/utils/speakers';

	const review = useReview();

	let summary = $state<HTMLTextAreaElement | null>(null);

	const submission = review.submission;
	const unsent = $derived(review.threads.unsent.length);

	// The pane opens on the summary: the one thing in it that is written here
	onMount(() => summary?.focus());

	/** Put the pane away and go to a thread in it. */
	function jump(thread: Thread) {
		submission.setFinishing(false);
		review.navigator.reveal(thread);
	}
</script>

<!-- What has been written, a summary, and the two ways out -->
<div class="flex max-h-[70vh] flex-col">
	<div class="flex items-baseline gap-2 border-b border-base-300 px-4 py-2.5">
		<h3 class="text-sm font-semibold">
			{submission.inRounds ? `Round ${review.rounds.current}` : 'Finish the review'}
		</h3>
		<span data-testid="finish-count" class="cr-faint text-xs">
			{#if submission.inRounds}
				{unsent} unsent of {review.threads.count}
			{:else}
				{review.threads.count}
				{review.threads.count === 1 ? 'comment' : 'comments'}
			{/if}
		</span>
	</div>

	<div class="min-h-0 flex-1 overflow-y-auto px-4 py-3">
		{#if review.threads.count === 0}
			<p class="cr-faint text-sm">Nothing written yet. A summary on its own is a review too.</p>
		{:else}
			<ul class="flex flex-col gap-1.5">
				{#each review.threads.all as thread (thread.id)}
					{@const sent = review.threads.sentInRound(thread.id)}
					<li>
						<button
							type="button"
							data-testid="finish-comment"
							class={['cr-finish-row w-full rounded px-2 py-1.5 text-left', sent !== undefined && 'opacity-55']}
							onclick={() => jump(thread)}
						>
							<span class="flex items-baseline gap-2">
								<span data-testid="modal-comment-ref" class="cr-comment-ref font-mono text-xs">
									{anchorPlace(thread.anchor)}
								</span>
								{#if thread.severity !== 'note'}
									<span class="cr-severity cr-severity-{thread.severity}">{thread.severity}</span>
								{/if}
								{#if raisedByAgent(thread)}
									<span class="cr-severity cr-raised-tag">agent</span>
								{/if}
								{#if thread.resolved}
									<span class="cr-severity cr-muted">resolved</span>
								{/if}
								<span class="flex-1"></span>
								{#if sent !== undefined}
									<span class="cr-faint shrink-0 text-xs">round {sent}</span>
								{/if}
							</span>
							<span class="cr-comment-body mt-0.5 block whitespace-pre-wrap">{thread.body}</span>
						</button>
					</li>
				{/each}
			</ul>
		{/if}
	</div>

	<div class="border-t border-base-300 px-4 py-3">
		<textarea
			bind:this={summary}
			data-testid="review-body"
			class="cr-field cr-comment-body min-h-16 w-full rounded px-3 py-2"
			placeholder="Summary — optional, about the change as a whole"
			aria-label="Summary of the review"
			value={submission.body}
			oninput={(event) => submission.setBody(event.currentTarget.value)}
		></textarea>

		<div class="mt-2 flex items-center gap-2">
			<span class="cr-faint hidden text-xs lg:inline">Ctrl+Shift+Enter sends</span>
			<div class="flex-1"></div>
			{#if submission.inRounds}
				<button
					type="button"
					data-testid="end-review"
					class="btn btn-ghost btn-sm"
					disabled={submission.sending}
					onclick={() => submission.end()}
				>
					End review
				</button>
			{/if}
			<button
				type="button"
				data-testid="modal-submit"
				class="btn btn-primary btn-sm"
				disabled={!submission.canSend}
				onclick={() => submission.send()}
			>
				{#if submission.sending}
					Sending
				{:else if submission.inRounds}
					Send round {review.rounds.current}
				{:else}
					Send review
				{/if}
			</button>
		</div>
	</div>
</div>
