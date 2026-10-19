<script lang="ts">
	import type { Anchor, Thread } from '$lib/types';
	import { anchorPlace, anchorReplaces } from '$lib/anchors/views';
	import { useReview } from '$lib/review/context';
	import Button from '$lib/ui/Button.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import Tag from '$lib/ui/Tag.svelte';
	import { raisedByAgent } from '$lib/utils/speakers';
	import { splitSuggestions } from '$lib/utils/suggestion';
	import { COMMENTS, counted } from '$lib/utils/words';
	import { finishingTitle } from './finishing';
	import { FINISH_KEYS } from './keymap';
	import Popover from './Popover.svelte';
	import { severityTone } from './severity-tone';
	import SuggestionDiff from './SuggestionDiff.svelte';

	const review = useReview();

	const submission = review.submission;
	const inRounds = $derived(submission.inRounds);
	// What the pane is called, and headed with: the round it sends, or the end
	const title = $derived(finishingTitle(inRounds, review.rounds.current));
	const unsent = $derived(review.threads.unsent.length);
	// Comments still open in their fields, which go with whatever is sent
	const open = $derived(review.threads.open);

	/** Put the pane away and go to a thread in it. */
	function jump(thread: Thread) {
		submission.setFinishing(false);
		review.navigator.reveal(thread);
	}

	/** The pane opens on the summary: the one thing in it that is written here. */
	function focusOnDraw(field: HTMLTextAreaElement) {
		field.focus();
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

<!-- How many comments go, beside the pane's heading: those unsent of all, in a review in rounds -->
{#snippet howMany()}
	<span data-testid="finish-count" class="cr-faint text-xs">
		{#if inRounds}
			{unsent} unsent of {review.threads.count}
		{:else}
			{counted(review.threads.count, COMMENTS)}
		{/if}
	</span>
{/snippet}

<!-- A summary, and the two ways out: at the pane's foot, in sight however far what was written scrolls -->
{#snippet sending()}
	<div class="p-3">
		<textarea
			{@attach focusOnDraw}
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
			{#if inRounds}
				<Button
					tone="quiet"
					size="sm"
					testId="end-review"
					disabled={!submission.canEnd}
					onclick={() => submission.end()}
				>
					End review
				</Button>
			{/if}
			<Button
				tone="primary"
				size="sm"
				testId="modal-submit"
				disabled={!submission.canSend}
				onclick={() => submission.send()}
			>
				{#if submission.sending}
					Sending
				{:else if inRounds}
					Send round {review.rounds.current}
				{:else}
					Send review
				{/if}
			</Button>
		</div>
	</div>
{/snippet}

<!-- One door: what has been written, a summary, and the two ways out -->
<Popover
	bind:open={() => submission.finishing, (opened: boolean) => submission.setFinishing(opened)}
	label={title}
	heading={title}
	aside={howMany}
	foot={sending}
	placement="below-end"
	width="wide"
	testId="finish-review"
>
	{#snippet trigger(control)}
		<Button
			{...control}
			tone="primary"
			size="sm"
			testId="quick-submit"
			data-tour="send"
			disabled={submission.sending}
			title={FINISH_KEYS}
		>
			{#if submission.sending}
				<span class="loading loading-xs loading-spinner"></span>
				Sending
			{:else if inRounds}
				Send round {review.rounds.current}
			{:else}
				Finish review
			{/if}
			<Icon name="chevron" size="xs" />
		</Button>
	{/snippet}

	<div class="px-3 py-3">
		{#if open.length > 0}
			<!-- Written and not added: it goes, as a pending comment does, so it is shown before it does -->
			<div data-testid="open-fields" class="mb-3">
				<p class="cr-faint mb-1.5 text-xs">
					{counted(open.length, { one: 'comment still open goes', many: 'comments still open go' })} with the review:
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
							class={['cr-pressable w-full rounded px-2 py-1.5 text-left', sent !== undefined && 'cr-viewed']}
							onclick={() => jump(thread)}
						>
							<span class="flex items-baseline gap-2">
								<span data-testid="modal-comment-ref" class="cr-comment-ref font-mono text-xs">
									{anchorPlace(thread.anchor)}
								</span>
								{#if thread.severity !== 'note'}
									<Tag tone={severityTone(thread)} testId="finish-severity">{thread.severity}</Tag>
								{/if}
								{#if raisedByAgent(thread)}
									<Tag tone="agent" testId="finish-raised">agent</Tag>
								{/if}
								{#if thread.resolved}
									<Tag tone="quiet" testId="finish-resolved">resolved</Tag>
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
</Popover>
