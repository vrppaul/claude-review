<script lang="ts">
	import { onDestroy } from 'svelte';
	import { focusWhatCarries, focusWhatRemainsInItsCard } from '$lib/dom/keyboard';
	import { useReview } from '$lib/review/context';
	import type { FeedbackKind, FeedbackIssue, GoesWithIt } from '$lib/types';
	import Actions from '$lib/ui/Actions.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Callout from '$lib/ui/Callout.svelte';
	import Checkbox from '$lib/ui/Checkbox.svelte';
	import CodeBox from '$lib/ui/CodeBox.svelte';
	import Failure from '$lib/ui/Failure.svelte';
	import Field from '$lib/ui/Field.svelte';
	import Heading from '$lib/ui/Heading.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import Link from '$lib/ui/Link.svelte';
	import LinkButton from '$lib/ui/LinkButton.svelte';
	import Pane from '$lib/ui/Pane.svelte';
	import Segment from '$lib/ui/Segment.svelte';
	import Segmented from '$lib/ui/Segmented.svelte';
	import { HELP_BUTTON_ROLE } from './keymap';

	// What heads the card, and what its cross says it does
	const HEADING = 'Send feedback';
	const CLOSE_THE_FEEDBACK = 'Close the feedback';
	// The kinds of feedback in the order the switch draws them, what each is called there, and what the field asks
	const KIND_ORDER: FeedbackKind[] = ['bug', 'idea'];
	const KINDS: Record<FeedbackKind, { label: string; asks: string }> = {
		bug: { label: 'Bug', asks: 'What happened, and what did you expect?' },
		idea: { label: 'Idea', asks: 'What would make reviewing better?' }
	};
	// What each row that may go with the words is called
	const ROWS: { row: Exclude<GoesWithIt, 'part'>; label: string }[] = [
		{ row: 'machine', label: 'The version and your system' },
		{ row: 'reading', label: 'What you were reading' }
	];
	// The review's promise over what goes, and where anyone can read the code that keeps it
	const PROMISE = 'None of your code goes, and nothing of your review.';
	const WRITER_OF_THE_ISSUE =
		'https://github.com/vrppaul/claude-review/blob/master/src/claude_review/services/feedback.py';
	// Where the issue opens, said before it does
	const WHERE_IT_OPENS =
		'Opens a public issue in vrppaul/claude-review, where you read it once more before it is sent.';
	const TOO_LONG = 'Too long for GitHub to take filled in.';

	const review = useReview();
	const feedback = $derived(review.feedback);
	const stage = $derived(feedback.stage);

	let field = $state<HTMLTextAreaElement>();
	let toGitHub = $state<HTMLAnchorElement>();
	let done = $state<HTMLButtonElement>();

	// The card opens with the keyboard in the field, and Edit brings it back there: the words are what it is for
	$effect(() => {
		field?.focus({ preventScroll: true });
	});

	// The preview offers the act it leads to, and where it went offers Done, in sight in a card that scrolls: what
	// pressed it is gone
	$effect(() => {
		if (stage.step === 'preview') focusWhatRemainsInItsCard(() => toGitHub);
		else if (stage.step === 'went') focusWhatRemainsInItsCard(() => done);
	});

	// However the card goes — its cross, Done, or the tour or the news taking the corner — it opens next time on
	// what is written, and where the last feedback went is forgotten
	onDestroy(() => feedback.putAway());

	/** Put the card away, keeping what is written, and give the keyboard to Help, where the card is found again. */
	function putAway() {
		review.guide.closeFeedback();
		focusWhatCarries(HELP_BUTTON_ROLE);
	}

	/** The issue as it goes, to the letter: its title over its body. */
	function toTheLetter(issue: FeedbackIssue): string {
		return `${issue.title}\n\n${issue.body}`;
	}
</script>

<!-- The reader's feedback on claude-review, in the guide's corner: written, then shown to the letter before it
	goes, then where it went. The page stays uncovered while it is written -->
<Pane
	width="wide"
	testId="feedback"
	role="complementary"
	aria-label={HEADING}
	head={{ heading: HEADING, close: putAway, closing: CLOSE_THE_FEEDBACK }}
>
	<div class="cr-guide-card">
		{#if stage.step === 'writing'}
			<div class="flex">
				<Segmented label="What it is" size="xs" testId="feedback-kind">
					{#each KIND_ORDER as kind (kind)}
						<Segment
							testId="feedback-kind-{kind}"
							pressed={feedback.kind === kind}
							onclick={() => feedback.setKind(kind)}
						>
							{KINDS[kind].label}
						</Segment>
					{/each}
				</Segmented>
			</div>
			<Field
				bind:element={field}
				bind:value={() => feedback.words, (words: string) => feedback.setWords(words)}
				holds="comment"
				voice="reader"
				testId="feedback-words"
				placeholder={KINDS[feedback.kind].asks}
				maxlength={review.limits.max_feedback_length}
				aria-label="Your feedback"
			/>
			<p class="cr-faint text-xs">You see everything that goes before it is sent.</p>
			<Actions testId="feedback-writing-actions">
				{#snippet aside()}
					{#if !feedback.written}
						<span class="cr-faint text-xs">Write it first</span>
					{/if}
				{/snippet}
				{#snippet main()}
					<Button
						tone="primary"
						size="sm"
						testId="feedback-preview"
						disabled={!feedback.written}
						onclick={() => feedback.preview()}
					>
						Preview
					</Button>
				{/snippet}
			</Actions>
		{:else if stage.step === 'preview'}
			<!-- The issue shown, named once, so what its snippets do is held to it -->
			{@const issue = stage.issue}
			<Callout tone="kept" lead={PROMISE} testId="feedback-promise">
				No repository, branch, file, line, comment or story: only what you wrote and the rows you leave ticked. The
				issue below is all of it, to the letter.
				{#snippet check()}
					<Link href={WRITER_OF_THE_ISSUE} testId="feedback-writer">Read the code that writes it</Link>
				{/snippet}
			</Callout>
			<div class="flex flex-col gap-2 text-xs">
				{#each ROWS as each (each.row)}
					<Checkbox
						drawn="box"
						note={issue.with_it[each.row]}
						checked={feedback.isGoing(each.row)}
						testId="feedback-goes-{each.row}"
						onToggle={(checked: boolean) => feedback.setGoing(each.row, checked)}
					>
						{each.label}
					</Checkbox>
				{/each}
			</div>
			<div class="flex flex-col gap-2">
				<div class="flex items-center justify-between gap-2">
					<Heading tag="h3" heads="list">The issue, to the letter</Heading>
					<Button tone="quiet" size="xs" testId="feedback-edit" onclick={() => feedback.edit()}>Edit</Button>
				</div>
				<CodeBox code={toTheLetter(issue)} wrapped testId="feedback-issue" />
			</div>
			<p class="cr-faint text-xs">{WHERE_IT_OPENS}</p>
			<Actions testId="feedback-preview-actions">
				{#snippet aside()}
					{#if !review.canAsk}
						<span class="cr-faint text-xs">No agent here</span>
					{/if}
				{/snippet}
				{#snippet others()}
					<Button
						tone="asking"
						size="sm"
						testId="feedback-hand-to-agent"
						disabled={!review.canAsk}
						onclick={() => feedback.handToAgent(issue)}
					>
						Hand to the agent
					</Button>
				{/snippet}
				{#snippet main()}
					<LinkButton
						bind:element={toGitHub}
						tone="primary"
						size="sm"
						href={issue.address}
						onfollow={() => feedback.openedOnGitHub(issue)}
						testId="feedback-open-on-github"
					>
						Open on GitHub
					</LinkButton>
				{/snippet}
			</Actions>
		{:else if stage.step === 'went' && stage.went === 'opened'}
			{@const issue = stage.issue}
			<div class="flex items-start gap-3">
				<Icon name="decided" size="sm" tone="done" />
				<p class="cr-guide-body">Opened on GitHub, in a new tab. Read it there and press Submit.</p>
			</div>
			<Actions testId="feedback-went-actions">
				{#snippet others()}
					<Button tone="quiet" size="sm" testId="feedback-copy" onclick={() => feedback.copyText(issue)}>
						Copy the text
					</Button>
				{/snippet}
				{#snippet main()}
					<Button bind:element={done} tone="primary" size="sm" testId="feedback-done" onclick={putAway}>Done</Button>
				{/snippet}
			</Actions>
		{:else if stage.step === 'went' && stage.went === 'too-long'}
			{@const issue = stage.issue}
			<Callout tone="warning" lead={TOO_LONG} testId="feedback-too-long">
				The issue opened with its title alone, and the text is copied: paste it there.
			</Callout>
			<Actions testId="feedback-went-actions">
				{#snippet others()}
					<Button tone="quiet" size="sm" testId="feedback-copy" onclick={() => feedback.copyText(issue)}>
						Copy the text again
					</Button>
				{/snippet}
				{#snippet main()}
					<Button bind:element={done} tone="primary" size="sm" testId="feedback-done" onclick={putAway}>Done</Button>
				{/snippet}
			</Actions>
		{:else if stage.step === 'went'}
			<div class="flex items-start gap-3">
				<Icon name="conversation" size="sm" tone="agent" />
				<p class="cr-guide-body">Handed to the agent. It answers in its panel.</p>
			</div>
			<Actions testId="feedback-went-actions">
				{#snippet others()}
					<Button
						tone="quiet"
						size="sm"
						testId="feedback-show-panel"
						onclick={() => review.layout.agentPanel.setOpen(true)}
					>
						Show the panel
					</Button>
				{/snippet}
				{#snippet main()}
					<Button bind:element={done} tone="primary" size="sm" testId="feedback-done" onclick={putAway}>Done</Button>
				{/snippet}
			</Actions>
		{/if}
		{#if feedback.failed}
			<Failure stands="apart" testId="feedback-failed" said={feedback.failed} />
		{/if}
	</div>
</Pane>
