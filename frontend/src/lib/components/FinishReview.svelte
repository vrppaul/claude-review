<script lang="ts">
	import type { Anchor, Thread } from '$lib/types';
	import { anchorPlace, anchorReplaces } from '$lib/anchors/views';
	import { tourStop } from '$lib/guide/tour';
	import { useReview } from '$lib/review/context';
	import Actions from '$lib/ui/Actions.svelte';
	import BreathingDots from '$lib/ui/BreathingDots.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Count from '$lib/ui/Count.svelte';
	import Field from '$lib/ui/Field.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import Popover from '$lib/ui/Popover.svelte';
	import Row from '$lib/ui/Row.svelte';
	import Tag from '$lib/ui/Tag.svelte';
	import { raisedByAgent } from '$lib/utils/speakers';
	import { splitSuggestions } from '$lib/utils/suggestion';
	import { COMMENTS, counted, type CountedWords } from '$lib/utils/words';
	import { finishingTitle } from './finishing';
	import { FINISH_KEYS } from './keymap';
	import { severityTone } from './severity-tone';
	import SuggestionDiff from './SuggestionDiff.svelte';

	// What the comments still open in their fields are said to do, counted
	const OPEN_COMMENTS_GOING: CountedWords = { one: 'comment still open goes', many: 'comments still open go' };
	// What the comments that go with a send are said to do, counted on the button that sends them
	const GOING_WITH_IT: CountedWords = { one: 'comment goes with it', many: 'comments go with it' };

	const review = useReview();

	const submission = review.submission;
	const inRounds = $derived(submission.inRounds);
	// What the pane is called, and headed with: the round it sends, or the end
	const title = $derived(finishingTitle(inRounds, review.rounds.current));
	const unsent = $derived(review.threads.unsent.length);
	// What goes with what the button sends: what is unsent, with a round; everything, with the end
	const going = $derived(inRounds ? unsent : review.threads.count);
	const goingSaid = $derived(counted(going, GOING_WITH_IT));
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
		<Field
			{@attach focusOnDraw}
			holds="message"
			voice="reader"
			testId="review-body"
			placeholder="Summary — optional, about the change as a whole"
			maxlength={review.limits.max_text_length}
			aria-label="Summary of the review"
			value={submission.body}
			oninput={(event: Event & { currentTarget: HTMLTextAreaElement }) => submission.setBody(event.currentTarget.value)}
		/>

		<div class="mt-2">
			<Actions testId="finish-actions">
				{#snippet aside()}
					<span class="cr-faint hidden text-xs lg:inline">{FINISH_KEYS} sends</span>
				{/snippet}
				{#snippet others()}
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
				{/snippet}
				{#snippet main()}
					<Button
						tone="primary"
						size="sm"
						testId="modal-submit"
						disabled={!submission.canSend}
						onclick={() => submission.send()}
					>
						{#if submission.sending}
							<BreathingDots tone="inherited" testId="pane-sending-dots" />
							Sending
						{:else if inRounds}
							Send round {review.rounds.current}
						{:else}
							Send review
						{/if}
					</Button>
				{/snippet}
			</Actions>
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
			data-tour={tourStop('send')}
			disabled={submission.sending}
			title={FINISH_KEYS}
		>
			{#if submission.sending}
				<BreathingDots tone="inherited" testId="sending-dots" />
				Sending
			{:else if inRounds}
				<!-- The round's number gives way last, with the branch, kept in Send's name; Send keeps its word and its
					count -->
				<!-- One run of words, as the board writes it, a word's space before the round -->
				<span>Send <span class="max-cr-header-narrowest:sr-only">round {review.rounds.current}</span></span>
			{:else}
				Finish review
			{/if}
			{#if going > 0}
				<!-- The figure seen, its words in Send's name, apart from the round's number, and on the pointer -->
				<Count
					tone="reader"
					count={going}
					title={goingSaid}
					aria-hidden
					data-tour={tourStop('unsent-count')}
					testId="unsent-count"
				/>
				<span class="sr-only">({goingSaid})</span>
			{/if}
			<Icon name="chevron" size="xs" />
		</Button>
	{/snippet}

	<div class="px-3 py-3">
		{#if open.length > 0}
			<!-- Written and not added: it goes, as a pending comment does, so it is shown before it does -->
			<div data-testid="open-fields" class="mb-3">
				<p class="cr-faint mb-1.5 text-xs">
					{counted(open.length, OPEN_COMMENTS_GOING)} with the review:
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
			<!-- Each comment a row, one press to its thread, all of it: where it hangs on its line and what it says
				in full under that; one sent with a round steps back -->
			<ul class="flex flex-col gap-1.5">
				{#each review.threads.all as thread (thread.id)}
					{@const sent = review.threads.sentInRound(thread.id)}
					<li>
						<Row names="path" testId="finish-comment" viewed={sent !== undefined} onclick={() => jump(thread)}>
							{#snippet label()}
								<span data-testid="modal-comment-ref" class="cr-comment-ref">{anchorPlace(thread.anchor)}</span>
							{/snippet}
							{#snippet trailing()}
								{#if thread.severity !== 'note'}
									<Tag tone={severityTone(thread)} testId="finish-severity">{thread.severity}</Tag>
								{/if}
								{#if raisedByAgent(thread)}
									<Tag tone="agent" testId="finish-raised">agent</Tag>
								{/if}
								{#if thread.resolved}
									<Tag tone="quiet" testId="finish-resolved">resolved</Tag>
								{/if}
								{#if sent !== undefined}
									<span class="cr-faint">round {sent}</span>
								{/if}
							{/snippet}
							{#snippet below()}
								{@render said(thread.body, thread.anchor)}
							{/snippet}
						</Row>
					</li>
				{/each}
			</ul>
		{/if}
	</div>
</Popover>
