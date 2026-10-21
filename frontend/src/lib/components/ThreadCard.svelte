<script lang="ts">
	import type { Thread } from '$lib/types';
	import type { CommentField } from '$lib/review/comment-field.svelte';
	import { useReview } from '$lib/review/context';
	import Button from '$lib/ui/Button.svelte';
	import Card from '$lib/ui/Card.svelte';
	import type { CardHanging, CardTone } from '$lib/ui/card';
	import Conversation from '$lib/ui/Conversation.svelte';
	import Failure from '$lib/ui/Failure.svelte';
	import FieldButton from '$lib/ui/FieldButton.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import TurnAside from '$lib/ui/TurnAside.svelte';
	import { messageOf } from '$lib/utils/errors';
	import { AGENT, raisedByAgent } from '$lib/utils/speakers';
	import CommentBox from './CommentBox.svelte';
	import { PLACEHOLDERS } from './placeholders';
	import ThreadBar from './ThreadBar.svelte';
	import ThreadConversation from './ThreadConversation.svelte';
	import { threadVoice } from './thread-voice';

	/** How the card is drawn, which the tests know it by: open, folded by hand, or folded by settling it. */
	type Drawn = 'open' | 'folded' | 'settled';

	const TEST_IDS: Record<Drawn, string> = { open: 'thread-card', folded: 'folded-thread', settled: 'resolved-thread' };

	interface Props {
		thread: Thread;
		/** Where its card hangs: under its line, under a block of the story's words, or at the head of what it lost its place in. */
		hangs: CardHanging;
		/** Whether it is folded to its bar, the conversation under it put away. */
		folded: boolean;
	}

	let { thread, hangs, folded }: Props = $props();
	const review = useReview();
	const writing = review.threads.writing;

	let failed = $state<string | null>(null);

	// The reply being written here, held by the review so that folding the
	// thread or its file, or reloading the page, keeps it
	const replying = $derived(writing.reply(thread.id));
	const awaiting = $derived(review.threads.reading.awaiting(thread.id));
	// Who spoke last: after an answer there is nothing new to hand over until
	// the reader says something. On a thread the agent raised, the opening
	// is already the agent's word.
	const lastWord = $derived(thread.turns.at(-1)?.author ?? thread.raised_by);
	const askable = $derived(review.canAsk && awaiting.length === 0 && lastWord !== AGENT);
	// The field to reply in is edged in the colour of whose thread it is
	const voice = $derived(threadVoice(thread));
	// What has gone out with a round reads as read by the other side; what is
	// still unsent keeps the mark colour
	const sent = $derived(review.threads.sentInRound(thread.id) !== undefined);
	// Its card's edge and bar say where it stands: settled in the colour of what is done, the agent's colour when the
	// agent raised it, quieter once it went out with a round, faint once what it was written on is gone, and the
	// reader's mark while in their hands
	const tone = $derived.by<CardTone>(() => {
		if (thread.resolved) return 'done';
		if (raisedByAgent(thread)) return 'agent';
		if (sent) return 'quiet';
		return thread.anchor.outdated ? 'stale' : 'reader';
	});
	const drawn = $derived.by<Drawn>(() => {
		if (!folded) return 'open';
		return thread.resolved ? 'settled' : 'folded';
	});

	/** Looking at the thread — clicking in it, or moving the keyboard into it — is what makes its answer read. */
	function markRead() {
		review.threads.reading.markRead(thread.id);
	}

	/** Add the reply being written; the keyboard stays with the thread, where the field was. */
	function reply(written: CommentField) {
		review.threads.say(written);
		review.sections.keyboardToThread(thread.id);
	}

	/** Add the reply being written, and hand the thread over with it. */
	function replyAndAsk(written: CommentField) {
		const said = review.threads.sayAndAsk(written);
		review.sections.keyboardToThread(said.thread);
		void asking(said.asked);
	}

	/** Put the reply being written away; the keyboard stays with the thread. */
	function putAway(written: CommentField) {
		writing.discard(written);
		review.sections.keyboardToThread(thread.id);
	}

	/** Wait for a question to be handed over, and say so if it could not be. */
	async function asking(handedOver: Promise<void>) {
		failed = null;
		try {
			await handedOver;
		} catch (error) {
			failed = messageOf(error);
		}
	}
</script>

<!-- One card: its bar, the same open and folded; open, its turns a row each under the bar, and the reader's next
	turn at its foot — a field to begin it in, the field itself once begun -->
<Card
	{tone}
	{hangs}
	testId={TEST_IDS[drawn]}
	role="presentation"
	onclick={markRead}
	onfocusin={markRead}
	children={folded ? undefined : conversation}
	foot={folded ? undefined : nextTurn}
>
	{#snippet bar()}
		<ThreadBar {thread} {folded} />
	{/snippet}
</Card>

{#snippet conversation()}
	<Conversation testId="thread-turns">
		<ThreadConversation {thread} />

		{#if askable || failed}
			<!-- Hands over everything said so far, the comment included: a row of its own under the last of it, in
				the column of what was said, rather than beside the empty field below; and why it could not be -->
			<TurnAside lays="stacked" testId="ask-row">
				{#if askable}
					<Button tone="asking" size="sm" testId="ask-now-thread" onclick={() => asking(review.threads.ask(thread.id))}>
						<Icon name="conversation" size="xs" />
						{thread.turns.length === 0 ? 'Ask about this' : 'Ask about all this'}
					</Button>
				{/if}
				{#if failed}
					<Failure stands="apart" testId="ask-error" said={failed} />
				{/if}
			</TurnAside>
		{/if}
	</Conversation>
{/snippet}

{#snippet nextTurn()}
	{#if replying}
		<CommentBox
			field={replying}
			onSave={() => reply(replying)}
			onAsk={review.canAsk ? () => replyAndAsk(replying) : undefined}
			onCancel={() => putAway(replying)}
			severityPicker={false}
			hangs="in-its-thread"
			{voice}
		/>
	{:else}
		<FieldButton
			placeholder={PLACEHOLDERS.reply}
			{voice}
			testId="open-reply"
			onclick={() => writing.openReply(thread.id)}
		/>
	{/if}
{/snippet}
