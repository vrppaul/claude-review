<script lang="ts">
	import type { Thread } from '$lib/types';
	import type { CommentField } from '$lib/review/comment-field.svelte';
	import { useReview } from '$lib/review/context';
	import { messageOf } from '$lib/utils/errors';
	import { AGENT, raisedByAgent } from '$lib/utils/speakers';
	import CommentBox from './CommentBox.svelte';
	import ThreadConversation from './ThreadConversation.svelte';
	import ThreadHeading from './ThreadHeading.svelte';

	// What the thread says when it could not be handed over and nothing said why
	const ASKING_FAILED = 'Could not ask';

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
	const askable = $derived(review.answerer.attached && awaiting.length === 0 && lastWord !== AGENT);
	const raised = $derived(raisedByAgent(thread));
	// What has gone out with a round reads as read by the other side; what is
	// still unsent keeps the mark colour
	const sent = $derived(review.threads.sentInRound(thread.id) !== undefined);

	/** Looking at the thread — clicking in it, or moving the keyboard into it — is what makes its answer read. */
	function markRead() {
		review.threads.reading.markRead(thread.id);
	}

	/** Add the reply being written, and hand the thread over with it. */
	function replyAndAsk(written: CommentField) {
		void asking(review.threads.sayAndAsk(written));
	}

	/** Wait for a question to be handed over, and say so if it could not be. */
	async function asking(handedOver: Promise<void>) {
		failed = null;
		try {
			await handedOver;
		} catch (error) {
			failed = messageOf(error, ASKING_FAILED);
		}
	}
</script>

<div
	class={[
		'cr-comment group rounded-r px-4 py-3',
		thread.anchor.outdated && 'cr-stale',
		sent && !raised && 'cr-sent',
		raised && 'cr-raised'
	]}
	role="presentation"
	onclick={markRead}
	onfocusin={markRead}
>
	<ThreadHeading {thread} />

	{#if thread.anchor.outdated && thread.anchor.quote.length > 0}
		<!-- One that has lost its lines keeps its own copy of them -->
		<div data-testid="stale-quote" class="cr-stale-quote mb-3 rounded-r px-3 py-2">
			<p class="cr-muted mb-1 text-xs">what it was written against</p>
			{#each thread.anchor.quote as line, index (index)}
				<pre class="cr-code cr-muted overflow-x-auto font-mono">{line}</pre>
			{/each}
		</div>
	{/if}

	<ThreadConversation {thread} />

	{#if askable}
		<!-- Hands over everything said so far, the comment included, and hangs
			under the last of it rather than beside the empty field below. -->
		<div class="mt-3">
			<button
				type="button"
				data-testid="ask-now-thread"
				class="btn btn-outline btn-xs"
				onclick={() => asking(review.threads.ask(thread.id))}
			>
				{thread.turns.length === 0 ? 'Ask about this' : 'Ask about all this'}
			</button>
		</div>
	{/if}

	{#if failed}
		<p data-testid="ask-error" class="mt-2 text-xs text-error">{failed}</p>
	{/if}

	{#if replying}
		<div class="mt-3">
			<CommentBox
				field={replying}
				onSave={() => review.threads.say(replying)}
				onAsk={review.answerer.attached ? () => replyAndAsk(replying) : undefined}
				onCancel={() => writing.discard(replying)}
				severityPicker={false}
				nested
			/>
		</div>
	{:else}
		<div class="mt-3 border-t border-base-300 pt-3">
			<button
				type="button"
				data-testid="open-reply"
				class="cr-field cr-comment-body block w-full rounded px-3 py-1.5 text-left"
				onclick={() => writing.openReply(thread.id)}
			>
				<span class="cr-muted">Write a reply…</span>
			</button>
		</div>
	{/if}
</div>
