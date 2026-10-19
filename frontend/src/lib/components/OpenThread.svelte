<script lang="ts">
	import type { Thread } from '$lib/types';
	import type { CommentField } from '$lib/review/comment-field.svelte';
	import { useReview } from '$lib/review/context';
	import Button from '$lib/ui/Button.svelte';
	import Card from '$lib/ui/Card.svelte';
	import type { CardHanging, CardTone } from '$lib/ui/card';
	import type { FieldVoice } from '$lib/ui/field';
	import FieldButton from '$lib/ui/FieldButton.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import { messageOf } from '$lib/utils/errors';
	import { AGENT, raisedByAgent } from '$lib/utils/speakers';
	import CommentBox from './CommentBox.svelte';
	import { PLACEHOLDERS } from './placeholders';
	import ThreadConversation from './ThreadConversation.svelte';
	import ThreadTurn from './ThreadTurn.svelte';

	interface Props {
		thread: Thread;
		/** Where its card hangs: under its line, under a block of the story's words, or at the head of what it lost its place in. */
		hangs: CardHanging;
	}

	let { thread, hangs }: Props = $props();
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
	const raised = $derived(raisedByAgent(thread));
	// The field to reply in is edged in the colour of whose thread it is
	const voice = $derived<FieldVoice>(raised ? 'agent' : 'reader');
	// What has gone out with a round reads as read by the other side; what is
	// still unsent keeps the mark colour
	const sent = $derived(review.threads.sentInRound(thread.id) !== undefined);
	// Its card's edge says where it stands: the agent's colour when the agent raised it, quieter once it went
	// out with a round, faint once what it was written on is gone, and the reader's mark while in their hands
	const tone = $derived.by<CardTone>(() => {
		if (raised) return 'agent';
		if (sent) return 'quiet';
		return thread.anchor.outdated ? 'stale' : 'reader';
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

<!-- One card, its turns a row each; what is said in a thread the agent raised is said in the agent's colour -->
<Card {tone} {hangs} testId="thread-card" role="presentation" onclick={markRead} onfocusin={markRead}>
	<div class={['cr-thread-rows', raised && 'cr-raised']}>
		<ThreadConversation {thread} />

		{#if askable || failed}
			<!-- Hands over everything said so far, the comment included: a row of its own under the last of it, in
				the column of what was said, rather than beside the empty field below; and why it could not be -->
			<div data-testid="ask-row" class="cr-thread-row cr-thread-aside flex flex-col items-start gap-2">
				{#if askable}
					<Button tone="asking" size="xs" testId="ask-now-thread" onclick={() => asking(review.threads.ask(thread.id))}>
						<Icon name="conversation" size="xs" />
						{thread.turns.length === 0 ? 'Ask about this' : 'Ask about all this'}
					</Button>
				{/if}
				{#if failed}
					<p data-testid="ask-error" class="text-xs text-error">{failed}</p>
				{/if}
			</div>
		{/if}

		<!-- The reader's next turn, the last of the thread: a field to begin it in, the field itself once begun -->
		<ThreadTurn voice="reply" testId="reply-turn">
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
		</ThreadTurn>
	</div>
</Card>
