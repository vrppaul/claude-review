<script lang="ts">
	import { useReview } from '$lib/review/context';
	import type { Ending } from '$lib/review/server-link.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Dot from '$lib/ui/Dot.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import IconButton from '$lib/ui/IconButton.svelte';
	import type { IconName } from '$lib/ui/icons';
	import type { NoticeTone } from '$lib/ui/notice';
	import NoticeBar from '$lib/ui/NoticeBar.svelte';
	import { COMMENTS, counted } from '$lib/utils/words';
	import BasePicker from './BasePicker.svelte';
	import FinishReview from './FinishReview.svelte';
	import HelpMenu from './HelpMenu.svelte';
	import { PANEL_TOGGLE_ROLE } from './keymap';
	import PresenceDot from './PresenceDot.svelte';
	import RepliesMenu from './RepliesMenu.svelte';
	import SettingsMenu from './SettingsMenu.svelte';
	import ViewSwitch from './ViewSwitch.svelte';

	/** What the header says in place of everything else once the review is over, and the notice it says it in. */
	interface Over {
		testId: string;
		said: string;
		/** Done once it was sent; a warning where it ended under the reader, their unsent work waiting for them. */
		tone: NoticeTone;
		icon: IconName;
	}

	// By how the review ended
	const OVER: Record<Ending, Over> = {
		finished: { testId: 'submitted-banner', said: 'Review sent. You can close this tab.', tone: 'done', icon: 'check' },
		stopped: {
			testId: 'review-stopped',
			said: 'The review has stopped. What you had not sent is kept, and comes back when you open it again.',
			tone: 'warning',
			icon: 'notice'
		},
		replaced: {
			testId: 'review-replaced',
			said: 'This review is over: another review is running here now. What you had not sent is kept for when you open this one again.',
			tone: 'warning',
			icon: 'notice'
		}
	};

	// What pressing the header's note that whitespace is hidden does: its name, for whoever cannot see the note's
	// words say a state, and its hint under the pointer
	const SHOW_WHITESPACE_AGAIN = 'Show whitespace changes again';

	const review = useReview();

	const inRounds = $derived(review.submission.inRounds);
	const over = $derived(review.link.ending === null ? null : OVER[review.link.ending]);
</script>

{#if over}
	<NoticeBar tone={over.tone} icon={over.icon} testId={over.testId}>{over.said}</NoticeBar>
{:else}
	<!-- One row while it fits; on a narrow screen the controls wrap onto another, none cut off -->
	<header
		data-testid="top-bar"
		class="flex min-h-12 shrink-0 flex-wrap items-center gap-x-3 gap-y-1.5 border-b border-base-300 bg-base-200 px-4 py-1.5"
	>
		<span class="font-semibold">Review</span>
		<HelpMenu />
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
					<!-- Said here as well as in the settings, because it hides changes: in the reader's mark, as a
						narrower base is, since it narrows the diff too. Pressed, it shows them again -->
					<Button
						tone="marked"
						size="xs"
						testId="whitespace-hidden"
						aria-label={SHOW_WHITESPACE_AGAIN}
						title={SHOW_WHITESPACE_AGAIN}
						onclick={() => review.setIgnoreWhitespace(false)}
					>
						No whitespace
						<Icon name="cross" size="xs" />
					</Button>
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
				{counted(review.threads.count, COMMENTS)}
			{/if}
		</span>

		{#if review.threads.count > 0}
			<div class="flex">
				<IconButton
					tone="quiet"
					size="xs"
					label="Previous comment"
					testId="prev-comment"
					onclick={() => review.navigator.step(-1)}
				>
					<Icon name="chevron" size="xs" pointing="up" />
				</IconButton>
				<IconButton
					tone="quiet"
					size="xs"
					label="Next comment"
					testId="next-comment"
					onclick={() => review.navigator.step(1)}
				>
					<Icon name="chevron" size="xs" />
				</IconButton>
			</div>
		{/if}

		<Button
			tone="quiet"
			size="xs"
			testId="toggle-panel"
			data-role={PANEL_TOGGLE_ROLE}
			data-tour="agent-panel-toggle"
			aria-pressed={review.layout.agentPanel.open}
			title="The agent panel — talk about the review, not one line of it"
			onclick={() => review.layout.agentPanel.toggle()}
		>
			<PresenceDot />
			Agent
			{#if review.layout.agentPanel.unread > 0}
				<Dot tone="unread" testId="panel-unread" /><span class="sr-only">new answers</span>
			{/if}
		</Button>

		<FinishReview />

		<SettingsMenu />
	</header>
	{#if review.link.state === 'reconnecting'}
		<!-- Not over until the review says so: the page tries again, and holds every send meanwhile -->
		<NoticeBar tone="warning" icon="notice" testId="connection-lost">
			The review cannot be reached — trying again. What you write is kept. Nothing is sent until it is back.
		</NoticeBar>
	{/if}
{/if}
