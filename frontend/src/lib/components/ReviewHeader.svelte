<script lang="ts">
	import { useReview } from '$lib/review/context';
	import type { Ending } from '$lib/review/server-link.svelte';
	import { counted } from '$lib/utils/words';
	import BasePicker from './BasePicker.svelte';
	import { finishingTitle } from './finishing';
	import FinishReview from './FinishReview.svelte';
	import Icon from './Icon.svelte';
	import { FINISH_KEYS, HELP_BUTTON_ROLE } from './keymap';
	import Popover from './Popover.svelte';
	import PresenceDot from './PresenceDot.svelte';
	import RepliesMenu from './RepliesMenu.svelte';
	import SettingsMenu from './SettingsMenu.svelte';
	import ViewSwitch from './ViewSwitch.svelte';

	/** What the header says in place of everything else once the review is over. */
	interface Over {
		testId: string;
		said: string;
		/** Whether it ended under the reader, with their unsent work waiting for them: a warning, not a done deal. */
		underTheReader: boolean;
	}

	// By how the review ended
	const OVER: Record<Ending, Over> = {
		finished: { testId: 'submitted-banner', said: 'Review sent. You can close this tab.', underTheReader: false },
		stopped: {
			testId: 'review-stopped',
			said: 'The review has stopped. What you had not sent is kept, and comes back when you open it again.',
			underTheReader: true
		},
		replaced: {
			testId: 'review-replaced',
			said: 'This review is over: another review is running here now. What you had not sent is kept for when you open this one again.',
			underTheReader: true
		}
	};

	const review = useReview();

	const inRounds = $derived(review.submission.inRounds);
	const over = $derived(review.link.ending === null ? null : OVER[review.link.ending]);
</script>

{#if over}
	<div
		data-testid={over.testId}
		class={[
			'flex min-h-12 shrink-0 items-center justify-center gap-3 border-b border-base-300 px-4 py-2 text-center',
			over.underTheReader ? 'cr-warning-bar' : 'bg-base-200'
		]}
	>
		{#if over.underTheReader}
			<Icon name="notice" class="h-4 w-4" />
		{:else}
			<Icon name="check" class="h-4 w-4 text-(--cr-done)" />
		{/if}
		<p class="font-semibold">{over.said}</p>
	</div>
{:else}
	<!-- One row while it fits; on a narrow screen the controls wrap onto another, none cut off -->
	<header
		data-testid="top-bar"
		class="flex min-h-12 shrink-0 flex-wrap items-center gap-x-3 gap-y-1.5 border-b border-base-300 bg-base-200 px-4 py-1.5"
	>
		<span class="font-semibold">Review</span>
		<!-- The ? key may belong to a browser extension, so the list has a button too -->
		<button
			type="button"
			data-testid="open-help"
			data-role={HELP_BUTTON_ROLE}
			class="cr-chip"
			title="The tour, what is new, and the keys (?)"
			onclick={() => review.guide.setHelpOpen(true)}
		>
			<kbd class="cr-guide-key">?</kbd> Help
		</button>
		<!-- Right after Help, where it never moves, whatever else the header shows -->
		<ViewSwitch />
		<!-- What the diff is compared against, as a control. The repository it is
		of is in the tab's title; the header has room only for what changes. A
		story is of the review's own diff whatever base the files are read
		against, so it shows none. -->
		{#if review.views.onScreen.name === 'files'}
			{#if review.diff.phrase}
				<BasePicker />
				{#if review.settings.current.ignore_whitespace}
					<!-- Said here as well as in the settings, because it hides changes -->
					<span data-testid="whitespace-hidden" class="cr-chip cr-chip-narrowing">
						No whitespace
						<button
							type="button"
							data-testid="show-whitespace"
							class="btn btn-ghost btn-xs px-1"
							aria-label="Show whitespace changes again"
							title="Show whitespace changes again"
							onclick={() => review.setIgnoreWhitespace(false)}
						>
							<Icon name="cross" class="h-2.5 w-2.5" />
						</button>
					</span>
				{/if}
			{:else if review.title}
				<span data-testid="review-title" class="cr-muted truncate font-mono text-xs">
					{review.title}
				</span>
			{/if}
		{/if}

		<div class="flex-1"></div>

		{#if review.submission.failed}
			<span data-testid="submit-error" class="text-sm text-error">{review.submission.failed}</span>
		{/if}

		{#if review.threads.answered.length > 0}
			<RepliesMenu />
		{/if}

		<span data-testid="comment-count" data-tour="unsent-count" class="cr-muted text-sm">
			{#if inRounds}
				{review.threads.unsent.length} unsent · {review.threads.count}
			{:else}
				{counted(review.threads.count, 'comment', 'comments')}
			{/if}
		</span>

		{#if review.threads.count > 0}
			<div class="join">
				<button
					type="button"
					data-testid="prev-comment"
					class="btn join-item btn-ghost btn-xs"
					onclick={() => review.navigator.step(-1)}
					title="Previous comment"
					aria-label="Previous comment"
				>
					<Icon name="chevron" class="h-3 w-3 rotate-180" />
				</button>
				<button
					type="button"
					data-testid="next-comment"
					class="btn join-item btn-ghost btn-xs"
					onclick={() => review.navigator.step(1)}
					title="Next comment"
					aria-label="Next comment"
				>
					<Icon name="chevron" class="h-3 w-3" />
				</button>
			</div>
		{/if}

		<button
			type="button"
			data-testid="toggle-panel"
			data-tour="agent-panel-toggle"
			class="cr-chip"
			aria-pressed={review.layout.agentPanel.open}
			title="The agent panel — talk about the review, not one line of it"
			onclick={() => review.layout.agentPanel.toggle()}
		>
			<PresenceDot />
			Agent
			{#if review.layout.agentPanel.unread > 0}
				<span data-testid="panel-unread" class="text-(--cr-unread)">
					<span aria-hidden="true">●</span><span class="sr-only">new answers</span>
				</span>
			{/if}
		</button>

		<!-- One door: what has been written, a summary, and the two ways out -->
		<Popover
			bind:open={() => review.submission.finishing, (open: boolean) => review.submission.setFinishing(open)}
			label={finishingTitle(inRounds, review.rounds.current)}
			placement="below-end"
			data-testid="finish-review"
			class="w-[26rem]"
		>
			{#snippet trigger(control)}
				<button
					{...control}
					type="button"
					class="btn btn-primary btn-sm"
					data-testid="quick-submit"
					data-tour="send"
					disabled={review.submission.sending}
					title={FINISH_KEYS}
				>
					{#if review.submission.sending}
						<span class="loading loading-xs loading-spinner"></span>
						Sending
					{:else if inRounds}
						Send round {review.rounds.current}
					{:else}
						Finish review
					{/if}
					<Icon name="chevron" class="h-2.5 w-2.5" />
				</button>
			{/snippet}

			<FinishReview />
		</Popover>

		<SettingsMenu />
	</header>
	{#if review.link.state === 'reconnecting'}
		<!-- Not over until the review says so: the page tries again, and holds every send meanwhile -->
		<div
			data-testid="connection-lost"
			class="cr-warning-bar flex shrink-0 items-center gap-3 border-b border-base-300 px-4 py-1.5 text-xs"
		>
			<Icon name="notice" class="h-3 w-3 shrink-0" />
			<span>
				The review cannot be reached — trying again. What you write is kept. Nothing is sent until it is back.
			</span>
		</div>
	{/if}
{/if}
