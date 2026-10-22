<script lang="ts">
	import type { Anchor, Thread } from '$lib/types';
	import { anchorPlace, anchorReplaces } from '$lib/anchors/views';
	import { tourStop } from '$lib/guide/tour';
	import { useReview } from '$lib/review/context';
	import Actions from '$lib/ui/Actions.svelte';
	import BreathingDots from '$lib/ui/BreathingDots.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Chip from '$lib/ui/Chip.svelte';
	import Count from '$lib/ui/Count.svelte';
	import Failure from '$lib/ui/Failure.svelte';
	import Field from '$lib/ui/Field.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import IconButton from '$lib/ui/IconButton.svelte';
	import ItemCard from '$lib/ui/ItemCard.svelte';
	import PassingNote from '$lib/ui/PassingNote.svelte';
	import Popover from '$lib/ui/Popover.svelte';
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
	// The threads the next round carries, which wait for it in the list
	const waiting = $derived(new Set(review.threads.unsent));
	// What goes with what the button sends: what is unsent, with a round; everything, with the end
	const going = $derived(inRounds ? unsent : review.threads.count);
	const goingSaid = $derived(counted(going, GOING_WITH_IT));
	// Comments still open in their fields, which go with whatever is sent
	const open = $derived(review.threads.open);
	// The button the pane opens from, which a send that did not go is said under
	let sendButton = $state<HTMLButtonElement>();

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

<!-- What a comment says, on its card: its words run together, and a suggestion as the change it makes -->
{#snippet said(body: string, anchor: Anchor)}
	{#each splitSuggestions(body) as part, partIndex (partIndex)}
		{#if part.kind === 'suggestion'}
			<SuggestionDiff replaced={anchorReplaces(anchor)} suggested={part.text} />
		{:else}
			{part.text}
		{/if}
	{/each}
{/snippet}

<!-- Where a comment hangs, on its card: a chip of the reader's, the card being the way there, its whole place on
	the pointer where the line's end cuts it -->
{#snippet placed(anchor: Anchor, testId: string)}
	{@const place = anchorPlace(anchor)}
	<Chip voice="reader" names="place" reachedByItsHolder title={place} {testId}>{place}</Chip>
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

<!-- One door: what has been written, a summary, and the two ways out; and under it, the pane put away, why a send
	through it did not go -->
<div class="relative">
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
				bind:element={sendButton}
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
							<li>
								<ItemCard beingWritten testId="open-field">
									{#snippet place()}
										{@render placed(anchor, 'open-field-place')}
									{/snippet}
									{#snippet below()}
										{@render said(field.text, anchor)}
									{/snippet}
								</ItemCard>
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
				<!-- Each comment a card, one press to its thread, read whole there: where it hangs and what is said of it
				on one line, its words under that; one holding what the agent does not have waits for this round, one
				the agent has whole steps back, saying the round it went in -->
				<ul class="flex flex-col gap-1.5">
					{#each review.threads.all as thread (thread.id)}
						{@const waits = waiting.has(thread)}
						{@const wentIn = review.threads.handing.roundOf(thread.id)}
						<li>
							<ItemCard testId="finish-comment" {waits} onclick={() => jump(thread)}>
								{#snippet place()}
									{@render placed(thread.anchor, 'modal-comment-ref')}
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
									{#if !waits && wentIn !== undefined}
										<span class="cr-faint">round {wentIn}</span>
									{/if}
								{/snippet}
								{#snippet below()}
									{@render said(thread.body, thread.anchor)}
								{/snippet}
							</ItemCard>
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	</Popover>
	{#if submission.failed}
		{@const failed = submission.failed}
		<!-- As the note of a story that arrived stands under Story: pointing at Send, in the colour of what failed,
			its time running out along its foot, and put away by its cross. Called for whatever the pane did, a send
			or the end, which its words name -->
		<PassingNote
			pointsAt={sendButton}
			label="Not done"
			placement="below-end"
			arrow
			edge="failure"
			fades={false}
			testId="send-failed"
			onGone={() => submission.putFailureAway()}
		>
			{#snippet children(putAway: () => void)}
				<!-- Its words and its cross, as a pane's head holds its name and its close: no act to lead to, so no row of
					acts, whose last is always one -->
				<div class="flex items-center gap-2 py-2 pr-2 pl-3">
					<Failure stands="inline" testId="submit-error" said={failed} />
					<IconButton tone="quiet" size="sm" shape="square" label="Close" testId="send-failed-close" onclick={putAway}>
						<Icon name="cross" size="xs" />
					</IconButton>
				</div>
			{/snippet}
		</PassingNote>
	{/if}
</div>
