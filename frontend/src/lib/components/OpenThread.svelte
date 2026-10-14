<script lang="ts">
	import type { Thread } from '$lib/types';
	import type { CommentField } from '$lib/review/comment-field.svelte';
	import { useReview } from '$lib/review/context';
	import { messageOf } from '$lib/utils/errors';
	import { AGENT, raisedByAgent } from '$lib/utils/speakers';
	import CommentBox from './CommentBox.svelte';
	import { PLACEHOLDERS } from './placeholders';
	import ThreadConversation from './ThreadConversation.svelte';
	import ThreadTurn from './ThreadTurn.svelte';

	interface Props {
		thread: Thread;
	}

	let { thread }: Props = $props();
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
	// What has gone out with a round reads as read by the other side; what is
	// still unsent keeps the mark colour
	const sent = $derived(review.threads.sentInRound(thread.id) !== undefined);

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

<div
	data-testid="thread-card"
	class={['cr-thread-card', thread.anchor.outdated && 'cr-stale', sent && !raised && 'cr-sent', raised && 'cr-raised']}
	role="presentation"
	onclick={markRead}
	onfocusin={markRead}
>
	<ThreadConversation {thread} />

	{#if askable || failed}
		<!-- Hands over everything said so far, the comment included: a row of its own under the last of it, in
			the column of what was said, rather than beside the empty field below; and why it could not be -->
		<div data-testid="ask-row" class="cr-thread-row cr-thread-aside flex flex-col items-start gap-2">
			{#if askable}
				<button
					type="button"
					data-testid="ask-now-thread"
					class="btn btn-outline btn-xs"
					onclick={() => asking(review.threads.ask(thread.id))}
				>
					{thread.turns.length === 0 ? 'Ask about this' : 'Ask about all this'}
				</button>
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
				nested
			/>
		{:else}
			<button
				type="button"
				data-testid="open-reply"
				class="cr-reply-field"
				onclick={() => writing.openReply(thread.id)}
			>
				{PLACEHOLDERS.reply}
			</button>
		{/if}
	</ThreadTurn>
</div>
