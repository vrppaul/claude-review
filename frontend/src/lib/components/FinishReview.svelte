<script lang="ts">
	import { onMount } from 'svelte';
	import type { Anchor, Thread } from '$lib/types';
	import { anchorPlace, anchorReplaces } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';
	import { raisedByAgent } from '$lib/utils/speakers';
	import { splitSuggestions } from '$lib/utils/suggestion';
	import { counted } from '$lib/utils/words';
	import { finishingTitle } from './finishing';
	import { FINISH_KEYS } from './keymap';
	import SuggestionDiff from './SuggestionDiff.svelte';

	const review = useReview();

	let summary = $state<HTMLTextAreaElement | null>(null);

	const submission = review.submission;
	const unsent = $derived(review.threads.unsent.length);
	// Comments still open in their fields, which go with whatever is sent
	const open = $derived(review.threads.open);

	// The pane opens on the summary: the one thing in it that is written here
	onMount(() => summary?.focus());

	/** Put the pane away and go to a thread in it. */
	function jump(thread: Thread) {
		submission.setFinishing(false);
		review.navigator.reveal(thread);
	}
</script>

<!-- What a comment says, in full: its words as written, and a suggestion as the change it makes -->
{#snippet said(body: string, anchor: Anchor)}
	{#each splitSuggestions(body) as part, partIndex (partIndex)}
		{#if part.kind === 'suggestion'}
			<SuggestionDiff replaced={anchorReplaces(anchor)} suggested={part.text} />
		{:else}
			<span class="cr-comment-body mt-0.5 block whitespace-pre-wrap">{part.text}</span>
		{/if}
	{/each}
{/snippet}

<!-- What has been written, a summary, and the two ways out -->
<div class="flex max-h-[70vh] flex-col">
	<div class="flex items-baseline gap-2 border-b border-base-300 px-4 py-2.5">
		<h3 class="text-sm font-semibold">
			{finishingTitle(submission.inRounds, review.rounds.current)}
		</h3>
		<span data-testid="finish-count" class="cr-faint text-xs">
			{#if submission.inRounds}
				{unsent} unsent of {review.threads.count}
			{:else}
				{counted(review.threads.count, 'comment', 'comments')}
			{/if}
		</span>
	</div>

	<div class="cr-scroller min-h-0 flex-1 px-4 py-3">
		{#if open.length > 0}
			<!-- Written and not added: it goes, as a pending comment does, so it is shown before it does -->
			<div data-testid="open-fields" class="mb-3">
				<p class="cr-faint mb-1.5 text-xs">
					{counted(open.length, 'comment still open goes', 'comments still open go')} with the review:
				</p>
				<ul class="flex flex-col gap-1.5">
					{#each open as { field, anchor } (field.key)}
						<li data-testid="open-field" class="px-2 py-1.5">
							<span class="cr-comment-ref font-mono text-xs">{anchorPlace(anchor)}</span>
							{@render said(field.text, anchor)}
						</li>
					{/each}
				</ul>
			</div>
		{/if}
		{#if review.threads.count === 0}
			{#if open.length === 0}
				<p class="cr-faint text-sm">Nothing written yet. A summary on its own is a review too.</p>
			{/if}
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
									<span class="cr-tag cr-severity-{thread.severity}">{thread.severity}</span>
								{/if}
								{#if raisedByAgent(thread)}
									<span class="cr-tag cr-raised-tag">agent</span>
								{/if}
								{#if thread.resolved}
									<span class="cr-tag cr-muted">resolved</span>
								{/if}
								<span class="flex-1"></span>
								{#if sent !== undefined}
									<span class="cr-faint shrink-0 text-xs">round {sent}</span>
								{/if}
							</span>
							{@render said(thread.body, thread.anchor)}
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
			maxlength={review.limits.max_text_length}
			aria-label="Summary of the review"
			value={submission.body}
			oninput={(event) => submission.setBody(event.currentTarget.value)}
		></textarea>

		<div class="mt-2 flex items-center gap-2">
			<span class="cr-faint hidden text-xs lg:inline">{FINISH_KEYS} sends</span>
			<div class="flex-1"></div>
			{#if submission.inRounds}
				<button
					type="button"
					data-testid="end-review"
					class="btn btn-ghost btn-sm"
					disabled={!submission.canEnd}
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
