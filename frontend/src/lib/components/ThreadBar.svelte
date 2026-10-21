<script lang="ts">
	import type { Thread } from '$lib/types';
	import { useReview } from '$lib/review/context';
	import BreathingDots from '$lib/ui/BreathingDots.svelte';
	import Button from '$lib/ui/Button.svelte';
	import CardBar from '$lib/ui/CardBar.svelte';
	import Dot from '$lib/ui/Dot.svelte';
	import FoldedSummary from '$lib/ui/FoldedSummary.svelte';
	import FoldToggle from '$lib/ui/FoldToggle.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import Standing from '$lib/ui/Standing.svelte';
	import Tag from '$lib/ui/Tag.svelte';
	import { plainWords } from '$lib/utils/plain-words';
	import { raisedByAgent } from '$lib/utils/speakers';
	import { counted, type CountedWords } from '$lib/utils/words';
	import { headingOf } from './anchor-headings';
	import ReopenButton from './ReopenButton.svelte';
	import { severityTone } from './severity-tone';
	import ThreadMenu from './ThreadMenu.svelte';
	import { threadVoice } from './thread-voice';

	// What everything said under the comment that opened a thread is called, counted: the agent's and the reader's alike
	const REPLIES: CountedWords = { one: 'reply', many: 'replies' };
	// What a folded thread's first words are, where the comment that opened it is an image and nothing more
	const AN_IMAGE = 'an image';

	interface Props {
		thread: Thread;
		/** Whether the thread is folded to this bar, which then says what it holds. */
		folded: boolean;
	}

	let { thread, folded }: Props = $props();
	const review = useReview();

	const AnchorHeading = $derived(headingOf(thread.anchor));
	const sentIn = $derived(review.threads.sentInRound(thread.id));
	const answering = $derived(review.threads.reading.awaiting(thread.id).length > 0);
	const unread = $derived(review.threads.reading.isUnread(thread.id));
	// A thread the agent raised is the agent's: the reader answers its words and settles it, and never rewrites it
	// nor deletes it — the review keeps it whatever a page says, and it would come back
	const raised = $derived(raisedByAgent(thread));

	/** Fold the thread away or open it; the keyboard stays on the toggle, drawn anew on the bar as it now stands. */
	function toggleFold() {
		review.threads.reading.setFolded(thread.id, !folded);
		review.sections.keyboardToThreadFold(thread.id);
	}

	/** Settle the thread, which folds it; the keyboard stays with it. */
	function resolve() {
		review.threads.setResolved(thread.id, true);
		review.sections.keyboardToThread(thread.id);
	}
</script>

<!-- The bar heading a thread's card, the same open and folded: where it hangs, what it asks for and where it
	stands — settled, or the round it went out in, which the grey of a folded one says already — whether the agent
	is answering and whether a reply is new, which a folded thread still says; folded, who began it, their first
	words and how many replies are under it; then Resolve or Reopen, the reader's own thread's menu, and the fold -->
<CardBar testId="thread-bar">
	{#snippet place()}
		<AnchorHeading anchor={thread.anchor} />
	{/snippet}
	{#if thread.severity !== 'note'}
		<Tag tone={severityTone(thread)} testId="comment-severity">{thread.severity}</Tag>
	{/if}
	{#if thread.anchor.outdated}
		<Tag tone="warning" testId="comment-outdated">outdated</Tag>
	{/if}
	{#if thread.resolved}
		<Standing tone="done" testId="comment-resolved"><Icon name="check" size="xs" tone="done" /> resolved</Standing>
	{:else if sentIn !== undefined && !folded}
		<Standing tone="quiet" testId="comment-sent">sent in round {sentIn}</Standing>
	{/if}
	{#if answering}
		<Standing tone="agent" testId="comment-answering"
			><BreathingDots tone="quiet" testId="comment-answering-dots" /> answering</Standing
		>
	{/if}
	{#if unread}
		<Standing tone="unread" testId="comment-unread"
			><Dot tone="unread" testId="comment-unread-dot" /> new reply</Standing
		>
	{/if}
	{#if folded}
		<FoldedSummary voice={threadVoice(thread)} words={plainWords(thread.body) || AN_IMAGE} testId="folded-summary" />
		{#if thread.turns.length > 0}
			<Standing tone="faint" testId="folded-replies">{counted(thread.turns.length, REPLIES)}</Standing>
		{/if}
	{/if}
	{#snippet end()}
		{#if thread.resolved}
			<ReopenButton {thread} />
		{:else}
			<!-- Settling a thread folds it away; it can still be opened and read -->
			<Button tone="secondary" size="xs" testId="resolve-comment" onclick={resolve}>
				<Icon name="check" size="xs" tone="done" />
				Resolve
			</Button>
		{/if}
		{#if !raised}
			<ThreadMenu {thread} />
		{/if}
		<FoldToggle
			{folded}
			subject="this thread"
			testId={folded ? 'unfold-thread' : 'fold-comment'}
			tone="quiet"
			onToggle={toggleFold}
		/>
	{/snippet}
</CardBar>
