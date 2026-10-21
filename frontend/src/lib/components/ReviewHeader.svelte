<script lang="ts">
	import { tourStop } from '$lib/guide/tour';
	import { useReview } from '$lib/review/context';
	import type { Ending } from '$lib/review/server-link.svelte';
	import Bar from '$lib/ui/Bar.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Dot from '$lib/ui/Dot.svelte';
	import Failure from '$lib/ui/Failure.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import IconButton from '$lib/ui/IconButton.svelte';
	import type { IconName } from '$lib/ui/icons';
	import type { NoticeTone } from '$lib/ui/notice';
	import NoticeBar from '$lib/ui/NoticeBar.svelte';
	import BasePicker from './BasePicker.svelte';
	import FinishReview from './FinishReview.svelte';
	import HelpMenu from './HelpMenu.svelte';
	import { PANEL_TOGGLE_ROLE } from './keymap';
	import PresenceDot from './PresenceDot.svelte';
	import RepliesMenu from './RepliesMenu.svelte';
	import SettingsMenu from './SettingsMenu.svelte';
	import ViewSwitch from './ViewSwitch.svelte';
	import WhereTheChangeIs from './WhereTheChangeIs.svelte';

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

	const over = $derived(review.link.ending === null ? null : OVER[review.link.ending]);
</script>

{#if over}
	<NoticeBar tone={over.tone} icon={over.icon} testId={over.testId}>{over.said}</NoticeBar>
{:else}
	<!-- One row whatever the width, its controls as tall as a small button: as the window narrows, each control's
		words give way to its mark at a breakpoint of its own, kept for a screen reader and on the pointer -->
	<Bar heads="page" testId="top-bar">
		<WhereTheChangeIs />
		<HelpMenu />
		<!-- Right after Help, where it never moves, whatever else the header shows -->
		<ViewSwitch />
		<!-- What the diff is compared against, as a control. A story is of the review's own diff whatever base the
		files are read against, so it shows none -->
		{#if review.views.onScreen.name === 'files' && review.diff.phrase}
			<BasePicker />
			{#if review.settings.current.ignore_whitespace}
				<!-- Said here as well as in the settings, because it hides changes: in the reader's mark, as a
					narrower base is, since it narrows the diff too. Pressed, it shows them again -->
				<Button
					tone="marked"
					size="sm"
					testId="whitespace-hidden"
					aria-label={SHOW_WHITESPACE_AGAIN}
					title={SHOW_WHITESPACE_AGAIN}
					onclick={() => review.setIgnoreWhitespace(false)}
				>
					<span class="max-xl:sr-only">No whitespace</span>
					<Icon name="cross" size="xs" />
				</Button>
			{/if}
		{/if}

		<div class="flex-1"></div>

		{#if review.submission.failed}
			<Failure stands="inline" testId="submit-error" said={review.submission.failed} />
		{/if}

		{#if review.threads.answered.length > 0}
			<RepliesMenu />
		{/if}

		{#if review.threads.count > 0}
			<div class="flex">
				<IconButton
					tone="quiet"
					size="sm"
					label="Previous comment"
					testId="prev-comment"
					onclick={() => review.navigator.step(-1)}
				>
					<Icon name="chevron" size="xs" pointing="up" />
				</IconButton>
				<IconButton
					tone="quiet"
					size="sm"
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
			size="sm"
			testId="toggle-panel"
			data-role={PANEL_TOGGLE_ROLE}
			data-tour={tourStop('agent-panel-toggle')}
			aria-pressed={review.layout.agentPanel.open}
			title="The agent panel — talk about the review, not one line of it"
			onclick={() => review.layout.agentPanel.toggle()}
		>
			<PresenceDot />
			<span class="max-lg:sr-only">Agent</span>
			{#if review.layout.agentPanel.unread > 0}
				<Dot tone="unread" testId="panel-unread" /><span class="sr-only">new answers</span>
			{/if}
		</Button>

		<FinishReview />

		<SettingsMenu />
	</Bar>
	{#if review.link.state === 'reconnecting'}
		<!-- Not over until the review says so: the page tries again, and holds every send meanwhile -->
		<NoticeBar tone="warning" icon="notice" testId="connection-lost">
			The review cannot be reached — trying again. What you write is kept. Nothing is sent until it is back.
		</NoticeBar>
	{/if}
{/if}
